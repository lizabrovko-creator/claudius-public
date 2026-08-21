"""Documentation must stay true to the code it describes."""
import json
import os
import re

import pytest

from conftest import PLUGIN_DIR, REPO_ROOT
README = os.path.join(REPO_ROOT, "README.md")


@pytest.fixture(scope="module")
def readme():
    if not os.path.isfile(README):
        pytest.skip("README.md is repo-only - it is not shipped inside an "
                     "installed plugin copy, so this doc check only runs "
                     "from a checkout of the repo itself.")
    return open(README, encoding="utf-8").read()


def test_readme_is_ukrainian(readme):
    """Written for the team; Ukrainian is the agreed language."""
    ukrainian_only = set("іїєґІЇЄҐ")
    assert ukrainian_only & set(readme), (
        "README.md has no Ukrainian-specific letters - is it the right language?")


def test_install_commands_match_the_real_names(readme):
    market = json.load(open(os.path.join(REPO_ROOT, ".claude-plugin",
                                         "marketplace.json"), encoding="utf-8"))
    plugin = json.load(open(os.path.join(PLUGIN_DIR, ".claude-plugin",
                                         "plugin.json"), encoding="utf-8"))
    expected = f"{plugin['name']}@{market['name']}"
    assert expected in readme, (
        f"\n\nHEADS UP - README does not show the real install target.\n"
        f"Expected to find: /plugin install {expected}\n")


def test_documented_invocation_matches_the_namespace(readme):
    plugin = json.load(open(os.path.join(PLUGIN_DIR, ".claude-plugin",
                                         "plugin.json"), encoding="utf-8"))
    for skill in sorted(os.listdir(os.path.join(PLUGIN_DIR, "skills"))):
        cmd = f"/{plugin['name']}:{skill}"
        # Match on word boundary to avoid substring false positives:
        # /upstars:twbx-lint should not match /upstars:twbx-lint-test
        pattern = re.escape(cmd) + r"(?![\w-])"
        assert re.search(pattern, readme), (
            f"\n\nHEADS UP - README never shows {cmd}, "
            f"which is how the skill is actually invoked.\n")


def test_relative_links_resolve(readme):
    broken = []
    for m in re.finditer(r"\]\((?!https?://|#)([^)]+)\)", readme):
        target = m.group(1).split("#")[0]
        if not target:
            continue
        # A leading "/" is a repo-root-relative link (how GitHub renders
        # it), not a filesystem-absolute path. os.path.join discards its
        # first argument entirely when the second is absolute, so without
        # stripping it this silently resolved against the real machine's
        # filesystem root and passed for any target that happened to
        # exist there (e.g. "](/etc/hosts)").
        if not os.path.exists(os.path.join(REPO_ROOT, target.lstrip("/"))):
            broken.append(target)
    assert not broken, (
        "\n\nHEADS UP - README links to files that do not exist:\n"
        + "\n".join(f"    - {b}" for b in broken) + "\n")


def test_github_page_is_linked(readme):
    assert "docs/index.html" in readme or "github.io" in readme, (
        "README should point at the GitHub page")


PAGE = os.path.join(REPO_ROOT, "docs", "index.html")


@pytest.fixture(scope="module")
def page():
    if not os.path.isfile(PAGE):
        pytest.skip("docs/index.html is repo-only - it is not shipped inside "
                     "an installed plugin copy, so this doc check only runs "
                     "from a checkout of the repo itself.")
    return open(PAGE, encoding="utf-8").read()


def test_page_is_ukrainian(page):
    assert 'lang="uk"' in page, 'the page should declare lang="uk"'
    assert set("іїєґІЇЄҐ") & set(page)


def test_page_is_self_contained(page):
    """A strict host may block third-party requests; only fonts are allowed."""
    external = [m.group(1) for m in
                re.finditer(r'(?:src|href)="(https?://[^"]+)"', page)]
    allowed = ("https://fonts.googleapis.com", "https://fonts.gstatic.com",
               "https://github.com", "https://code.claude.com")
    stray = [u for u in external if not u.startswith(allowed)]
    assert not stray, (
        "\n\nHEADS UP - the page loads third-party resources:\n"
        + "\n".join(f"    - {u}" for u in stray) + "\n")


def test_page_carries_no_attribution_footer(page):
    banned = ("Co-Authored-By", "Generated with", "Claude Code</a> ",
              "made with claude", "powered by claude")
    found = [b for b in banned if b.lower() in page.lower()]
    assert not found, f"attribution left on the page: {found}"


def test_page_shows_the_real_install_commands(page):
    market = json.load(open(os.path.join(REPO_ROOT, ".claude-plugin",
                                         "marketplace.json"), encoding="utf-8"))
    plugin = json.load(open(os.path.join(PLUGIN_DIR, ".claude-plugin",
                                         "plugin.json"), encoding="utf-8"))
    assert f"{plugin['name']}@{market['name']}" in page
    cmd = f"/{plugin['name']}:twbx-lint"
    # Match on word boundary to avoid substring false positives:
    # /upstars:twbx-lint should not match /upstars:twbx-lint-test
    pattern = re.escape(cmd) + r"(?![\w-])"
    assert re.search(pattern, page), (
        f"\n\nHEADS UP - the page never shows {cmd}, "
        f"which is how the skill is actually invoked.\n")


def test_page_states_the_macos_limitation(page):
    assert "macOS" in page, (
        "the page must say the skill is macOS-only - it is the first thing "
        "a Windows user will hit")
