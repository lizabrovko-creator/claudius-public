"""Every invariant is still caught."""
import re

import pytest

from rules import RULES


@pytest.mark.parametrize("invariant", sorted(RULES))
def test_rule_is_still_detected(invariant, issues_of):
    xml, pattern = RULES[invariant]
    found = issues_of(xml)
    assert any(re.search(pattern, i) for i in found), (
        f"\n\nHEADS UP - rule '{invariant}' is no longer caught.\n"
        f"Expected a message matching /{pattern}/, the validator returned:\n"
        + ("\n".join(f"    · {i[:120]}" for i in found) or "    (nothing)")
        + "\n\nEither you broke the check in twbx_tool.py, or the rule moved -\n"
          "in that case, fix the regex in tests/rules.py.\n"
    )


def test_clean_workbook_is_not_flagged_for_absent_rules(issues_of):
    """The flip side: the validator does not invent findings out of thin air."""
    minimal = (
        "<?xml version='1.0' encoding='utf-8' ?>"
        "<workbook source-build='2026.2' version='18.1' locale='en_GB'/>"
    )
    found = issues_of(minimal)
    assert not any("duplicate" in i for i in found), found
    assert not any("off-palette" in i for i in found), found
