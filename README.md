# ProFold

ProFold is a Mesocosm environment for simplified protein folding. An agent folds a hydrophobic-polar sequence on a 2D lattice and chooses whether to keep, repair, or mutate residues as it goes.

The reward is scalar and non-binary: compact folds with buried hydrophobic contacts score well, while collisions, exposed hydrophobic patches, and simulated high-risk mutations at critical residues are penalized.

## Local Checks

```bash
python -m unittest test_env.py
mesocosm validate benchanything.json
```

## Showcase

The replay viewer lives in `showcase/` and is designed to run on GitHub Pages or directly from disk after `showcase/data/replay.js` is generated.
