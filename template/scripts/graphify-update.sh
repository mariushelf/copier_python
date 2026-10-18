#!/bin/sh
# Rebuild the graphify code graph (graphify-out/) for this worktree.
#
# Called by the pre-commit "graphify" hook after commit, checkout, merge and
# rewrite. Runs the AST-only update in the background and always exits 0, so
# it never slows down or breaks a git operation.

# Stops graphify from rewriting the global agent skill files with this
# project's pinned version.
export GRAPHIFY_NO_AUTO_REFRESH=1

command -v uv >/dev/null 2>&1 || exit 0
mkdir -p graphify-out 2>/dev/null || exit 0

# One build at a time per worktree. flock is missing on macOS: run unguarded.
if command -v flock >/dev/null 2>&1; then
    update='flock -n graphify-out/.update.lock uv run --frozen graphify update .'
else
    update='uv run --frozen graphify update .'
fi

# Detach from the git process: new session when setsid exists, no stdio.
if command -v setsid >/dev/null 2>&1; then
    setsid sh -c "$update" >graphify-out/update.log 2>&1 </dev/null &
else
    nohup sh -c "$update" >graphify-out/update.log 2>&1 </dev/null &
fi
exit 0
