#!/usr/bin/env bash
# Tiers 1-2 for the twbx-lint skill. No Tableau, no network, no LLM.
#
#   ./run.sh                 everything
#   ./run.sh -k guards       one group
#   ./run.sh -v              with test names
#
# Exit: 0 clean | 1 tests failed | 3 skill structure broken
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_DIR="$(cd "$SKILL_DIR/../.." && pwd)"
REPO_ROOT="$(cd "$PLUGIN_DIR/../.." && pwd)"

# In the repo, cd to the root so pytest.ini is picked up. Installed, there is no
# repo: PLUGIN_DIR sits in Claude Code's plugin cache, so REPO_ROOT is just the
# cache directory, and cd-ing there would make pytest collect every OTHER
# plugin's tests. Either way, name our own tests explicitly rather than trusting
# the working directory to mean something.
if [[ -f "$REPO_ROOT/pytest.ini" ]]; then
  cd "$REPO_ROOT" || exit 1
fi

if ! python3 -c "import pytest" 2>/dev/null; then
  echo "pytest is missing. Install it: python3 -m pip install pytest" >&2
  exit 1
fi

# Tier 1: a broken frontmatter loads the skill with empty metadata, silently,
# so no test below would ever notice.
if command -v claude >/dev/null 2>&1; then
  if ! out=$(claude plugin validate --strict "$PLUGIN_DIR" 2>&1); then
    echo "-- plugin structure ------------------------------" >&2
    echo "$out" >&2
    exit 3
  fi
  echo "plugin structure: OK"
fi

# Tier 2
python3 -m pytest "$SKILL_DIR/tests" "$@"
