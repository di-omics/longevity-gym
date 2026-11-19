"""The repo's own rules: aggregates only, ASCII only, README built from results/."""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_repo_holds_no_participant_level_real_data():
    from longevitygym import realcheck
    assert realcheck.REAL["n_samples"] == 168
    numbers = json.dumps(realcheck.REAL)
    assert len(numbers) < 3000                                                # aggregates only
    assert not list(ROOT.rglob("*.xlsx")) or all(".venv" in str(p) or "venv" in p.parts for p in ROOT.rglob("*.xlsx"))


def _tracked_files():
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        files = [ROOT / line for line in out.splitlines() if line]
        if files:
            return files
    except (OSError, subprocess.CalledProcessError):
        pass
    files = [ROOT / "README.md", ROOT / "pyproject.toml", ROOT / ".gitignore"]
    for folder in ("src", "tests", "docs", "results", "tools", ".github"):
        files += [p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    return files


def test_repo_is_ascii_with_no_em_dashes():
    for path in _tracked_files():
        if path.exists() and path.suffix != ".pyc":
            data = path.read_bytes()
            assert all(b < 128 for b in data), path


def test_readme_is_built_from_the_results_files():
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "build_readme.py"), "--check"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
