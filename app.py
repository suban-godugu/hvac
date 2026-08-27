"""Root ASGI app for hosted FastAPI detection."""
import os
import sys

_ROOT = os.path.abspath(os.path.dirname(__file__))
_BACKEND = os.path.join(_ROOT, "backend")
# Root first so `database` is database/, not backend/database/
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if _BACKEND not in sys.path:
    sys.path.append(_BACKEND)

from backend.cloud_env import apply_cloud_demo_env  # noqa: E402

apply_cloud_demo_env()

from main import app  # noqa: E402  # backend/main.py via PYTHONPATH
