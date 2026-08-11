# Contributing

ContextCost makes numerical and file-selection claims. A useful change must
show the repository fixture that makes the old behavior wrong and the observed
result that makes the new behavior better.

## Local checks

```bash
python -m pytest -q
python -m ruff check src tests docs
python -m ruff format --check src tests docs
python docs/build_docs.py --check
python docs/calibrate.py --check
```

The calibration check needs the optional `calibrate` dependencies. Pull
requests that change file selection, estimation, classification, or ignore
handling should also include a real command-line fixture and state the limits
of what was not reproduced.

Keep runtime dependencies at zero unless a measured user outcome cannot be
achieved without one. Do not add adoption, performance, or compatibility
claims that were not observed.
