"""The pack/clone guards - what stops a corrupted file from shipping.

Each one exists because of a real incident (see the comments in
twbx_tool.py). If a guard silently stops firing, the incident repeats,
and neither validate nor open-verify will notice - which is exactly why
they are checked here separately and by name.
"""
import os
import zipfile

import pytest

from rules import BASE


def _extracted(run_cli, make_twbx, tmp_path, **kw):
    """A real extract cycle: gives a workdir with a baseline sidecar."""
    pkg = make_twbx(BASE, **kw)
    wd = tmp_path / "wd"
    r = run_cli("extract", pkg, str(wd))
    assert r.returncode == 0, r.stdout + r.stderr
    return pkg, str(wd), os.path.join(str(wd), "wb.twb")


# ------------------------------------------------------- line endings ----
def test_pack_refuses_crlf_flattened_to_lf(run_cli, make_twbx, tmp_path):
    """An edit made without newline='' collapses CRLF to LF - the file stays
    valid and still opens, so only pack can catch this."""
    _, wd, twb = _extracted(run_cli, make_twbx, tmp_path, eol="crlf")

    flattened = open(twb, "rb").read().replace(b"\r\n", b"\n")
    open(twb, "wb").write(flattened)

    r = run_cli("pack", wd, str(tmp_path / "out.twbx"))
    assert r.returncode == 4, (
        "\nHEADS UP - pack no longer catches collapsed line endings.\n"
        f"Expected exit code 4, got {r.returncode}.\n{r.stdout}{r.stderr}"
    )
    assert "line endings changed" in r.stdout + r.stderr


def test_allow_eol_change_is_the_only_way_through(run_cli, make_twbx, tmp_path):
    _, wd, twb = _extracted(run_cli, make_twbx, tmp_path, eol="crlf")
    flattened = open(twb, "rb").read().replace(b"\r\n", b"\n")
    open(twb, "wb").write(flattened)

    r = run_cli("pack", wd, str(tmp_path / "out.twbx"), "--allow-eol-change")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "WARNING" in r.stdout, "a deliberate EOL substitution must be loud"


def test_untouched_crlf_packs_clean(run_cli, make_twbx, tmp_path):
    """The flip side: the guard does not get in the way of normal work."""
    _, wd, _ = _extracted(run_cli, make_twbx, tmp_path, eol="crlf")
    r = run_cli("pack", wd, str(tmp_path / "out.twbx"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PACKED=" in r.stdout


# ------------------------------------------------- content loss ----
@pytest.mark.parametrize("tag,needle", [
    ("worksheet", "<worksheet name="),
    ("datasource", "<datasource "),
    ("column", "<column "),
])
def test_pack_refuses_silent_element_loss(tag, needle, run_cli, make_twbx, tmp_path):
    """Rebuilding a block in a way that drops unfamiliar children is a silent
    loss. The file stays schema-valid, so only the counter catches it."""
    _, wd, twb = _extracted(run_cli, make_twbx, tmp_path)

    data = open(twb, "rb").read()
    assert needle.encode() in data, f"the fixture does not contain {needle!r}"
    open(twb, "wb").write(data.replace(needle.encode(), b"<gone ", 1))

    r = run_cli("pack", wd, str(tmp_path / "out.twbx"))
    assert r.returncode == 5, (
        f"\nHEADS UP - pack no longer catches a missing <{tag}>.\n"
        f"Expected exit code 5, got {r.returncode}.\n{r.stdout}{r.stderr}"
    )
    assert "disappeared since extract" in r.stdout + r.stderr


def test_adding_elements_is_allowed(run_cli, make_twbx, tmp_path):
    """The guard catches loss, not growth - otherwise the file could never be fixed."""
    _, wd, twb = _extracted(run_cli, make_twbx, tmp_path)
    data = open(twb, "rb").read()
    open(twb, "wb").write(
        data.replace(b"</worksheets>", b"<worksheet name='Sheet 2'/></worksheets>"))

    r = run_cli("pack", wd, str(tmp_path / "out.twbx"))
    assert r.returncode == 0, r.stdout + r.stderr


def test_allow_loss_escape_hatch(run_cli, make_twbx, tmp_path):
    _, wd, twb = _extracted(run_cli, make_twbx, tmp_path)
    data = open(twb, "rb").read()
    open(twb, "wb").write(data.replace(b"<column ", b"<gone ", 1))

    r = run_cli("pack", wd, str(tmp_path / "out.twbx"), "--allow-loss")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "deliberate removals" in r.stdout


# ------------------------------------------------------- read-only dummy ----
def test_clone_refuses_to_write_into_dummy(run_cli, make_twbx, tmp_path):
    """dummy/ is a read-only input per the skill's contract."""
    src = make_twbx(BASE)
    dummy = tmp_path / "dummy"
    dummy.mkdir()
    r = run_cli("clone", src, "--results", str(dummy))
    assert r.returncode != 0
    assert "dummy" in r.stdout + r.stderr


def test_pack_refuses_to_write_into_dummy(run_cli, make_twbx, tmp_path):
    _, wd, _ = _extracted(run_cli, make_twbx, tmp_path)
    dummy = tmp_path / "dummy"
    dummy.mkdir()
    r = run_cli("pack", wd, str(dummy / "out.twbx"))
    assert r.returncode != 0
    assert "dummy" in r.stdout + r.stderr


# ------------------------------------------------------------- sidecar ----
def test_sidecar_never_lands_inside_the_package(tool, run_cli, make_twbx, tmp_path):
    """extract's bookkeeping file must never end up inside the .twbx."""
    _, wd, _ = _extracted(run_cli, make_twbx, tmp_path)
    out = tmp_path / "out.twbx"
    assert run_cli("pack", wd, str(out)).returncode == 0

    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    assert tool.BASELINE_SIDECAR not in names, f"the sidecar ended up in the package: {names}"
    assert "wb.twb" in names
    assert os.path.isfile(os.path.join(wd, tool.BASELINE_SIDECAR)), \
        "the sidecar must stay in the workdir - pack checks against it"


def test_pack_refuses_workdir_without_twb(run_cli, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    r = run_cli("pack", str(empty), str(tmp_path / "out.twbx"))
    assert r.returncode != 0
    assert "no .twb" in r.stdout + r.stderr
