#!/usr/bin/env bash
# Kept for older docs: vendoring now copies agentfeed and the kit together.
exec "$(dirname "$0")/vendor-kit.sh" "$@"
