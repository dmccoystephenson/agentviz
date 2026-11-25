#!/usr/bin/env bash
# Vendors agentfeed/ and kit/ into a visualization repo, each with a PIN
# (line 1: the agentviz commit, line 2: sha256 of the copy), and copies the
# kit's page files (kit/web/*) into the repo's web/, where the page loads them.
# Run from anywhere:
#   tools/vendor-kit.sh /path/to/agentviz-office
# The viz repo checks its copies with: python3 vendor/agentviz-kit/check_vendor.py
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
dest="${1:?usage: vendor-kit.sh <viz repo>}"
sha="$(git -C "$here" rev-parse HEAD 2>/dev/null || echo unknown)"

vendor_one() {  # <source dir in agentviz> <name under vendor/>
  local src="$1" name="$2" target="$dest/vendor/$2" dirty=""
  [ -z "$(git -C "$here" status --porcelain -- "$src" 2>/dev/null)" ] || dirty="-dirty"
  rm -rf "$target"
  mkdir -p "$dest/vendor"
  cp -r "$here/$src" "$target"
  find "$target" -name '__pycache__' -prune -exec rm -rf {} +
  printf '%s%s\nsha256:%s\n' "$sha" "$dirty" "$(python3 "$here/kit/check_vendor.py" --digest "$target")" > "$target/PIN"
  echo "vendored $src ${sha}${dirty} into $target"
}

vendor_one agentfeed agentfeed
vendor_one kit agentviz-kit
mkdir -p "$dest/web"
cp "$here"/kit/web/* "$dest/web/"
echo "copied kit/web/* into $dest/web/"
