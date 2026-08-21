"""Coverage registry: invariant -> the fixture that provokes it.

Each entry says: "here is a .twb that violates rule X, and here is what
the validator's message looks like." If a rule stops firing at all - the
check is deleted, the code path breaks, or the message text drifts far
enough to miss the regex - exactly this test fails and names the invariant.

What this does NOT pin, despite the name "coverage registry": the rule's
actual thresholds or boundaries. Every fixture violates its rule by a wide,
arbitrary margin, and each regex matches the message's fixed wording, not
the numbers embedded in it. Move a threshold - filter card height 50 -> 60,
the canvas width ceiling widened tenfold, an extra accepted <zoom type> -
and, as long as the same fixture still lands on the wrong side of the new
threshold, every test here keeps passing; verified live, all three of those
changes left all 159 tests green. There are also no negative (passing)
fixtures: nothing here confirms a *compliant* workbook is left unflagged.
Read a green run as "the rule still exists and still fires on this one
extreme violation" - not as "the rule's numbers are right" or "the rule
has no false positives."

To add a rule: add its name to INVARIANTS in scripts/twbx_tool.py, then add
an entry here. test_coverage.py will not let you forget the second step.
"""
import pathlib

BASE = (pathlib.Path(__file__).parent / "_base.twb").read_text(encoding="utf-8")


def _z(zone_xml: str) -> str:
    """Swap out the dashboard's single zone."""
    return BASE.replace("<zone id='1'/>", zone_xml)


# invariant -> (twb fixture, regex of the expected message)
RULES: dict[str, tuple[str, str]] = {
    "datasource child order": (
        BASE.replace("<connection class='hyper'/>\n      <column", "<column")
            .replace("caption='Project'/>", "caption='Project'/><connection class='hyper'/>"),
        r"violates content-model order",
    ),
    "dashboard zone id uniqueness": (
        _z("<zone id='1'/><zone id='1'/>"),
        r"duplicate zone ids",
    ),
    "worksheet name/uuid uniqueness": (
        BASE.replace("</worksheets>", "<worksheet name='Sheet 1'/></worksheets>"),
        r"duplicate worksheet names",
    ),
    "workbook locale": (
        BASE.replace("locale='en_GB'", "locale='en_US'"),
        r"locale is .*must be 'en_GB'",
    ),
    "viewpoint zoom type": (
        _z("<zone id='1'><zoom type='vscroll'/></zone>"),
        r"invalid <zoom type=",
    ),
    "dashboard viewpoint registration": (
        _z("<zone id='1' type-v2='paneZone' name='Sheet 1'/>"),
        r"missing from <viewpoints>",
    ),
    "off-palette colours": (
        _z("<zone id='1' param='#ab12cd'/>"),
        r"off-palette colour",
    ),
    "template placeholders": (
        BASE.replace("<run>Sheet 1</run>", "<run>Replace this object</run>"),
        r"template placeholder left",
    ),
    "caption title case": (
        BASE.replace("caption='Project'", "caption='my project name'"),
        r"is not Title Case",
    ),
    "filter card height": (
        _z("<zone id='1' type-v2='filter' param='[Project]' fixed-size='30' is-fixed='true'/>"),
        r"filter card\(s\) not 50px",
    ),
    "filter panel": (
        _z("<zone id='1' type-v2='filter' param='[Project]'/>"),
        r"filter panel has no 'FILTERS' caption",
    ),
    "action name pattern": (
        BASE.replace("</dashboards>",
                     "</dashboards><actions><action name='NotBracketed'/></actions>"),
        r"must match the bracketed",
    ),
    "packaged asset references": (
        _z("<zone id='1' param='Image/missing.png'/>"),
        r"missing packaged asset: Image/missing\.png",
    ),
    "format attr enumeration": (
        BASE.replace(
            "<worksheet name='Sheet 1'>",
            "<worksheet name='Sheet 1'><style><style-rule element='axis'>"
            "<format attr='font-name' value='x'/></style-rule></style>"),
        r"is not a valid StyleAttribute",
    ),
    "button toggle-action": (
        _z("<zone id='1'><toggle-action>bogus:thing</toggle-action></zone>"),
        r"toggle-action must be tabdoc:toggle-button-click-action",
    ),
    "dashboard viz fit = Standard": (
        BASE.replace(
            "</dashboards>",
            "</dashboards><windows><window class='dashboard' name='Dash'>"
            "<viewpoints><viewpoint name='Sheet 1'><zoom type='entire-view'/>"
            "</viewpoint></viewpoints></window></windows>"),
        r"fit is 'entire-view', must stay Standard",
    ),
    "canvas width": (
        BASE.replace("<zones>", "<size maxwidth='999' minwidth='999'/><zones>"),
        r"canvas width 999 outside 1200",
    ),
    "mark colour palette declared": (
        BASE.replace(
            "<layout-options>",
            "<table><panes><pane><encodings>"
            "<color column='[ds].[none:Project:nk]'/>"
            "</encodings></pane></panes></table><layout-options>"),
        r"with no palette declared",
    ),
    "tooltip typography": (
        BASE.replace(
            "</layout-options>",
            "</layout-options><customized-tooltip><formatted-text>"
            "<run fontname='Arial' fontsize='11' fontcolor='#000000'>t</run>"
            "</formatted-text></customized-tooltip>"),
        r"tooltip run is not Tableau Book/9/#333333",
    ),
    "legend beside its viz": (
        _z("<zone id='1' type-v2='color' name='Sheet 1'/>"),
        r"legend for 'Sheet 1' is not a sibling of its viz",
    ),
    "filter control mode": (
        _z("<zone id='1' type-v2='filter' mode='radiolist' "
           "fixed-size='50' is-fixed='true'/>"),
        r"mode='radiolist'",
    ),
    "parameter control typography": (
        _z("<zone id='1' type-v2='paramctrl'/>"),
        r"lacks 'parameter-ctrl' with Tableau Book 9",
    ),
    # These are already violated in the bare base - the absence itself is the violation.
    "dashboard header": (BASE, r"no header zone"),
    "update-time block": (BASE, r"no update-time worksheet"),
    "worksheet text styling": (BASE, r"style-rule '\w+' missing font-family"),
    "worksheet title run": (BASE, r"title run is"),
    "viz borders": (BASE, r"has no border-color='#f5f5f5'"),
}
