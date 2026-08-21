---
name: twbx-lint-test
description: Runs the twbx-lint test suite — the linter invariants, the pack/clone safety guards, the clone-extract-pack-validate round trip, bundled assets, manifests, portability and the SKILL.md contract. Use after changing anything inside the twbx-lint skill to see what stopped working.
disable-model-invocation: true
---

# /upstars:twbx-lint-test — check the skill

Argument: `$ARGUMENTS` — optional pytest flags (`-k guards`, `-v`, `-x`, a file
name). Empty runs everything.

Run exactly this. `${CLAUDE_PLUGIN_ROOT}` resolves the script relative to
this skill's own plugin, so the same command works from a checkout of the
repo and from an installed copy — there is no "repo root" for the latter:

```
"${CLAUDE_PLUGIN_ROOT}/skills/twbx-lint/tests/run.sh" $ARGUMENTS
```

Show the user the result before changing anything.

## Reading the output

Exit codes: `0` clean · `1` tests failed · `3` skill structure broken — a
malformed frontmatter, which loads the skill with empty metadata and stops it
working at all.

Failures are phrased as "HEADS UP — …" and already name what stopped working.
Three common shapes:

- **a rule is no longer caught** — either the check in `scripts/twbx_tool.py`
  broke, or the message text changed and the regex in `tests/rules.py` needs
  updating;
- **an invariant is uncovered** — a rule was added to `INVARIANTS` without a
  fixture; add an entry to `tests/rules.py`;
- **a guard went quiet** — `pack` stopped catching flattened line endings or lost
  elements. This is the worst case: such files pass every other check and are
  still corrupt.

## Report

```
twbx-lint tests: <N passed / M failed> in <T>s
Broken: <what stopped working, or "—">
Cause: <file and what changed in it, if visible>
```

One line if everything is green. Do not restate the list of tests.
