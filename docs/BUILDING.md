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
| emsdk | 6.0.11 (must match Strata's), activated or pointed to by `$EMSDK` |

The tarball carries the kit in `kit/` (`build-kit.sh`, `strata_kit.h`,
`strata-kit.js`, `strata-loader.js`, `example/`). Read its `WEB.md`,
section "The web kit", and copy the shape of `kit/example/`.

## Recipe

```bash
EMSDK=/path/to/emsdk vendor/agentviz-kit/scene/build-scene.sh scene/kit.conf   # ~20 s
```

`build-scene.sh` (from the vendored kit, docs/KIT.md) downloads the tarball
from the public release into `.strata/` (gitignored) once, checks the SHA-256
above, activates emsdk from `$EMSDK` and runs the tarball's
`kit/build-kit.sh` with the repo's `scene/kit.conf`. Output goes to `web/`.
With the kit's wire format, `KIT_EXPORTS=_agentviz_frame` is the only export
a scene needs.

## Conventions

- Scene state comes ONLY from `/api/agents` (docs/FEED.md), through the
  kit's `AgentvizFeed`. Key by `id`, ease between snapshots, never rebuild
  everything per poll.
- `waiting` (needs the owner) must be unmissable. Followers (subagents) must
  read as belonging to their lead.
- Labels: `AgentvizScreen.labels` + `StrataKit.placeLabels`. Feed strings
  go into the DOM as text only, never `innerHTML`.
- Mobile is first-class: touch orbit/pinch from the Strata kit; tap = select,
  and the agentviz HUD's bottom sheet shows the selected agent.
- `?fixture=1` shows the demo feed; `?fps=1` shows the kit's frame stats.
- Browser tests: a `package.json` pinning `playwright` 1.61.1, `npm ci`,
  `npx playwright install chromium`, and the kit's `tests/harness.cjs`.
- Headless Chromium (SwiftShader) is far slower than a real GPU: never judge
  performance from it.
