"""Put the repo root on sys.path so `import agent` works under pytest.

`pyproject.toml` has no `[build-system]`, so uv treats this as a virtual project and
never installs `agent/` into the venv. Rather than package it mid-hackathon, this
makes the tests importable from a clean checkout.
"""

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
