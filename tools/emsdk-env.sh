# Source this before building a scene:  . tools/emsdk-env.sh
# emsdk_env.sh needs python >= 3.10 and CLEARS EMSDK_PYTHON, so set it
# before AND after sourcing (trap noted in the Strata memory, 2026-10-24).
_py="$(ls -d "$HOME"/.local/share/uv/python/cpython-3.12*/bin/python3.12 2>/dev/null | head -1)"
export EMSDK_PYTHON="${EMSDK_PYTHON:-$_py}"
_keep="$EMSDK_PYTHON"
# shellcheck disable=SC1091
. "${EMSDK:-/root/emsdk}/emsdk_env.sh" >/dev/null 2>&1
export EMSDK_PYTHON="$_keep"
unset _py _keep
