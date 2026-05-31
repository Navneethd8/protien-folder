from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
replay_json = ROOT / "showcase" / "data" / "replay.json"
replay_js = ROOT / "showcase" / "data" / "replay.js"

data = json.loads(replay_json.read_text(encoding="utf-8"))
replay_js.write_text(
    "window.REPLAY = " + json.dumps(data, indent=2) + ";\n",
    encoding="utf-8",
)
print(f"wrote {replay_js}")
