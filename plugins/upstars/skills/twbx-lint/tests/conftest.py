"""Shared fixtures for the twbx-lint tests.

None of this needs Tableau Desktop, the network, or an LLM - the whole
suite is deterministic and runs in a fraction of a second.
"""
import os
import subprocess
import sys
import tempfile
import zipfile

import pytest

# tests/ -> twbx-lint -> skills -> upstars -> plugins -> repo root
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_DIR = os.path.dirname(os.path.dirname(SKILL_DIR))
REPO_ROOT = os.path.dirname(os.path.dirname(PLUGIN_DIR))
TOOL = os.path.join(SKILL_DIR, "scripts", "twbx_tool.py")
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

import twbx_tool as T  # noqa: E402


@pytest.fixture(scope="session")
def tool():
    """The module itself - for tests against pure functions and registries."""
    return T


@pytest.fixture(scope="session")
def skill_dir():
    return SKILL_DIR


@pytest.fixture(scope="session")
def plugin_dir():
    return PLUGIN_DIR


@pytest.fixture(scope="session")
def repo_root():
    return REPO_ROOT


@pytest.fixture
def issues_of(tmp_path):
    """Run a .twb string through the validator, return the list of findings.

    package_dir defaults to an empty folder next to the file: that turns on
    the Image/ reference check, and it has no effect on the other rules.
    """
    def run(xml: str, package_dir: str | None = None) -> list[str]:
        pkg = package_dir if package_dir is not None else str(tmp_path)
        fd, path = tempfile.mkstemp(suffix=".twb", dir=pkg)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(xml)
        try:
            return T._structural_issues(path, pkg)
        finally:
            os.unlink(path)
    return run


@pytest.fixture
def run_cli():
    """Invoke twbx_tool.py as a subprocess. Returns a CompletedProcess.

    A subprocess, deliberately, not an import: exit codes are part of the
    skill's contract, SKILL.md refers to them, and they need to be checked
    the same way the real workflow sees them.
    """
    def run(*argv: str, cwd: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, TOOL, *argv],
            capture_output=True, text=True, cwd=cwd, timeout=120,
        )
    return run


@pytest.fixture
def make_twbx(tmp_path):
    """Build a real .twbx: a zip with a .twb at its root and optional Image/.

    eol='crlf' by default - that is what Tableau writes, and it is exactly
    what pack's line-ending-substitution guard depends on.
    """
    def build(twb_xml: str, name: str = "wb.twbx", *,
              eol: str = "crlf", images: dict[str, bytes] | None = None) -> str:
        data = twb_xml.replace("\r\n", "\n")
        if eol == "crlf":
            data = data.replace("\n", "\r\n")
        out = tmp_path / name
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("wb.twb", data.encode("utf-8"))
            for rel, blob in (images or {}).items():
                z.writestr(rel, blob)
        return str(out)
    return build
