"""The contract of SKILL.md and references/ - what breaks when the prose is edited."""
import os
import re

import pytest


@pytest.fixture(scope="module")
def skill_md(skill_dir):
    return open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8").read()


@pytest.fixture(scope="module")
def checklist(skill_dir):
    return open(os.path.join(skill_dir, "references", "style-checklist.md"),
                encoding="utf-8").read()


# ------------------------------------------------------- frontmatter ----
def test_frontmatter_is_intact(skill_md):
    """Broken frontmatter loads with empty metadata - silently."""
    assert skill_md.startswith("---\n"), "frontmatter has no opening ---"
    fm = skill_md.split("---", 2)[1]
    assert re.search(r"^name:\s*twbx-lint\s*$", fm, re.M), "the name field is gone"
    desc = re.search(r"^description:\s*(.+)$", fm, re.M)
    assert desc, "the description field is gone"
    assert len(desc.group(1)) <= 1024, "description is longer than the 1024-character limit"


def test_stays_a_manual_command(skill_md):
    """disable-model-invocation: true - the skill runs only via
    /twbx-lint. If the flag goes away, Claude will start invoking it on
    its own for any .twbx, and that is a different product."""
    fm = skill_md.split("---", 2)[1]
    assert re.search(r"^disable-model-invocation:\s*true\s*$", fm, re.M), (
        "\nHEADS UP - the skill became auto-invocable.\n"
        "Restore disable-model-invocation: true, or knowingly accept\n"
        "that the model will now trigger it, not only you.\n"
    )


# ---------------------------------------------------------- links ----
def test_referenced_files_exist(skill_dir, skill_md):
    refs = set(re.findall(r"`((?:references|assets|scripts)/[\w./ -]+?)`", skill_md))
    missing = sorted(r for r in refs
                     if not os.path.exists(os.path.join(skill_dir, r.strip())))
    assert not missing, (
        "\nHEADS UP - SKILL.md links to something that does not exist:\n"
        + "\n".join(f"    · {m}" for m in missing) + "\n"
    )


def test_checklist_links_resolve(skill_dir, checklist):
    refs = set(re.findall(r"`(style-guide/[\w./-]+)`", checklist))
    base = os.path.join(skill_dir, "references")
    missing = sorted(r for r in refs if not os.path.exists(os.path.join(base, r)))
    assert not missing, (
        "\nHEADS UP - the checklist links to guide sections that do not exist:\n"
        + "\n".join(f"    · {m}" for m in missing) + "\n"
    )


# --------------------------------------------------------- structure ----
@pytest.mark.parametrize("section", ["A.", "B.", "C.", "D.", "E."])
def test_checklist_section_present(checklist, section):
    """The report template requires a verdict for A-D, and E is the
    exceptions list. A missing section makes the report dishonest."""
    assert re.search(rf"^#+\s*{re.escape(section)}", checklist, re.M), (
        f"\nHEADS UP - section {section} disappeared from the checklist\n"
    )


def test_report_template_fields_intact(skill_md):
    """The report template is a contract with the user."""
    # NOTE: these labels are matched verbatim against SKILL.md's report
    # template, which is user-facing prose and stays in its own language -
    # do not translate this list, only the surrounding test prose.
    required = ["Исправлено", "Чеклист:", "Не сделано:", "Валидация:",
                "Tableau:", "Приёмка:", "Исходник dummy/"]
    missing = [f for f in required if f not in skill_md]
    assert not missing, (
        "\nHEADS UP - fields disappeared from the report template:\n"
        + "\n".join(f"    · {m}" for m in missing) + "\n"
    )


def test_workflow_steps_are_contiguous(skill_md):
    """Workflow steps are numbered 0..10 with no gaps - the text itself refers to them."""
    body = skill_md.split("## Workflow", 1)[1]
    nums = [int(n) for n in re.findall(r"^(\d+)\.\s+\*\*", body, re.M)]
    assert nums == list(range(nums[0], nums[0] + len(nums))), (
        f"\nHEADS UP - the step numbering drifted: {nums}\n"
    )


def test_every_cli_subcommand_is_documented(skill_dir, skill_md):
    src = open(os.path.join(skill_dir, "scripts", "twbx_tool.py"),
               encoding="utf-8").read()
    subs = set(re.findall(r'sub\.add_parser\("([\w-]+)"\)', src))
    # Match on word boundary to avoid substring false positives: a mention
    # of "packaged" elsewhere in the prose must not count as documenting
    # the `pack` subcommand, and "pack" must not satisfy a longer sibling
    # subcommand that merely starts with it.
    undocumented = sorted(
        s for s in subs
        if not re.search(re.escape(s) + r"(?![\w-])", skill_md))
    assert not undocumented, (
        "\nHEADS UP - subcommands exist in the script but are not documented in SKILL.md:\n"
        + "\n".join(f"    · {s}" for s in undocumented) + "\n"
    )


def test_success_gate_wording_survives(skill_md):
    """The contract "done only on PASS and OK" is the skill's core.
    Historically, softening this wording produced success reports for
    files that never actually opened."""
    for phrase in ("open-verify", "PASS", "SKIP"):
        assert phrase in skill_md, f"mention of {phrase!r} disappeared"
    # Pin the actual "Non-negotiable contract" sentence instead of a bare
    # "not ... success" pattern. The previous regex's `not.*success`
    # branch had no tie to SKIP at all, and with re.S its unbounded `.*`
    # let the "not" in an unrelated "do not fight it" (about dummy/, said
    # several lines earlier) reach forward to *any* later "success"
    # mention - so a rewrite that flipped SKIP to count as a pass still
    # left the regex satisfied by leftover, unrelated text elsewhere in
    # the document. This match is bounded (`.{0,N}`, never unbounded) and
    # anchored on the literal contract sentence, so only that sentence
    # itself - still saying SKIP/INCONCLUSIVE are not OK - can satisfy it.
    gate = re.search(
        r"only DONE when `validate` prints PASS.{0,80}?"
        r"AND `open-verify` prints OK\..{0,300}?"
        r"SKIP.{0,120}?INCONCLUSIVE.{0,20}?not.{0,20}?OK",
        skill_md, re.S)
    assert gate, (
        "\nHEADS UP - SKILL.md's non-negotiable contract sentence "
        "('run is only DONE when PASS and OK; SKIP/INCONCLUSIVE are not "
        "OK') is gone or reworded away from its meaning.\n"
    )


# ------------------------------------------------------- dummy/ guard ----
import json
import subprocess
import sys

from conftest import PLUGIN_DIR

GUARD = os.path.join(PLUGIN_DIR, "hooks", "protect-dummy.py")


def _guard(payload):
    return subprocess.run([sys.executable, GUARD], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=30)


def test_dummy_guard_ships_with_the_plugin():
    """SKILL.md promises a PreToolUse hook that denies writes into dummy/."""
    assert os.path.isfile(GUARD), (
        f"\n\nHEADS UP - the dummy/ guard SKILL.md promises is gone:\n    {GUARD}\n")
    import py_compile
    py_compile.compile(GUARD, doraise=True)


def test_dummy_guard_is_declared_in_plugin_hooks():
    hooks = os.path.join(PLUGIN_DIR, "hooks", "hooks.json")
    assert os.path.isfile(hooks), "plugin ships no hooks.json"
    assert "protect-dummy" in open(hooks, encoding="utf-8").read()


def test_dummy_guard_denies_writes_via_permission_decision():
    """PreToolUse denies with a JSON decision and exit 0 - never exit 2.

    cwd is set explicitly: the guard resolves dummy/ from the payload's cwd
    (an installed plugin's own location is not the user's project), so the
    payload must say which project it's acting in, same as Claude Code sends.
    """
    target = os.path.join(PLUGIN_DIR, "dummy", "x.twbx")
    r = _guard({"tool_name": "Write", "tool_input": {"file_path": target},
                "cwd": PLUGIN_DIR})
    assert r.returncode == 0, f"PreToolUse must exit 0, got {r.returncode}"
    out = json.loads(r.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    assert out["permissionDecision"] == "deny", out


def test_dummy_guard_allows_reads():
    """Step 9 of the workflow re-hashes the source; reading must not be blocked."""
    r = _guard({"tool_name": "Bash",
                "tool_input": {"command": "shasum -a 256 dummy/x.twbx"}})
    assert r.returncode == 0
    assert r.stdout.strip() == "", f"read was blocked: {r.stdout}"


def test_placeholder_registry_matches_the_checklist_intent(tool, skill_md):
    """PLACEHOLDERS in the code is what the skill promises to clean up."""
    assert tool.PLACEHOLDERS, "the placeholder registry is empty"
    for ph in tool.PLACEHOLDERS:
        assert isinstance(ph, str) and ph.strip()
