#!/usr/bin/env bash
# accuracy-tracker — install script (standard fleet template, S3-compliant)
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HOME/.claude/skills/accuracy-tracker"
STALE_ZIP="$HOME/.claude/skills/accuracy-tracker.skill"

echo "📦 accuracy-tracker install/sync"
echo "   source: $SRC"
echo "   target: $DEST"

# ─── Auto-validate SKILL.md against fleet schema v0.3 ───
VALIDATOR="$HOME/.claude/skills/future-proof/scripts/validate-skill.py"
if [ -f "$VALIDATOR" ]; then
  python3 "$VALIDATOR" --schema-version 0.3 "$SRC/SKILL.md" || {
    echo "❌ SKILL.md failed schema v0.3 validation — install aborted"
    exit 1
  }
fi
# ───────────────────────────────────────────────────────────

[ -f "$STALE_ZIP" ] && { echo "🗑️  removing stale $STALE_ZIP"; rm "$STALE_ZIP"; }
{ [ -L "$DEST" ] || [ -e "$DEST" ]; } && rm -rf "$DEST"

ln -s "$SRC" "$DEST"
VERSION=$(grep -m1 "^version:" "$SRC/SKILL.md" | awk '{print $2}')
echo "✅ accuracy-tracker v$VERSION installed as symlink → $SRC"
