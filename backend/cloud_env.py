"""Hosted-demo defaults for Render (API) and Netlify (UI)."""
from __future__ import annotations

import os

DEMO_CORS_ORIGIN_REGEX = r"https://.*\.(netlify\.app|onrender\.com)"


def is_hosted_demo() -> bool:
    return any(os.getenv(k) for k in ("RENDER", "NETLIFY", "VERCEL"))


def apply_cloud_demo_env() -> None:
    if not is_hosted_demo():
        return
    serverless = bool(os.getenv("VERCEL"))
    if serverless and not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "sqlite:////tmp/hvac_supervisory.db"
    os.environ.setdefault("HVAC_START_CONTROL_WORKER", "0" if serverless else "1")
    os.environ.setdefault("HVAC_BMS_MODE", "simulation")
    os.environ.setdefault("HVAC_USE_SIMULATION", "1")
    os.environ.setdefault("HVAC_BMS_WRITE_ENABLED", "0")
    os.environ.setdefault("HVAC_ALLOW_SIM_WRITES", "1")
    os.environ.setdefault("HVAC_ALLOW_CREATE_ALL", "1")
    os.environ.setdefault("HVAC_DEPLOYMENT_MODE", "demo")
    os.environ.setdefault("HVAC_PLANT_MODE_PERSIST", "1")
    os.environ.setdefault("HVAC_CORS_ORIGIN_REGEX", DEMO_CORS_ORIGIN_REGEX)
