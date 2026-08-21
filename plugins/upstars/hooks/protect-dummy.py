#!/usr/bin/env python3
"""PreToolUse guard: makes the project's dummy/ directory read-only for Claude.

dummy/ is the inbox for source .twbx files. They may be READ (cat, unzip,
cp FROM dummy to elsewhere) but never modified, deleted, moved or written to.
All edits must go to a clone in results/ (see the /twbx-lint skill).

Contract (per https://code.claude.com/docs/en/hooks):
  - receives hook input JSON on stdin (tool_name, tool_input, cwd)
  - to block: print {"hookSpecificOutput": {"hookEventName": "PreToolUse",
    "permissionDecision": "deny", ...}} and exit 0
  - silent exit 0 = no decision, normal flow

Bash guarding is best-effort pattern matching; Edit/Write/NotebookEdit are
hard-blocked by resolved path. This is intentional defense in depth.
"""
import json
import os
import re
import shlex
import sys


# The inbox belongs to the user's project, not to the installed plugin, so
# resolve it from the hook payload's cwd (falling back to the process cwd).
def _dummy_dir(payload: dict) -> str:
    root = payload.get("cwd") or os.getcwd()
    return os.path.join(os.path.realpath(root), "dummy") + os.sep


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "dummy/ is a READ-ONLY inbox. " + reason +
                " Clone the file into results/ first (the /twbx-lint skill does this) "
                "and edit the clone."
            ),
        }
    }))
    sys.exit(0)


def path_in_dummy(path: str, cwd: str, root: str) -> bool:
    """`root` is dummy/'s directory path with a trailing separator (see
    `_dummy_dir`), so a plain prefix check also covers the dummy/ dir itself
    without matching a sibling like dummy-archive/."""
    if not path:
        return False
    p = os.path.expanduser(path)
    if not os.path.isabs(p):
        p = os.path.join(cwd, p)
    p = os.path.realpath(p)
    return (p + os.sep) == root or p.startswith(root)


# Commands whose mere *mention* of a dummy path is a write/destroy risk.
DESTRUCTIVE = {"rm", "rmdir", "mv", "shred", "truncate", "unlink", "touch",
               "chmod", "chown", "ln", "mkdir", "zip", "tar", "dd"}
# Commands where only the LAST argument (destination) being in dummy is a problem.
COPY_LIKE = {"cp", "rsync", "ditto", "install"}
# In-place editors: -i flag rewrites the file given as argument.
INPLACE = {"sed", "perl", "gsed"}


def bash_segment_denies(segment: str, cwd: str, root: str) -> str | None:
    seg = segment.strip()
    if not seg:
        return None
    # redirects into dummy: > path or >> path
    for m in re.finditer(r">{1,2}\s*([^\s;|&]+)", seg):
        if path_in_dummy(m.group(1).strip("'\""), cwd, root):
            return f"redirect writes into dummy/: `{seg}`"
    try:
        tokens = shlex.split(seg)
    except ValueError:
        tokens = seg.split()
    if not tokens:
        return None
    # strip leading VAR=... assignments and sudo/env wrappers
    while tokens and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]) or tokens[0] in {"sudo", "env", "command"}):
        tokens = tokens[1:]
    if not tokens:
        return None
    prog = os.path.basename(tokens[0])
    args = [t for t in tokens[1:]]
    non_flag = [t for t in args if not t.startswith("-")]
    if prog in DESTRUCTIVE:
        for t in non_flag:
            if path_in_dummy(t, cwd, root):
                return f"`{prog}` targets a dummy/ path"
    if prog in COPY_LIKE and non_flag:
        if path_in_dummy(non_flag[-1], cwd, root):
            return f"`{prog}` destination is inside dummy/"
    if prog in INPLACE and any(a == "-i" or a.startswith("-i") for a in args):
        for t in non_flag:
            if path_in_dummy(t, cwd, root):
                return f"in-place edit (`{prog} -i`) of a dummy/ file"
    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # malformed input: never block by accident
    root = _dummy_dir(payload)
    cwd = payload.get("cwd") or os.getcwd()
    tool = payload.get("tool_name", "")
    tin = payload.get("tool_input") or {}

    if tool in ("Edit", "Write", "MultiEdit"):
        fp = tin.get("file_path", "")
        if path_in_dummy(fp, cwd, root):
            deny(f"Attempted {tool} on {fp!r}.")
    elif tool == "NotebookEdit":
        fp = tin.get("notebook_path", "")
        if path_in_dummy(fp, cwd, root):
            deny(f"Attempted {tool} on {fp!r}.")
    elif tool == "Bash":
        cmd = tin.get("command", "") or ""
        if "dummy" in cmd:  # cheap pre-filter
            for segment in re.split(r"(?:&&|\|\||[;|\n])", cmd):
                reason = bash_segment_denies(segment, cwd, root)
                if reason:
                    deny(reason + f" (segment: `{segment.strip()}`).")
    sys.exit(0)


if __name__ == "__main__":
    main()
