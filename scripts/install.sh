#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_DIR="$HOME/.claude/skills/accuracy-tracker"
STALE_ZIP="$HOME/.claude/skills/accuracy-tracker.skill"

echo "📦 accuracy-tracker install/sync"
[ -f "$STALE_ZIP" ] && { echo "🗑️  removing stale $STALE_ZIP"; rm "$STALE_ZIP"; }
[ "${1:-}" = "--clean" ] && rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp "$REPO_DIR/SKILL.md" "$INSTALL_DIR/"
cp -R "$REPO_DIR/scripts" "$INSTALL_DIR/"
[ -d "$REPO_DIR/data" ] && cp -R "$REPO_DIR/data" "$INSTALL_DIR/"
VERSION=$(grep -m1 "^version:" "$INSTALL_DIR/SKILL.md" | awk '{print $2}')
echo "✅ installed accuracy-tracker v$VERSION — restart Claude Code to reload"
