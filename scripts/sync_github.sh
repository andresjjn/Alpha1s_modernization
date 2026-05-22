#!/usr/bin/env bash
# sync_github.sh
# Utility script for syncing the repository to GitHub.
# PLACEHOLDER — fill in your remote URL and branch before use.
#
# Usage: ./scripts/sync_github.sh [commit message]

set -e

BRANCH="main"
MSG="${1:-chore: sync}"

echo "[sync] Staging all changes..."
git add -A

echo "[sync] Committing: '$MSG'"
git commit -m "$MSG" || echo "[sync] Nothing to commit."

echo "[sync] Pushing to origin/$BRANCH..."
git push origin "$BRANCH"

echo "[sync] Done."
