from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data_dir = ROOT / "showcase" / "data"
replay_json = data_dir / "replay.json"
replay_js = data_dir / "replay.js"
runs_dir = data_dir / "runs"

data = json.loads(replay_json.read_text(encoding="utf-8"))
run_files = sorted(runs_dir.glob("*.json")) if runs_dir.exists() else []
runs = [
    {"id": path.stem, "label": path.stem.title(), "data": json.loads(path.read_text(encoding="utf-8"))}
    for path in run_files
]

replay_js.write_text(
    "window.REPLAY = " + json.dumps(data, indent=2) + ";\n"
    + "window.REPLAY_RUNS = " + json.dumps(runs, indent=2) + ";\n",
    encoding="utf-8",
)
print(f"wrote {replay_js}")
