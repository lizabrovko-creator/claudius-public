"""The full clone → extract → pack → validate cycle on a real .twbx."""
import hashlib
import os
import zipfile

from rules import BASE


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def test_clone_leaves_the_source_byte_identical(run_cli, make_twbx, tmp_path):
    """Workflow step 9: the source in dummy/ must remain untouched."""
    src = make_twbx(BASE)
    before = _sha(src)

    r = run_cli("clone", src, "--results", str(tmp_path / "results"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert _sha(src) == before, "HEADS UP - clone modified the source"


def test_clone_prints_the_contract_line(run_cli, make_twbx, tmp_path):
    """SKILL.md step 2 parses the output by the RESULT= prefix."""
    src = make_twbx(BASE)
    r = run_cli("clone", src, "--results", str(tmp_path / "results"))
    line = [l for l in r.stdout.splitlines() if l.startswith("RESULT=")]
    assert line, f"no RESULT= line: {r.stdout!r}"
    assert os.path.isfile(line[0].split("=", 1)[1])


def test_clone_name_is_timestamped(run_cli, make_twbx, tmp_path):
    src = make_twbx(BASE, name="report.twbx")
    r = run_cli("clone", src, "--results", str(tmp_path / "results"))
    dest = r.stdout.split("RESULT=", 1)[1].strip()
    assert "__report.twbx" in os.path.basename(dest)


def test_extract_prints_contract_lines(run_cli, make_twbx, tmp_path):
    """SKILL.md step 3 reads TWB=, EOL=, and ZONES=."""
    pkg = make_twbx(BASE, eol="crlf")
    r = run_cli("extract", pkg, str(tmp_path / "wd"))
    assert r.returncode == 0, r.stdout + r.stderr
    for key in ("WORKDIR=", "TWB=", "EOL=", "ZONES="):
        assert key in r.stdout, f"no {key} in extract's output"
    assert "EOL=crlf" in r.stdout


def test_full_roundtrip_preserves_bytes_of_the_twb(run_cli, make_twbx, tmp_path):
    """With no edits, the cycle must be byte-identical at the .twb level."""
    pkg = make_twbx(BASE, eol="crlf")
    wd = tmp_path / "wd"
    assert run_cli("extract", pkg, str(wd)).returncode == 0
    original = open(wd / "wb.twb", "rb").read()

    out = tmp_path / "out.twbx"
    assert run_cli("pack", str(wd), str(out)).returncode == 0

    with zipfile.ZipFile(out) as z:
        assert z.read("wb.twb") == original, "the cycle altered the .twb"


def test_packed_result_is_a_readable_zip(run_cli, make_twbx, tmp_path):
    pkg = make_twbx(BASE)
    wd = tmp_path / "wd"
    run_cli("extract", pkg, str(wd))
    out = tmp_path / "out.twbx"
    run_cli("pack", str(wd), str(out))

    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None


def test_packaged_images_survive_the_roundtrip(run_cli, make_twbx, tmp_path):
    """Header icons live in Image/ - pack must not lose them."""
    pkg = make_twbx(BASE, images={"Image/logo.png": b"\x89PNG\r\n\x1a\n"})
    wd = tmp_path / "wd"
    run_cli("extract", pkg, str(wd))
    out = tmp_path / "out.twbx"
    run_cli("pack", str(wd), str(out))

    with zipfile.ZipFile(out) as z:
        assert "Image/logo.png" in z.namelist()
        assert z.read("Image/logo.png").startswith(b"\x89PNG")


def test_validate_reports_missing_packaged_asset(run_cli, make_twbx, tmp_path):
    """A reference to an image that is not in the package is a finding."""
    twb = BASE.replace("<zone id='1'/>", "<zone id='1' param='Image/nope.png'/>")
    pkg = make_twbx(twb)
    r = run_cli("validate", pkg)
    assert r.returncode == 1
    assert "missing packaged asset" in r.stdout


def test_validate_rejects_a_non_zip(run_cli, tmp_path):
    fake = tmp_path / "fake.twbx"
    fake.write_text("this is not an archive", encoding="utf-8")
    r = run_cli("validate", str(fake))
    assert r.returncode == 1
    assert "not a zip" in r.stdout


def test_validate_rejects_package_without_twb(run_cli, tmp_path):
    pkg = tmp_path / "empty.twbx"
    with zipfile.ZipFile(pkg, "w") as z:
        z.writestr("Image/x.png", b"x")
    r = run_cli("validate", str(pkg))
    assert r.returncode == 1
    assert "no .twb inside" in r.stdout


def test_validate_rejects_malformed_xml(run_cli, make_twbx):
    pkg = make_twbx("<workbook><unclosed></workbook>")
    r = run_cli("validate", pkg)
    assert r.returncode == 1
    assert "not well-formed" in r.stdout


def test_validate_pass_line_carries_the_invariant_count(run_cli, tool, tmp_path):
    """SKILL.md requires showing a PASS line - its format is part of the contract."""
    clean = tmp_path / "clean.twb"
    clean.write_text(
        "<?xml version='1.0' encoding='utf-8' ?>"
        "<workbook source-build='2026.2' version='18.1' locale='en_GB'/>",
        encoding="utf-8", newline="")
    r = run_cli("validate", str(clean))
    assert r.returncode == 0, r.stdout
    assert "PASS" in r.stdout
    assert f"{len(tool.INVARIANTS)} invariants" in r.stdout


def test_missing_file_is_reported_not_crashed(run_cli):
    r = run_cli("validate", "/nope/nope.twbx")
    assert r.returncode != 0
    assert "not found" in r.stdout + r.stderr
