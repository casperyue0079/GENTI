"""Local project persistence for GENTI.

Provides auto-save / auto-load, save-as, new-project, and project listing.
All projects are stored under ``./projects/`` as JSON files.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.models import TestProject

PROJECTS_DIR = Path(__file__).resolve().parent.parent / "projects"
AUTOSAVE_FILE = PROJECTS_DIR / "_autosave.json"
RECENT_FILE = PROJECTS_DIR / "_recent.json"


def _ensure_dir() -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Auto-save / auto-load
# ---------------------------------------------------------------------------

def auto_save(project: TestProject) -> Path:
    """Save the current project to the auto-save slot."""
    _ensure_dir()
    project.save(AUTOSAVE_FILE)
    _update_recent(str(AUTOSAVE_FILE))
    return AUTOSAVE_FILE


def auto_load() -> Optional[TestProject]:
    """Load the most-recently saved project (auto-save or last opened)."""
    recent = _get_recent_path()
    if recent and Path(recent).exists():
        try:
            return TestProject.load(recent)
        except Exception:
            pass

    if AUTOSAVE_FILE.exists():
        try:
            return TestProject.load(AUTOSAVE_FILE)
        except Exception:
            pass

    return None


# ---------------------------------------------------------------------------
# Explicit save / load
# ---------------------------------------------------------------------------

def save_as(project: TestProject, name: str) -> Path:
    """Save the project under a given name (without .json extension)."""
    _ensure_dir()
    safe_name = name.strip().replace(" ", "_")
    if not safe_name:
        safe_name = f"project_{datetime.now():%Y%m%d_%H%M%S}"
    path = PROJECTS_DIR / f"{safe_name}.json"
    project.save(path)
    _update_recent(str(path))
    return path


def load_project(path: str | Path) -> TestProject:
    p = Path(path)
    proj = TestProject.load(p)
    _update_recent(str(p))
    return proj


def new_project() -> TestProject:
    return TestProject()


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

def list_projects() -> list[dict]:
    """Return metadata for every saved project (excluding internal files)."""
    _ensure_dir()
    result = []
    for f in sorted(PROJECTS_DIR.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            theme = data.get("config", {}).get("theme", "")
            mode = data.get("config", {}).get("mode", "")
            result.append({
                "name": f.stem,
                "path": str(f),
                "theme": theme,
                "mode": mode,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
        except Exception:
            continue
    return result


# ---------------------------------------------------------------------------
# Recent-project tracking
# ---------------------------------------------------------------------------

def _update_recent(path: str) -> None:
    _ensure_dir()
    RECENT_FILE.write_text(
        json.dumps({"last": path}, ensure_ascii=False), encoding="utf-8",
    )


def _get_recent_path() -> Optional[str]:
    if not RECENT_FILE.exists():
        return None
    try:
        data = json.loads(RECENT_FILE.read_text(encoding="utf-8"))
        return data.get("last")
    except Exception:
        return None
