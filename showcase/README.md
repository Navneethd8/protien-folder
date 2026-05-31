# ProFold Showcase

`index.html` is a self-contained replay viewer. It loads `data/replay.json` on GitHub Pages and falls back to `data/replay.js` when opened directly from disk.

After a Mesocosm run completes:

```bash
mesocosm run export RUN_ID -o showcase/data/replay.json
python scripts/replay_json_to_js.py
```
