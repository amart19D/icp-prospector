#!/bin/bash
# Run ICP prospector and send an openclaw system event when done
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$SCRIPT_DIR/output/run.log"
REPORT="$SCRIPT_DIR/output/last-run-report.md"

cd "$SCRIPT_DIR"
mkdir -p output

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting ICP prospector run..." | tee "$LOG"

python3 -m prospector run >> "$LOG" 2>&1
EXIT_CODE=$?

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Run complete (exit=$EXIT_CODE)" >> "$LOG"

# Extract summary from report
SUMMARY=$(grep -A 20 "## Sources" "$REPORT" 2>/dev/null | head -25 || echo "No report generated")

# Notify via openclaw system event
openclaw system event --text "ICP Prospector run finished (exit=$EXIT_CODE). Report at $REPORT. Summary: $SUMMARY" --mode now 2>/dev/null || true

echo "Done. Log: $LOG"
