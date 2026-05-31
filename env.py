from __future__ import annotations

import json
import random
from typing import Any

from bench_common.env_sdk.base import BaseEnv, StepResult

DIRECTIONS = {
    "up": (0, -1),
    "right": (1, 0),
    "down": (0, 1),
    "left": (-1, 0),
}

MUTATIONS = {"keep", "conservative", "risky", "repair"}
GRID_LIMIT = 6

SCENARIOS = [
    {
        "id": "cftr-channel",
        "name": "CFTR-like chloride channel segment",
        "sequence": "HPPHCHPHHP",
        "critical": {4, 8},
        "risk_notes": "Misfolded channel segments can be degraded before reaching the cell surface.",
    },
    {
        "id": "amyloid-core",
        "name": "Amyloid-prone hydrophobic core",
        "sequence": "HHPPHCHHPP",
        "critical": {5},
        "risk_notes": "Exposed hydrophobic patches raise aggregation pressure linked to toxic plaques.",
    },
    {
        "id": "enzyme-pocket",
        "name": "Enzyme active-site pocket",
        "sequence": "PHHPCPHHPP",
        "critical": {4, 6},
        "risk_notes": "Critical pocket mutations can reduce catalytic activity or destabilize the fold.",
    },
]

RESIDUE_LABELS = {
    "H": "hydrophobic",
    "P": "polar",
    "C": "critical",
}


class ProFoldEnv(BaseEnv):
    def __init__(self) -> None:
        self._rng = random.Random()
        self._scenario: dict[str, Any] | None = None
        self._sequence = ""
        self._classes: list[str] = []
        self._positions: list[tuple[int, int]] = []
        self._step_index = 0
        self._total_reward = 0.0
        self._health_burden = 0.0
        self._mutation_log: list[dict[str, Any]] = []
        self._done = False

    def reset(self, seed: int | None = None, **params: Any) -> dict[str, Any]:
        self._rng.seed(seed)
        requested = params.get("scenario_id")
        scenarios = {scenario["id"]: scenario for scenario in SCENARIOS}
        if requested in scenarios:
            self._scenario = scenarios[str(requested)]
        else:
            self._scenario = self._rng.choice(SCENARIOS)

        self._sequence = str(self._scenario["sequence"])
        self._classes = list(self._sequence)
        self._positions = [(0, 0)]
        self._step_index = 0
        self._total_reward = 0.0
        self._health_burden = 0.0
        self._mutation_log = []
        self._done = False
        return self._observation("Start folding residue 1 from the origin.")

    def parse_action(self, action: Any) -> dict[str, str]:
        if isinstance(action, dict):
            direction = str(action.get("direction", "")).strip().lower()
            mutation = str(action.get("mutation", "keep")).strip().lower()
            rationale = str(action.get("rationale", "")).strip()
            parsed = {"direction": direction, "mutation": mutation}
            if rationale:
                parsed["rationale"] = rationale
            return parsed

        text = str(action).strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return self.parse_action(parsed)
        except json.JSONDecodeError:
            pass

        lowered = text.lower()
        direction = next((name for name in DIRECTIONS if name in lowered), "")
        mutation = next((name for name in MUTATIONS if name in lowered), "keep")
        return {"direction": direction, "mutation": mutation}

    def step(self, action: Any) -> StepResult:
        if self._scenario is None:
            raise RuntimeError("Call reset() before step()")
        if self._done:
            return StepResult(
                observation=self._observation("Episode already ended."),
                reward=0.0,
                terminated=True,
                truncated=False,
                info=self._info("noop", {}, 0.0, "already_done"),
            )

        parsed = self.parse_action(action)
        direction = parsed["direction"]
        mutation = parsed["mutation"] if parsed["mutation"] in MUTATIONS else "keep"
        if direction not in DIRECTIONS:
            reward = -4.0
            self._total_reward += reward
            self._done = True
            info = self._info("invalid_action", parsed, reward, "invalid_direction")
            return StepResult(
                observation=self._observation("Invalid direction ended the fold."),
                reward=reward,
                terminated=True,
                truncated=False,
                info=info,
            )

        next_index = len(self._positions)
        original_class = self._sequence[next_index]
        mutated_class, mutation_penalty, health_delta, mutation_event = self._apply_mutation(
            next_index, original_class, mutation
        )
        self._classes[next_index] = mutated_class

        dx, dy = DIRECTIONS[direction]
        px, py = self._positions[-1]
        new_pos = (px + dx, py + dy)
        event = "placed"
        reward = 0.15 + mutation_penalty

        if self._is_collision(new_pos) or self._is_out_of_bounds(new_pos):
            reward -= 4.5
            self._health_burden += health_delta + 1.2
            self._total_reward += reward
            self._done = True
            info = self._info(
                "invalid_fold",
                {**parsed, **mutation_event, "position": list(new_pos)},
                reward,
                "collision_or_out_of_bounds",
            )
            return StepResult(
                observation=self._observation("Invalid self-intersection or out-of-bounds fold."),
                reward=reward,
                terminated=True,
                truncated=False,
                info=info,
            )

        self._positions.append(new_pos)
        self._health_burden += health_delta
        contacts = self._new_contacts(next_index)
        exposure = self._exposed_hydrophobics()
        compactness = self._compactness()
        contact_reward = 1.35 * contacts
        exposure_penalty = -0.18 * exposure
        compact_bonus = 0.35 * compactness
        health_penalty = -0.65 * health_delta
        reward += contact_reward + compact_bonus + exposure_penalty + health_penalty

        if next_index in self._scenario["critical"] and mutated_class == "C":
            reward += 0.45

        terminated = len(self._positions) == len(self._sequence)
        if terminated:
            event = "completed"
            reward += self._terminal_bonus()
            self._done = True

        self._step_index += 1
        self._total_reward += reward
        payload = {
            **parsed,
            **mutation_event,
            "position": list(new_pos),
            "new_contacts": contacts,
            "exposed_hydrophobics": exposure,
            "compactness": round(compactness, 3),
        }
        return StepResult(
            observation=self._observation(self._message(event, reward, contacts, health_delta)),
            reward=round(reward, 4),
            terminated=terminated,
            truncated=False,
            info=self._info(event, payload, reward, "ok"),
        )

    def _apply_mutation(
        self, index: int, original_class: str, mutation: str
    ) -> tuple[str, float, float, dict[str, Any]]:
        critical = index in self._scenario["critical"]
        new_class = original_class
        reward_delta = 0.0
        health_delta = 0.0

        if mutation == "conservative":
            reward_delta = -0.12
            health_delta = 0.08 if critical else 0.03
            if original_class == "C":
                new_class = "H"
        elif mutation == "risky":
            reward_delta = -0.75 if critical else -0.35
            health_delta = 1.35 if critical else 0.55
            new_class = "H" if original_class != "H" else "P"
        elif mutation == "repair":
            if critical:
                reward_delta = 0.55
                health_delta = -0.25
                new_class = "C"
            else:
                reward_delta = -0.25
                health_delta = 0.10

        event = {
            "residue_index": index,
            "original_class": original_class,
            "mutated_class": new_class,
            "mutation_health_delta": round(health_delta, 3),
            "critical_residue": critical,
        }
        if mutation != "keep":
            self._mutation_log.append(event)
        return new_class, reward_delta, health_delta, event

    def _new_contacts(self, index: int) -> int:
        if self._classes[index] not in {"H", "C"}:
            return 0
        x, y = self._positions[index]
        contacts = 0
        for other_index, (ox, oy) in enumerate(self._positions[:-1]):
            if abs(x - ox) + abs(y - oy) != 1:
                continue
            if abs(index - other_index) == 1:
                continue
            if self._classes[other_index] in {"H", "C"}:
                contacts += 1
        return contacts

    def _exposed_hydrophobics(self) -> int:
        occupied = set(self._positions)
        exposed = 0
        for index, (x, y) in enumerate(self._positions):
            if self._classes[index] not in {"H", "C"}:
                continue
            open_neighbors = 0
            for dx, dy in DIRECTIONS.values():
                if (x + dx, y + dy) not in occupied:
                    open_neighbors += 1
            if open_neighbors >= 3:
                exposed += 1
        return exposed

    def _compactness(self) -> float:
        xs = [p[0] for p in self._positions]
        ys = [p[1] for p in self._positions]
        area = (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1)
        return len(self._positions) / max(area, 1)

    def _terminal_bonus(self) -> float:
        contacts = self._total_contacts()
        exposure = self._exposed_hydrophobics()
        health_score = max(0.0, 1.0 - self._health_burden / 8.0)
        return 1.8 * contacts + 2.5 * health_score - 0.35 * exposure

    def _total_contacts(self) -> int:
        contacts = 0
        for i, (x, y) in enumerate(self._positions):
            if self._classes[i] not in {"H", "C"}:
                continue
            for j in range(i + 2, len(self._positions)):
                ox, oy = self._positions[j]
                if self._classes[j] in {"H", "C"} and abs(x - ox) + abs(y - oy) == 1:
                    contacts += 1
        return contacts

    def _is_collision(self, pos: tuple[int, int]) -> bool:
        return pos in set(self._positions)

    def _is_out_of_bounds(self, pos: tuple[int, int]) -> bool:
        x, y = pos
        return abs(x) > GRID_LIMIT or abs(y) > GRID_LIMIT

    def _message(self, event: str, reward: float, contacts: int, health_delta: float) -> str:
        return (
            f"{event}: reward {reward:.2f}, new hydrophobic contacts {contacts}, "
            f"health burden delta {health_delta:.2f}."
        )

    def _observation(self, message: str) -> dict[str, Any]:
        next_index = len(self._positions)
        next_residue = None
        if next_index < len(self._sequence):
            raw = self._sequence[next_index]
            next_residue = {
                "index": next_index,
                "class": raw,
                "label": RESIDUE_LABELS[raw],
                "is_critical": next_index in self._scenario["critical"],
            }
        return {
            "task": "Fold the protein on a 2D lattice without collisions. Choose direction and mutation.",
            "scenario": self._scenario["name"],
            "risk_notes": self._scenario["risk_notes"],
            "step": self._step_index,
            "max_steps": len(self._sequence) - 1,
            "sequence": self._sequence,
            "placed_count": len(self._positions),
            "next_residue": next_residue,
            "chain": self._chain_payload(),
            "valid_directions": self._valid_directions(),
            "score_so_far": round(self._total_reward, 3),
            "health_burden": round(self._health_burden, 3),
            "action_schema": {
                "direction": list(DIRECTIONS.keys()),
                "mutation": ["keep", "conservative", "risky", "repair"],
                "rationale": "short free-text explanation of this move",
            },
            "message": message,
        }

    def _chain_payload(self) -> list[dict[str, Any]]:
        return [
            {
                "index": index,
                "class": self._classes[index],
                "original_class": self._sequence[index],
                "label": RESIDUE_LABELS[self._classes[index]],
                "x": pos[0],
                "y": pos[1],
                "critical": index in self._scenario["critical"],
            }
            for index, pos in enumerate(self._positions)
        ]

    def _valid_directions(self) -> list[str]:
        px, py = self._positions[-1]
        valid = []
        for name, (dx, dy) in DIRECTIONS.items():
            pos = (px + dx, py + dy)
            if not self._is_collision(pos) and not self._is_out_of_bounds(pos):
                valid.append(name)
        return valid

    def _info(
        self, event: str, action_payload: dict[str, Any], reward: float, status: str
    ) -> dict[str, str]:
        health_score = max(0.0, 1.0 - self._health_burden / 8.0)
        fold_state = {
            "scenario_id": self._scenario["id"],
            "scenario_name": self._scenario["name"],
            "sequence": self._sequence,
            "chain": self._chain_payload(),
            "grid_limit": GRID_LIMIT,
            "critical_indices": sorted(self._scenario["critical"]),
            "mutations": self._mutation_log,
            "contacts": self._total_contacts(),
            "exposed_hydrophobics": self._exposed_hydrophobics(),
            "compactness": round(self._compactness(), 4),
            "health_burden": round(self._health_burden, 4),
            "health_score": round(health_score, 4),
            "total_reward": round(self._total_reward, 4),
            "event": event,
            "status": status,
        }
        return {
            "fold_state": json.dumps(fold_state, separators=(",", ":")),
            "action_detail": json.dumps(action_payload, separators=(",", ":")),
            "event": event,
            "status": status,
            "score": f"{self._total_reward:.4f}",
            "turn_reward": f"{reward:.4f}",
            "health_burden": f"{self._health_burden:.4f}",
            "health_score": f"{health_score:.4f}",
            "contacts": str(self._total_contacts()),
        }


MyEnv = ProFoldEnv
