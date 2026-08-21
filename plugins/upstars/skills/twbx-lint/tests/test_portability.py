"""The repo must work for anyone who clones it, on any machine."""
import os
import re
import subprocess
import sys

import pytest

from conftest import PLUGIN_DIR, REPO_ROOT

PYTEST_INI = os.path.join(REPO_ROOT, "pytest.ini")

# iteration-1 is NOT skipped: its per-run artefacts are untracked, so they never
# reach this sweep anyway, while its benchmark.json IS tracked and was scrubbed of
# another machine's paths. Skipping the directory would leave that scrub unguarded.
SKIP_DIRS = {".git", "__pycache__", "node_modules", "tmp", "results", "dummy",
             ".pytest_cache"}
TEXT_EXT = (".md", ".py", ".json", ".sh", ".yml", ".yaml", ".ini", ".html", ".txt")


def _tracked_text_files():
    out = subprocess.run(["git", "-C", REPO_ROOT, "ls-files"],
                         capture_output=True, text=True, timeout=60).stdout
    for rel in out.splitlines():
        if any(part in SKIP_DIRS for part in rel.split("/")):
            continue
        if rel.endswith(TEXT_EXT):
            yield rel


def test_no_absolute_home_paths_anywhere_tracked():
    offenders = []
    for rel in _tracked_text_files():
        p = os.path.join(REPO_ROOT, rel)
        if not os.path.isfile(p):
            continue
        text = open(p, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"/(?:Users|home)/[A-Za-z][\w.-]+/", text):
            offenders.append(f"{rel}: {m.group(0)}")
    assert not offenders, (
        "\n\nHEADS UP - absolute home paths break the repo for everyone else:\n"
        + "\n".join(f"    - {o}" for o in sorted(set(offenders))) + "\n")


def test_exactly_one_skill_md_per_skill_name():
    """Three copies of this skill once coexisted; tests watched the wrong one."""
    seen = {}
    out = subprocess.run(["git", "-C", REPO_ROOT, "ls-files", "*SKILL.md"],
                         capture_output=True, text=True, timeout=60).stdout
    for rel in out.splitlines():
        name = os.path.basename(os.path.dirname(rel))
        seen.setdefault(name, []).append(rel)
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    assert not dupes, (
        "\n\nHEADS UP - a skill exists in more than one place:\n"
        + "\n".join(f"    {k}:\n" + "\n".join(f"        - {p}" for p in v)
                    for k, v in dupes.items())
        + "\n\nTests would watch one copy while Claude Code loads another.\n")


@pytest.mark.skipif(
    not os.path.isfile(PYTEST_INI),
    reason="pytest.ini is repo-only - it is not shipped with an installed "
           "plugin copy, and this check needs it to invoke pytest with an "
           "explicit config from an arbitrary cwd. It only runs from the "
           "repo."
)
def test_suite_runs_from_any_working_directory(tmp_path):
    # pytest.ini's `testpaths` is a path relative to the repo root, and pytest
    # resolves it against the process's cwd, not against --rootdir/-c, when
    # they differ (pytest 9.1.1: 0 items collected without this). Passing the
    # tests dir explicitly - derived from PLUGIN_DIR, not hardcoded - is what
    # actually makes the invocation cwd-independent, which is the property
    # this test exists to check.
    tests_dir = os.path.join(PLUGIN_DIR, "skills", "twbx-lint", "tests")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q",
                        "--rootdir", REPO_ROOT, "-c", PYTEST_INI,
                        tests_dir, "-k", "test_title_case_accepts"],
                       cwd=str(tmp_path), capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, (
        "\n\nHEADS UP - the suite depends on the current directory:\n"
        + r.stdout[-2000:] + r.stderr[-2000:])


def test_tmp_is_not_tracked():
    out = subprocess.run(["git", "-C", REPO_ROOT, "ls-files", "tmp/"],
                         capture_output=True, text=True, timeout=60).stdout.strip()
    assert not out, (
        "\n\nHEADS UP - tmp/ is tracked again; it held 38 MB of binary workbooks:\n"
        + out[:500] + "\n")
