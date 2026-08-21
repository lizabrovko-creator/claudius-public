"""The plugin and marketplace manifests stay valid and mutually consistent."""
import json
import os
import shutil
import subprocess

import pytest

from conftest import PLUGIN_DIR, REPO_ROOT
PLUGIN_JSON = os.path.join(PLUGIN_DIR, ".claude-plugin", "plugin.json")
MARKETPLACE_JSON = os.path.join(REPO_ROOT, ".claude-plugin", "marketplace.json")


@pytest.fixture(scope="module")
def plugin():
    return json.load(open(PLUGIN_JSON, encoding="utf-8"))


@pytest.fixture(scope="module")
def marketplace():
    if not os.path.isfile(MARKETPLACE_JSON):
        pytest.skip(".claude-plugin/marketplace.json is repo-only - it lives "
                     "at the repo root, not inside the plugin, so it is not "
                     "shipped with an installed plugin copy. This "
                     "plugin<->marketplace cross-check only runs from the "
                     "repo.")
    return json.load(open(MARKETPLACE_JSON, encoding="utf-8"))


def test_plugin_manifest_has_required_fields(plugin):
    assert plugin["name"] == "upstars"
    assert plugin["description"].strip()
    assert plugin["version"].count(".") == 2, "version must be semver x.y.z"


def test_marketplace_lists_the_plugin(marketplace):
    assert marketplace["name"] == "claudius"
    assert marketplace["owner"]["name"].strip()
    names = [p["name"] for p in marketplace["plugins"]]
    assert names == ["upstars"], names


def test_marketplace_source_resolves(marketplace):
    entry = marketplace["plugins"][0]
    resolved = os.path.normpath(os.path.join(REPO_ROOT, entry["source"]))
    assert resolved == os.path.normpath(PLUGIN_DIR), (
        f"\n\nHEADS UP - marketplace source points at {resolved},\n"
        f"but the plugin lives at {PLUGIN_DIR}\n")


def test_plugin_and_skill_names_differ(plugin):
    """A plugin namespace is always prefixed; equal names give /x:x."""
    skills = os.listdir(os.path.join(PLUGIN_DIR, "skills"))
    assert plugin["name"] not in skills, (
        f"\n\nHEADS UP - plugin '{plugin['name']}' has a skill of the same name,\n"
        f"so the daily command becomes /{plugin['name']}:{plugin['name']}.\n")


def test_claude_plugin_dir_holds_only_the_manifest():
    """skills/ and hooks/ belong at the plugin root, never inside .claude-plugin/."""
    entries = sorted(os.listdir(os.path.join(PLUGIN_DIR, ".claude-plugin")))
    assert entries == ["plugin.json"], entries


@pytest.mark.skipif(
    shutil.which("claude") is None,
    reason="needs the claude CLI, which CI runners do not have. Skipping loses "
           "nothing there: the repo's PostToolUse hook runs the same "
           "`claude plugin validate --strict` on every edit to the skill, on a "
           "machine where the binary exists."
)
def test_cli_validation_passes_strict():
    r = subprocess.run(["claude", "plugin", "validate", "--strict", PLUGIN_DIR],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
