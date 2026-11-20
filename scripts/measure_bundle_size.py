#!/usr/bin/env python3
"""Install requirements into a clean target dir and report deploy-like bundle size."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "requirements.txt"


def _dir_size(path: Path) -> int:
    total = 0
    if path.is_file():
        return path.stat().st_size
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


def main() -> int:
    if not REQUIREMENTS.exists():
        print("requirements.txt missing", file=sys.stderr)
        return 1

    work = Path(tempfile.mkdtemp(prefix="tutorrag-bundle-"))
    try:
        target = work / "site"
        target.mkdir()
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-q",
                "-r",
                str(REQUIREMENTS),
                "--target",
                str(target),
            ],
            cwd=ROOT,
        )

        rows: list[tuple[int, str]] = []
        for entry in target.iterdir():
            rows.append((_dir_size(entry), entry.name))
        rows.sort(reverse=True)
        tracked = sum(size for size, _ in rows)

        app_paths = [
            ROOT / "app.py",
            ROOT / "streamlit_app.py",
            ROOT / "rag",
            ROOT / "utils",
            ROOT / "knowledge_base",
            ROOT / "data" / "questions.csv",
            ROOT / "requirements.txt",
            ROOT / "vendor",
            ROOT / ".streamlit",
        ]
        app_size = sum(_dir_size(path) for path in app_paths if path.exists())
        total = tracked + app_size

        print("=== TutorRAG deploy bundle estimate ===")
        print(f"site-packages: {tracked / (1024 * 1024):.2f} MB")
        print(f"app source:    {app_size / (1024 * 1024):.2f} MB")
        print(f"TOTAL:         {total / (1024 * 1024):.2f} MB")
        print(f"limit:         500.00 MB")
        print(f"margin:        {(500 * 1024 * 1024 - total) / (1024 * 1024):.2f} MB")
        print()
        print("Top packages:")
        for size, name in rows[:20]:
            print(f"  {size / (1024 * 1024):8.2f} MB  {name}")

        forbidden = [
            name
            for _, name in rows
            if "sklearn" in name.lower() or name.lower().startswith("scipy")
        ]
        if forbidden:
            print("\nWARNING: heavy ML packages still present:", ", ".join(forbidden))
            return 2

        real_pyarrow = any(
            path.suffix in {".so", ".dylib", ".dll"}
            for path in (target / "pyarrow").rglob("*")
            if path.is_file()
        ) if (target / "pyarrow").exists() else False
        if real_pyarrow:
            print("\nWARNING: full pyarrow binaries present")
            return 2

        if total >= 500 * 1024 * 1024:
            print("\nFAIL: bundle still exceeds 500 MB")
            return 3
        if total >= 450 * 1024 * 1024:
            print("\nWARN: under 500 MB but margin < 50 MB")
        else:
            print("\nOK: under 500 MB with comfortable margin")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
