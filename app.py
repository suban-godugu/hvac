"""Root ASGI app for Vercel FastAPI detection."""
import os
import sys

_ROOT = os.path.abspath(os.path.dirname(__file__))
_BACKEND = os.path.join(_ROOT, "backend")
# Root first so `database` is database/, not backend/database/
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if _BACKEND not in sys.path:
    sys.path.append(_BACKEND)

if os.getenv("VERCEL"):
    os.environ["DATABASE_URL"] = "sqlite:////tmp/hvac_supervisory.db"
    os.environ["HVAC_START_CONTROL_WORKER"] = "0"
    os.environ.setdefault("HVAC_BMS_MODE", "simulation")
    os.environ.setdefault("HVAC_USE_SIMULATION", "1")
    os.environ.setdefault("HVAC_BMS_WRITE_ENABLED", "0")
    os.environ.setdefault("HVAC_ALLOW_SIM_WRITES", "1")
    os.environ.setdefault("HVAC_ALLOW_CREATE_ALL", "1")
    os.environ.setdefault("HVAC_DEPLOYMENT_MODE", "demo")
    os.environ.setdefault("HVAC_PLANT_MODE_PERSIST", "1")
    os.environ.setdefault("HVAC_CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app")

from main import app  # noqa: E402  # backend/main.py via PYTHONPATH
