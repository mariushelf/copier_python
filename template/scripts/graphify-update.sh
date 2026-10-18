#!/bin/sh
# Rebuild the graphify code graph (graphify-out/) for this worktree.
#
# Called by the pre-commit "graphify" hook after commit, checkout, merge and
# rewrite. Needs a POSIX sh. Always exits 0 so it never breaks a git operation.
#
# Every call marks the worktree "dirty" and starts a detached worker. Only one
# worker per worktree holds the lock (a mkdir lock, portable to macOS); it
# rebuilds until nothing marked the tree dirty meanwhile, so the final graph
# always reflects the latest trigger.
#
# GRAPHIFY_UPDATE_FOREGROUND=1 runs the worker inline (for tests).

# Stops graphify from rewriting the global agent skill files with this
# project's pinned version.
export GRAPHIFY_NO_AUTO_REFRESH=1

out=graphify-out
lock=$out/.lock
dirty=$out/.dirty
log=$out/update.log
stale_minutes=10
max_log_bytes=100000

say() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$log"; }

trim_log() {
    size=$(wc -c <"$log" 2>/dev/null || echo 0)
    if [ "${size:-0}" -gt "$max_log_bytes" ]; then
        tail -n 200 "$log" >"$log.tmp" 2>/dev/null && mv "$log.tmp" "$log"
    fi
}

# Take the lock, clearing it first when its holder is dead or it is too old.
acquire() {
    mkdir "$lock" 2>/dev/null && { echo $$ >"$lock/pid"; return 0; }
    pid=$(cat "$lock/pid" 2>/dev/null)
    if { [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; } ||
        [ -n "$(find "$lock" -maxdepth 0 -mmin +"$stale_minutes" 2>/dev/null)" ]; then
        say "removing stale lock (holder ${pid:-unknown})"
        rm -rf "$lock"
        mkdir "$lock" 2>/dev/null && { echo $$ >"$lock/pid"; return 0; }
    fi
    return 1
}

worker() {
    while acquire; do
        trap 'rm -rf "$lock"' EXIT
        while [ -f "$dirty" ]; do
            rm -f "$dirty"
            say "update start"
            if uv run --frozen graphify update . >>"$log" 2>&1; then
                say "update done"
            else
                say "update failed (exit $?)"
            fi
            trim_log
        done
        rm -rf "$lock"
        trap - EXIT
        # A trigger may have arrived between the last check and the release.
        [ -f "$dirty" ] || return 0
    done
}

if [ "$1" = "--worker" ]; then
    worker
    exit 0
fi

command -v uv >/dev/null 2>&1 || exit 0
mkdir -p "$out" 2>/dev/null || exit 0

if [ ! -f uv.lock ]; then
    say "no uv.lock in this checkout; skipping (run 'uv lock' to enable the graph)"
    exit 0
fi

touch "$dirty"
if [ -n "$GRAPHIFY_UPDATE_FOREGROUND" ]; then
    worker
elif command -v setsid >/dev/null 2>&1; then
    setsid sh "$0" --worker >/dev/null 2>&1 </dev/null &
else
    nohup sh "$0" --worker >/dev/null 2>&1 </dev/null &
fi
exit 0
