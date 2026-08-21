"""Assemble a Docker Space tree and upload backend/agents (no Next.js UI)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / ".hf-upload"
SPACE_ID = "subhan07/hvac-agents"
MODEL_ID = "subhan07/hvac-agents"
SKIP_DIR_NAMES = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite"}


def _copy_tree(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in SKIP_DIR_NAMES or item.name.endswith(".egg-info"):
            continue
        if item.suffix.lower() in SKIP_SUFFIXES:
            continue
        target = dest / item.name
        if item.is_dir():
            _copy_tree(item, target)
        else:
            shutil.copy2(item, target)


def stage() -> Path:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    shutil.copy2(ROOT / "huggingface-space" / "Dockerfile", STAGE / "Dockerfile")
    shutil.copy2(ROOT / "huggingface-space" / "README.md", STAGE / "README.md")
    dockerignore = ROOT / "huggingface-space" / ".dockerignore"
    if dockerignore.exists():
        shutil.copy2(dockerignore, STAGE / ".dockerignore")
    shutil.copy2(ROOT / "alembic.ini", STAGE / "alembic.ini")
    _copy_tree(ROOT / "backend", STAGE / "backend")
    _copy_tree(ROOT / "database", STAGE / "database")
    _copy_tree(ROOT / "alembic", STAGE / "alembic")
    return STAGE


def upload(space_id: str = SPACE_ID, *, as_space: bool = False) -> str:
    from huggingface_hub import HfApi

    staged = stage()
    api = HfApi()
    repo_type = "space" if as_space else "model"
    if as_space:
        api.create_repo(space_id, repo_type="space", space_sdk="docker", exist_ok=True, private=False)
    else:
        api.create_repo(space_id, repo_type="model", exist_ok=True, private=False)
        readme = ROOT / "huggingface-space" / "MODEL_README.md"
        if readme.exists():
            shutil.copy2(readme, staged / "README.md")
    api.upload_folder(
        folder_path=str(staged),
        repo_id=space_id,
        repo_type=repo_type,
        commit_message="Phase 2: simulation API, writes off, Dataset feeder on",
    )
    return space_id


if __name__ == "__main__":
    as_space = "--space" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--space"]
    sid = args[0] if args else SPACE_ID
    print(upload(sid, as_space=as_space))
    if as_space:
        print(f"https://huggingface.co/spaces/{sid}")
        print(f"https://{sid.replace('/', '-')}.hf.space/healthz")
    else:
        print(f"https://huggingface.co/{sid}")
        print("Docker Space hosting needs Hugging Face PRO; re-run with --space after subscribing.")
