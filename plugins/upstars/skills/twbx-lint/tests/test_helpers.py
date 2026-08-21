"""Pure functions and registries - the cheapest and most precise coverage."""
import pytest


# --------------------------------------------------------- title case ----
@pytest.mark.parametrize("caption", [
    "Project", "VIP Status", "Net Gaming Revenue", "NGR", "GGR/NGR",
    "Player ID", "Deposit Amount (USD)", "AR", "RFD",
    "Sum of NGR", "Country ",           # trailing space - a deliberate distinguisher
])
def test_title_case_accepts(tool, caption):
    assert tool._title_case_ok(caption), f"{caption!r} should pass"


@pytest.mark.parametrize("caption", [
    "my project name", "net gaming revenue", "Sum of ngr amount",
    "player identifier", "deposit amount",
])
def test_title_case_rejects(tool, caption):
    assert not tool._title_case_ok(caption), f"{caption!r} should fail"


def test_short_words_are_exempt(tool):
    """Words shorter than 3 letters are left alone - 'of', 'by', 'in'."""
    assert tool._title_case_ok("Revenue by Country")
    assert tool._title_case_ok("Sum of Deposits")


def test_every_declared_acronym_is_honoured(tool):
    """An acronym from the registry passes in ANY case.

    The lowercase form specifically must be checked: uppercase 'NGR' passes
    even without the registry - its first letter is already capitalized -
    so a test against 'NGR' would not exercise the exemption, and would not
    notice if it were disabled.
    """
    bad = [a for a in tool.TITLE_CASE_ACRONYMS
           if not tool._title_case_ok(a.lower())]
    assert not bad, (
        "\nHEADS UP - acronyms are declared but the rule does not exempt them:\n"
        + "\n".join(f"    · {a.lower()}" for a in bad)
        + "\n\nLooks like the TITLE_CASE_ACRONYMS branch was removed from _title_case_ok.\n"
    )


def test_acronym_exemption_is_word_scoped(tool):
    """The exemption applies per word, not to the whole caption."""
    assert tool._title_case_ok("Sum of ngr"), "an acronym inside a phrase"
    assert not tool._title_case_ok("vip status"), (
        "'status' is an ordinary word, the registry does not cover it"
    )


# ------------------------------------------------------------ profile ----
@pytest.mark.parametrize("raw,expected", [
    (b"a\r\nb\r\n", "crlf"),
    (b"a\nb\n", "lf"),
    (b"a\r\nb\n", "mixed"),
    (b"abc", "none"),
])
def test_eol_detection(tool, tmp_path, raw, expected):
    p = tmp_path / "x.twb"
    p.write_bytes(raw)
    assert tool._twb_profile(str(p))["eol"] == expected


def test_profile_reads_bytes_not_text(tool, tmp_path):
    """Python's text mode hides CRLF - the profiler must read bytes."""
    p = tmp_path / "x.twb"
    p.write_bytes(b"<zone />\r\n<zone />\r\n")
    prof = tool._twb_profile(str(p))
    assert prof["eol"] == "crlf" and prof["crlf"] == 2 and prof["lf"] == 0


def test_profile_counts_zones(tool, tmp_path):
    p = tmp_path / "x.twb"
    p.write_bytes(b"<zone id='1'/><zone id='2'/><zones>")
    assert tool._twb_profile(str(p))["zones"] == 2


def test_profile_tracks_every_preserve_tag(tool, tmp_path):
    """The counter must count every declared tag, not a subset."""
    p = tmp_path / "x.twb"
    p.write_bytes(b"".join(v for v in tool.PRESERVE_TAGS.values()))
    got = tool._twb_profile(str(p))["preserve"]
    missed = [k for k in tool.PRESERVE_TAGS if got.get(k, 0) < 1]
    assert not missed, (
        "\nHEADS UP - tags are declared in PRESERVE_TAGS but are not being counted:\n"
        + "\n".join(f"    · {k}" for k in missed)
    )


# ------------------------------------------------------------ registries ----
def test_upstars_palette_loads_from_tps(tool):
    """The palette is read from Preferences.tps - the file and the parser must not drift apart."""
    colours = tool._upstars_colours()
    assert len(colours) >= 6, f"suspiciously few colours read from .tps: {colours}"
    assert all(c.startswith("#") and len(c) == 7 for c in colours)
    assert all(c == c.lower() for c in colours), "colours must be normalized"


def test_structural_colours_are_valid_hex(tool):
    bad = [c for c in tool.STRUCTURAL_COLOURS
           if not (c.startswith("#") and len(c) == 7)]
    assert not bad, bad


def test_style_attr_enum_parsed_from_xsd(tool):
    """The enumeration is taken from the XSD; empty means the schema or the regex broke."""
    enum = tool._style_attr_enum()
    assert enum, "HEADS UP - StyleAttribute was not read from the XSD"
    assert "font-family" in enum
    assert "font-name" not in enum, "font-name is the exact trap described in references"


def test_zoom_types_registry_is_populated(tool):
    assert tool.ZOOM_TYPES, "ZOOM_TYPES is empty - the fit check would become useless"


def test_placeholders_registry_is_populated(tool):
    assert len(tool.PLACEHOLDERS) >= 4


# ------------------------------------------------------------ sidecar ----
def test_load_baseline_returns_none_for_foreign_workdir(tool, tmp_path):
    assert tool._load_baseline(str(tmp_path)) is None


def test_load_baseline_survives_corrupt_sidecar(tool, tmp_path):
    """A corrupt sidecar must not crash pack - only disable the comparison."""
    (tmp_path / tool.BASELINE_SIDECAR).write_text("{not json", encoding="utf-8")
    assert tool._load_baseline(str(tmp_path)) is None
