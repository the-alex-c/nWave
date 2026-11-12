#!/usr/bin/env bash
# Capture state of stalled pi sessions. Read-only: never kills anything.
# Run it while the stall is happening, before you kill pi.
# Output: ~/stall-captures/<timestamp>/report.txt (one file per run, outside the repo).
#
# Usage: stall-capture.sh [SAMPLE_SECONDS]   (default 10; the socket and CPU are sampled twice)

set -u
SAMPLE=${1:-10}
OUT=~/stall-captures/$(date +%Y%m%d-%H%M%S)
mkdir -p "$OUT"
REPORT="$OUT/report.txt"

log() { printf '%s\n' "$*" | tee -a "$REPORT"; }
section() { log ""; log "=== $* ==="; }

log "stall-capture $(date -u +%Y-%m-%dT%H:%M:%SZ) (local: $(date))"
log "sample window: ${SAMPLE}s"

# 1. pi processes. Match on the command word: `pgrep -x pi` misses pi here (its process name is not 'pi').
PIDS=$(ps -axo pid=,command= | awk '$2=="pi" || $2 ~ /\/pi$/ {print $1}')
section "1. pi processes"
if [ -z "$PIDS" ]; then
  log "no pi process found"
  log "report: $REPORT"
  exit 0
fi
ps -o pid,ppid,etime,%cpu,stat,command -p $(echo $PIDS | tr ' ' ',') | tee -a "$REPORT"

# tmux pane lookup by pane_pid (helps find which tmux session/window owns the pi)
PANES=$(tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} pane_pid=#{pane_pid} cwd=#{pane_current_path}' 2>/dev/null || true)

for PID in $PIDS; do
  section "2. pid $PID: ancestry, cwd, tmux"
  p=$PID
  while [ -n "$p" ] && [ "$p" != 1 ] && [ "$p" != 0 ]; do
    ps -o pid=,ppid=,command= -p "$p" 2>/dev/null | cut -c1-160 | tee -a "$REPORT"
    pane=$(printf '%s\n' "$PANES" | grep "pane_pid=$p " || true)
    [ -n "$pane" ] && log "  tmux: $pane"
    p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
  done
  CWD=$(lsof -a -p "$PID" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)
  log "cwd: ${CWD:-unknown}"

  section "3. pid $PID: CPU and network, sampled twice"
  log "t0:"
  lsof -a -p "$PID" -i -n -P 2>/dev/null | tee -a "$REPORT"
  ps -o %cpu=,cputime=,stat= -p "$PID" | tee -a "$REPORT"
  sleep "$SAMPLE"
  log "t+${SAMPLE}s:"
  lsof -a -p "$PID" -i -n -P 2>/dev/null | tee -a "$REPORT"
  ps -o %cpu=,cputime=,stat= -p "$PID" | tee -a "$REPORT"
  log "(same socket and growing cputime: waiting or streaming. CPU flat at 0: idle on network.)"

  section "4. pid $PID: child processes (a running child means a tool is hung; pi-lens *-lsp/server children are long-lived and expected; a bash child running this script is you)"
  CHILDREN=$(ps -axo pid=,ppid= | awk -v p="$PID" '$2==p {print $1}')
  if [ -z "$CHILDREN" ]; then
    log "none"
  else
    ps -o pid,ppid,etime,stat,command -p $(echo $CHILDREN | tr ' ' ',') | tee -a "$REPORT"
  fi

  section "5. pid $PID: newest session, last entries"
  if [ -n "$CWD" ]; then
    SLUG="--$(echo "${CWD#/}" | tr '/' '-')--"
    DIR=~/.pi/agent/sessions/$SLUG
    if [ -d "$DIR" ]; then
      FILE=$(ls -t "$DIR"/*.jsonl 2>/dev/null | head -1)
      log "dir: $DIR"
      log "file: ${FILE:-none}"
      if [ -n "${FILE:-}" ]; then
        log "copy: $OUT/session-last.jsonl (last 200 lines)"
        tail -n 200 "$FILE" > "$OUT/session-last.jsonl"
        python3 - "$FILE" <<'EOF' | tee -a "$REPORT"
import json, sys, datetime as dt
ev = []
for line in open(sys.argv[1]):
    try:
        ev.append(json.loads(line))
    except Exception:
        pass
msgs = [e for e in ev if e.get("type") == "message" and e.get("timestamp")]
now = dt.datetime.now(dt.timezone.utc)
print(f"entries: {len(msgs)}")
for e in msgs[-5:]:
    m = e["message"]
    c = m.get("content")
    tools = [x.get("name") for x in c if isinstance(x, dict) and x.get("type") == "toolCall"] if isinstance(c, list) else []
    print(f"  {e['timestamp']} {m.get('role')} stop={m.get('stopReason')} tools={tools}")
if msgs:
    last = dt.datetime.fromisoformat(msgs[-1]["timestamp"].replace("Z", "+00:00"))
    print(f"last entry age: {int((now - last).total_seconds())} s")
    m = msgs[-1]["message"]
    if m.get("role") == "assistant" and m.get("stopReason") == "toolUse":
        print("STATE: last entry is toolUse with no result -> a tool is pending")
    elif m.get("role") == "user":
        print("STATE: last entry is user with no reply -> model request pending")
    else:
        print("STATE: last entry is a completed assistant turn")
EOF
      fi
    else
      log "no session dir for cwd slug: $SLUG"
    fi
  else
    log "cwd unknown; cannot find session"
  fi
done

section "done"
log "report: $REPORT"
