"""The coverage test - the one that says "heads up".

The skill declares its rules in INVARIANTS. This test watches that every
declared rule has a live fixture. Add a rule without adding a fixture, and
this test will name it by name.
"""
from rules import RULES


def test_every_invariant_has_a_fixture(tool):
    declared = set(tool.INVARIANTS)
    covered = set(RULES)

    uncovered = sorted(declared - covered)
    assert not uncovered, (
        f"\n\nHEADS UP - {len(uncovered)} of {len(declared)} invariants "
        f"are not covered by a test.\n"
        "The skill promises to check them, and there is no proof it does:\n"
        + "\n".join(f"    · {n}" for n in uncovered)
        + "\n\nAdd an entry to tests/rules.py for each one: a .twb that the rule\n"
          "violates, and a regex of the expected message.\n"
    )


def test_no_fixture_for_a_rule_the_skill_dropped(tool):
    """The flip side: a rule got cut from the skill, but the test stuck around and lies."""
    orphans = sorted(set(RULES) - set(tool.INVARIANTS))
    assert not orphans, (
        f"\n\nFixtures with no rule - they test something the skill no longer promises:\n"
        + "\n".join(f"    · {n}" for n in orphans)
        + "\n\nEither restore the rule to INVARIANTS, or remove the fixture.\n"
    )


def test_placeholders_registry_is_enforced(tool, issues_of):
    """Every PLACEHOLDER from the skill is actually caught, not just dead weight."""
    from rules import BASE
    missed = [
        ph for ph in tool.PLACEHOLDERS
        if not any(
            "template placeholder" in i
            for i in issues_of(BASE.replace("<run>Sheet 1</run>", f"<run>{ph}</run>"))
        )
    ]
    assert not missed, (
        "\n\nHEADS UP - these placeholders are declared but not detected:\n"
        + "\n".join(f"    · {p!r}" for p in missed) + "\n"
    )
