#!/usr/bin/env bash
# Copy agentfeed/ into a visualization repo as vendor/agentfeed/, with a PIN
# naming the agentviz commit it came from. Run from anywhere:
#   tools/vendor-feed.sh /path/to/agentviz-office
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
dest="${1:?usage: vendor-feed.sh <viz repo>}"
rm -rf "$dest/vendor/agentfeed"
mkdir -p "$dest/vendor"
cp -r "$here/agentfeed" "$dest/vendor/agentfeed"
find "$dest/vendor/agentfeed" -name '__pycache__' -prune -exec rm -rf {} +
sha="$(git -C "$here" rev-parse HEAD 2>/dev/null || echo unknown)"
dirty=""; git -C "$here" diff --quiet HEAD -- agentfeed 2>/dev/null || dirty="-dirty"
echo "${sha}${dirty}" > "$dest/vendor/agentfeed/PIN"
echo "vendored agentfeed ${sha}${dirty} into $dest/vendor/agentfeed"
