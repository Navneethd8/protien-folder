from __future__ import annotations

import json
import unittest

from env import ProFoldEnv


def run_episode(seed: int, policy) -> tuple[float, list[dict]]:
    env = ProFoldEnv()
    obs = env.reset(seed=seed)
    total = 0.0
    trace = [{"observation": obs}]
    for _ in range(20):
        action = policy(obs)
        result = env.step(action)
        total += result.reward
        trace.append(
            {
                "action": action,
                "observation": result.observation,
                "reward": result.reward,
                "terminated": result.terminated,
                "truncated": result.truncated,
                "info": result.info,
            }
        )
        obs = result.observation
        if result.terminated or result.truncated:
            break
    return round(total, 4), trace


def scripted_policy(obs: dict) -> dict[str, str]:
    pattern = ["right", "down", "left", "left", "up", "right", "right", "down", "left", "down"]
    valid = obs["valid_directions"]
    direction = next((move for move in pattern[obs["step"] :] + pattern if move in valid), valid[0])
    next_residue = obs.get("next_residue") or {}
    mutation = "repair" if next_residue.get("is_critical") else "keep"
    return {"direction": direction, "mutation": mutation}


def bad_policy(obs: dict) -> dict[str, str]:
    direction = "right" if "right" in obs["valid_directions"] else "up"
    return {"direction": direction, "mutation": "risky"}


class ProFoldTests(unittest.TestCase):
    def test_deterministic_replay_for_same_seed_and_actions(self) -> None:
        actions = [
            {"direction": "right", "mutation": "keep"},
            {"direction": "down", "mutation": "repair"},
            {"direction": "left", "mutation": "keep"},
            {"direction": "up", "mutation": "conservative"},
        ]

        traces = []
        for _ in range(2):
            env = ProFoldEnv()
            obs = env.reset(seed=7)
            rollout = [obs]
            for action in actions:
                result = env.step(action)
                rollout.append(
                    {
                        "observation": result.observation,
                        "reward": result.reward,
                        "terminated": result.terminated,
                        "truncated": result.truncated,
                        "info": result.info,
                    }
                )
                if result.terminated or result.truncated:
                    break
            traces.append(json.dumps(rollout, sort_keys=True))

        self.assertEqual(traces[0], traces[1])

    def test_smart_and_dumb_policies_score_differently(self) -> None:
        smart_scores = [run_episode(seed, scripted_policy)[0] for seed in range(8)]
        dumb_scores = [run_episode(seed, bad_policy)[0] for seed in range(8)]

        self.assertGreater(sum(smart_scores) / len(smart_scores), sum(dumb_scores) / len(dumb_scores) + 2.0)
        self.assertNotEqual(smart_scores, dumb_scores)

    def test_info_values_are_strings(self) -> None:
        env = ProFoldEnv()
        obs = env.reset(seed=3)
        result = env.step(scripted_policy(obs))
        self.assertTrue(all(isinstance(value, str) for value in result.info.values()))


if __name__ == "__main__":
    unittest.main()
