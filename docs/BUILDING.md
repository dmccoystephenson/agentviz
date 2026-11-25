# Building a visualization on Strata

Every visualization is a Strata **web kit** scene: one C++ file that includes
`strata_kit.h`, built to `<name>.js` + `<name>.wasm`, plus a page that polls
`/api/agents` and hands the scene what to draw through a few exported
functions. The built files are committed so serving needs only Python.

## Pins

| What | Value |
|---|---|
| Strata | **0.10.0** wasm release (`strata-0.10.0-wasm32-emscripten.tar.gz`, kit 1.3, ABI 1.18) |
| SHA-256 | `bb86b974c7e0309db91625ba5ee157273704c77d93f4338c8a63ee625e3d56de` |
| emsdk | 6.0.11 at `/root/emsdk` (must match Strata's) |

The tarball carries the kit in `kit/` (`build-kit.sh`, `strata_kit.h`,
`strata-kit.js`, `strata-loader.js`, `example/`). Read its `WEB.md`,
section "The web kit", and copy the shape of `kit/example/`.

## Recipe

```bash
. /root/agentviz/tools/emsdk-env.sh          # emcc 6.0.11, EMSDK_PYTHON trap handled
gh release download v0.10.0 -R Preponderous-Software/strata \
   -p 'strata-0.10.0-wasm32-emscripten.tar.gz' -D .strata
tar -xzf .strata/strata-0.10.0-wasm32-emscripten.tar.gz -C .strata
STRATA_TARBALL=.strata/strata-0.10.0-wasm32-emscripten.tar.gz \
STRATA_SHA256=bb86b974c7e0309db91625ba5ee157273704c77d93f4338c8a63ee625e3d56de \
  .strata/kit/build-kit.sh scene/kit.conf     # ~20 s
```

`.strata/` is gitignored; `scene/build.sh` wraps the above. Output goes to
`web/`. `KIT_EXPORTS` lists the scene's own `_xx_set_*` functions.

## Conventions

- Scene state comes ONLY from `/api/agents` (docs/FEED.md). Key by `id`,
  ease between snapshots, never rebuild everything per poll.
- `waiting` (needs the owner) must be unmissable. Followers (subagents) must
  read as belonging to their lead.
- Labels: use the kit's world labels / `StrataKit.placeLabels`.
- Mobile is first-class: touch orbit/pinch from the kit; tap = select, and a
  bottom sheet shows the selected agent's name, state, action and label.
- `?fixture=1` shows the demo feed; `?fps=1` shows the kit's frame stats.
- Playwright: /root/arcade-watch/node_modules is gone; use `NODE_PATH=/root/casework/node_modules` (any node_modules with Playwright).
- Headless Chromium (SwiftShader) is far slower than a real GPU: never judge
  performance from it.
