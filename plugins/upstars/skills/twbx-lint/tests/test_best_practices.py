"""Anthropic's skill-authoring guidance, encoded as executable checks.

The point is not to pass an audit once but to stop the skill drifting as it
grows: files creep past the progressive-disclosure limits, references go stale,
absolute paths sneak into prose.
"""
import os
import re
import warnings

import pytest

LINE_LIMIT = 500
TOKEN_LIMIT = 5000
DESC_LIMIT = 1024
WARN_AT = 0.8


@pytest.fixture(scope="module")
def skill_md(skill_dir):
    return open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8").read()


@pytest.fixture(scope="module")
def frontmatter(skill_md):
    return skill_md.split("---", 2)[1]


def _tokens(text: str) -> int:
    """Rough token estimate. Cyrillic costs more per character than Latin."""
    return round(len(text) / 3.6)


def _warn_near_limit(kind: str, n: int, limit: int) -> None:
    """Surface growth before it becomes urgent.

    warnings.warn, not print: pytest collects these into its warnings summary,
    so they are visible on a normal run rather than only under -s.
    """
    if n > limit * WARN_AT:
        warnings.warn(
            f"SKILL.md at {n}/{limit} {kind} ({n / limit:.0%} of the limit)",
            stacklevel=2)


def test_skill_md_within_line_limit(skill_md):
    n = len(skill_md.splitlines())
    _warn_near_limit("lines", n, LINE_LIMIT)
    assert n <= LINE_LIMIT, (
        f"\n\nHEADS UP - SKILL.md is {n} lines, over the {LINE_LIMIT} line limit.\n"
        "Move bulk material into references/ and tell the agent when to read it.\n")


def test_skill_md_within_token_limit(skill_md):
    n = _tokens(skill_md)
    _warn_near_limit("tokens", n, TOKEN_LIMIT)
    assert n <= TOKEN_LIMIT, (
        f"\n\nHEADS UP - SKILL.md is about {n} tokens, over the {TOKEN_LIMIT} limit.\n"
        "Its body stays in context every turn, so every line is a recurring cost.\n")


def test_description_within_hard_limit(frontmatter):
    desc = re.search(r"^description:\s*(.+)$", frontmatter, re.M)
    assert desc, "frontmatter has no description"
    n = len(desc.group(1))
    assert n <= DESC_LIMIT, (
        f"\n\nHEADS UP - description is {n} chars, over the {DESC_LIMIT} hard limit.\n"
        "Descriptions grow during trigger tuning; trim it back.\n")


def test_name_is_kebab_case_and_matches_directory(frontmatter, skill_dir):
    name = re.search(r"^name:\s*(\S+)\s*$", frontmatter, re.M)
    assert name, "frontmatter has no name"
    value = name.group(1)
    assert re.fullmatch(r"[a-z0-9-]+", value), f"name {value!r} is not kebab-case"
    assert value == os.path.basename(skill_dir), (
        f"name {value!r} does not match directory {os.path.basename(skill_dir)!r}")


def test_every_reference_is_reachable(skill_md, skill_dir):
    """Reachable means named directly, or inside a directory SKILL.md names.

    A per-file check would flag all of references/style-guide/, which SKILL.md
    deliberately presents as one directory - the right way to offer bulk prose.

    The references/ root itself never gets that shortcut. Unlike a nested
    directory, its own name is a prefix substring of every path inside it
    ("references" is contained in "references/style-checklist.md"), so a plain
    `rel_dir in skill_md` check would always read the root as "named" the
    moment any file inside it is mentioned anywhere - blinding the check for
    every top-level file, orphans included.
    """
    refs = os.path.join(skill_dir, "references")
    unreachable = []
    for root, _dirs, files in os.walk(refs):
        rel_dir = os.path.relpath(root, skill_dir)
        dir_named = root != refs and rel_dir.replace(os.sep, "/") in skill_md
        for f in files:
            if f.startswith("."):
                continue
            if not dir_named and f not in skill_md:
                unreachable.append(os.path.join(rel_dir, f))
    assert not unreachable, (
        "\n\nHEADS UP - these reference files are unreachable from SKILL.md:\n"
        + "\n".join(f"    - {p}" for p in unreachable)
        + "\n\nEither name them, or say when to read the directory holding them.\n")


def test_reference_mentions_carry_a_load_condition(skill_md):
    """Telling the agent WHEN to load a file matters more than listing it.

    Checked per reference path, not per individual mention: a file can be
    introduced once with a clear load condition (e.g. in a "read these before
    you start" list) and referenced again later in workflow prose without
    repeating it. Requiring every single mention to independently carry a cue
    word would flag that second, later mention as a gap even though the agent
    was already told when to read the file.
    """
    cues = ("read", "consult", "before", "when", "if ", "see ")
    has_cue = {}
    for m in re.finditer(r"`references/[\w./-]+`", skill_md):
        window = skill_md[max(0, m.start() - 260): m.end() + 260].lower()
        ref = m.group(0)
        has_cue[ref] = has_cue.get(ref, False) or any(c in window for c in cues)
    missing = [ref for ref, ok in has_cue.items() if not ok]
    assert not missing, (
        "\n\nHEADS UP - these references are listed with no load condition:\n"
        + "\n".join(f"    - {r}" for r in sorted(missing))
        + "\n\nSay when to read each one, e.g. 'read X before you start'.\n")


def test_no_absolute_home_paths_in_shipped_files(skill_dir):
    offenders = []
    for root, dirs, files in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "fixtures")]
        for f in files:
            if not f.endswith((".md", ".py", ".json", ".sh", ".txt")):
                continue
            p = os.path.join(root, f)
            text = open(p, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r"/(?:Users|home)/[A-Za-z][\w.-]+/", text):
                offenders.append(f"{os.path.relpath(p, skill_dir)}: {m.group(0)}")
    assert not offenders, (
        "\n\nHEADS UP - absolute home paths make the skill unusable for anyone else:\n"
        + "\n".join(f"    - {o}" for o in offenders) + "\n")


def test_no_placeholders_in_shipped_files(skill_dir):
    offenders = []
    for root, dirs, files in os.walk(skill_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests")]
        for f in files:
            if not f.endswith((".md", ".py", ".json")):
                continue
            p = os.path.join(root, f)
            for i, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
                if re.search(r"\b(TODO|FIXME|TBD)\b", line):
                    offenders.append(f"{os.path.relpath(p, skill_dir)}:{i}")
    assert not offenders, (
        "\n\nHEADS UP - placeholders left in files that ship to users:\n"
        + "\n".join(f"    - {o}" for o in offenders) + "\n")


def test_deterministic_work_lives_in_scripts(skill_dir):
    """Mechanical steps belong in a script the agent runs, not in prose."""
    tool = os.path.join(skill_dir, "scripts", "twbx_tool.py")
    assert os.path.isfile(tool), "scripts/twbx_tool.py is the skill's engine"
    assert os.access(tool, os.R_OK)
