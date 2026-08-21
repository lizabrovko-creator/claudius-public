"""Assets and the CLI surface: what the skill promises and what it uses."""
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest


# ------------------------------------------------------------- assets ----
@pytest.mark.parametrize("rel", [
    "assets/schema/twb_2026.2.0.xsd",
    "assets/design-materials/Preferences.tps",
    "references/style-checklist.md",
    "references/twbx-editing-rules.md",
    "references/header-recipe.md",
    "references/style-guide/99-quick-checklist.md",
    "scripts/twbx_tool.py",
])
def test_bundled_file_exists(skill_dir, rel):
    assert os.path.isfile(os.path.join(skill_dir, rel)), (
        f"\nHEADS UP - a file the skill depends on is gone: {rel}"
    )


def test_xsd_parses_and_declares_style_attribute(skill_dir):
    p = os.path.join(skill_dir, "assets", "schema", "twb_2026.2.0.xsd")
    ET.parse(p)
    assert "StyleAttribute-ST" in open(p, encoding="utf-8").read()


def test_preferences_tps_parses(skill_dir):
    ET.parse(os.path.join(skill_dir, "assets", "design-materials",
                          "Preferences.tps"))


@pytest.mark.parametrize("icon", ["1 Logo.svg", "2 Info.svg", "3 Slack.svg"])
def test_header_icon_present(skill_dir, icon):
    """header-recipe.md assembles the header out of these files."""
    assert os.path.isfile(
        os.path.join(skill_dir, "assets", "design-materials", icon))


def test_doctor_asset_list_matches_reality(skill_dir, run_cli):
    """doctor reports on assets - it must not report one that is not there,
    and must not stay silent about one that is."""
    r = run_cli("doctor")
    assert "asset XSD schema" in r.stdout
    assert "MISSING  asset" not in r.stdout, (
        "\nHEADS UP - doctor cannot find assets that are actually in the skill:\n"
        + "\n".join(l for l in r.stdout.splitlines() if "asset" in l)
    )


# ---------------------------------------------------------------- CLI ----
SUBCOMMANDS = ("clone", "extract", "pack", "validate", "doctor", "open-verify")


@pytest.mark.parametrize("sub", SUBCOMMANDS)
def test_subcommand_is_wired(sub, skill_dir):
    """The subcommand exists and accepts --help instead of crashing with a traceback."""
    tool = os.path.join(skill_dir, "scripts", "twbx_tool.py")
    r = subprocess.run([sys.executable, tool, sub, "--help"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"{sub} --help crashed:\n{r.stdout}{r.stderr}"


def test_declared_subcommands_match_the_parser(skill_dir):
    """The registry in the test and the parser in the script must not drift apart."""
    src = open(os.path.join(skill_dir, "scripts", "twbx_tool.py"),
               encoding="utf-8").read()
    actual = set(re.findall(r'sub\.add_parser\("([\w-]+)"\)', src))
    assert actual == set(SUBCOMMANDS), (
        f"\nHEADS UP - the set of subcommands changed.\n"
        f"    in the script: {sorted(actual)}\n"
        f"    in the tests:  {sorted(SUBCOMMANDS)}\n"
        "Update SUBCOMMANDS here and mention the new command in SKILL.md.\n"
    )


def test_no_subcommand_exits_nonzero(run_cli):
    assert run_cli().returncode != 0


def test_doctor_is_always_runnable(run_cli):
    """doctor is step 0 of the workflow; it must run cleanly on any machine.
    Exit code 6 is a legitimate 'there are blockers', a traceback is not."""
    r = run_cli("doctor")
    assert r.returncode in (0, 6), f"doctor crashed:\n{r.stdout}{r.stderr}"
    assert r.stdout.startswith("DOCTOR:"), r.stdout[:200]
    assert "Traceback" not in r.stderr


def test_doctor_reports_python_and_xmllint(run_cli):
    r = run_cli("doctor")
    assert "python" in r.stdout and "xmllint" in r.stdout
