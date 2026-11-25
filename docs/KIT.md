# The agentviz kit

Every visualization in the family needs the same things around its scene:
read the feed, show who needs you, show what was tapped, label the world,
pass the frame to the engine, build the wasm, and test the page. `kit/` is
that shared half, vendored into each viz repo next to `agentfeed`. A viz
keeps only its metaphor: the layout, the motion and the drawing.

| File | What it is for |
|---|---|
| `kit/web/agentviz-feed.js` | `AgentvizFeed`: polls `/api/agents` every 2 s (`?fixture=1` / `?demo=1` pick the demo feed), keys sessions and followers by id, reports added / removed / changed and new tool calls, backs off on failure with an explicit `"unreachable"` status. Also `fnv1a`, `seedOf` (identical to Python's `seed_of`), `ease`, `lerp`, `smoothstep`. |
| `kit/web/agentviz-hud.js` + `agentviz-hud.css` | `AgentvizHud`: top bar (title, "needs you" chip that cycles waiting sessions and says why each waits, counts, demo-feed badge, the page's buttons, legend toggle), unreachable banner, empty-state hint, and the selection panel (a card on desktop, a bottom sheet with a swipe-down grab on phones). |
| `kit/web/agentviz-screen.js` | `AgentvizScreen`: action icons, state dots, a keyed world-label pool for `StrataKit.placeLabels`, and nearest-point tap picking. |
| `kit/web/agentviz-wire.js` | `AgentvizWire`: packs one frame into a `Float32Array` (layout below) and hands it to the engine. |
| `kit/scene/agentviz.h` | Decodes that buffer in the scene; the vocabulary enums, `seed_of`, easing. Header-only C++17, no Strata dependency. |
| `kit/scene/build-scene.sh` | Downloads the pinned Strata 0.10.0 wasm tarball, checks its SHA-256, activates emsdk from `$EMSDK`, runs the tarball's `kit/build-kit.sh` with the repo's `scene/kit.conf`. |
| `kit/tests/harness.cjs`, `screens.cjs`, `make_gif.py` | Browser tests: Playwright from `NODE_PATH` or `./node_modules`, the fixture server started and killed by PID, console-error capture, CSS animations paused, the not-a-flat-frame check, README stills and a GIF (Pillow). |
| `kit/check_vendor.py` | Confirms the viz's vendored copies (and the page files served from `web/`) match their PINs. |

All feed strings reach the DOM through `textContent` or `createElement`,
never `innerHTML`: labels come from file names, Bash descriptions and
subagent descriptions. HUD parts re-render only when what they show changed,
so a button is never replaced under a finger between polls.

## Adopting it in a viz repo

1. Vendor: from the agentviz checkout, `tools/vendor-kit.sh /path/to/agentviz-<name>`.
   It writes `vendor/agentfeed/` and `vendor/agentviz-kit/` (each with a
   `PIN`: commit, then `sha256:` of the copy) and copies `kit/web/*` into the
   repo's `web/`. Never edit those copies; re-vendor. Add a test that runs
   `python3 vendor/agentviz-kit/check_vendor.py`.
2. Page: load, in order, `strata-loader.js`, `strata-kit.js`,
   `agentviz-feed.js`, `agentviz-screen.js`, `agentviz-hud.js`,
   `agentviz-wire.js`, then the viz's own scripts; link `agentviz-hud.css` and
   theme it by overriding the `--av-*` custom properties.

   ```js
   const hud = AgentvizHud.create({title: "Agent Office", legend: document.getElementById("legend"),
     buttons: [{icon: "home", label: "Recentre the view", onClick: fit}],
     onSelect(target, how) { /* highlight, fly the camera; how is "tap" | "list" | "waiting" | "api" */ }});
   const feed = AgentvizFeed.create({onUpdate(doc) { model.update(doc); hud.update(doc); },
     onStatus: hud.setStatus});
   feed.start();
   // in the kit's onTap: hud.select({session, follower}, "tap")
   ```
3. Scene: `#include "../vendor/agentviz-kit/scene/agentviz.h"` after
   `strata_kit.h`, declare an `agentviz::Frame`, add
   `AGENTVIZ_FRAME_EXPORT(frame)` and set `KIT_EXPORTS=_agentviz_frame` in
   `scene/kit.conf`. Each frame the page calls `wire.begin(...)`, writes its
   records and `wire.send(module)`.
4. Build: `EMSDK=/path/to/emsdk vendor/agentviz-kit/scene/build-scene.sh scene/kit.conf`.
5. Tests: `npm ci` (a `package.json` pinning `playwright` 1.61.1 as a
   devDependency, then `npx playwright install chromium`) and
   `pip install -r requirements-dev.txt` (Pillow) for the GIF. Build the smoke
   test and screenshots on `harness.cjs` / `screens.cjs`; give each repo its
   own test port. Screenshots come from `?fixture=1` only, never a live feed.

## Wire (format version 1)

One little-endian `Float32Array` per frame, passed as
`agentviz_frame(const float* data, int count)` with `count` in floats. Ids
are FNV-1a 32-bit hashes of the id string cut to 24 bits (exact in a float):
a session's `id`, a follower's `"<session id>/<follower id>"`. States and
actions are indices into `agentfeed/vocabulary.py`'s `STATES` and `ACTIONS`
(`tests/test_kit_vocabulary.py` keeps the three lists in step). Records come
grouped, zones then agents then links; the packer refuses any other order.

**Header** (24 floats)

| # | field |
|---|---|
| 0 | magic `42727` (0xA6E7) |
| 1 | format version (1) |
| 2, 3, 4 | number of zones, agents, links |
| 5 | sessions waiting on the owner |
| 6 | 1 when the feed is the demo fixture |
| 7 | reserved (0) |
| 8–23 | 16 scene floats (the viz decides: room bounds, night override, ...) |

**Zone** (16 floats): an area on the ground (a place, a pod, a region).

| # | field |
|---|---|
| 0 | id (24-bit hash) |
| 1 | kind (the viz decides) |
| 2 | seed (0..1; `seedOf(id)` when not given) |
| 3–6 | x0, z0, x1, z1 |
| 7 | appear (0..1) |
| 8–15 | 8 extras |

**Agent** (36 floats): one per session or follower.

| # | field |
|---|---|
| 0 | id |
| 1 | parent id (a session is its own parent) |
| 2 | kind: 0 session, 1 follower |
| 3 | state index; a follower's `active` / `resting` read as `busy` / `idle` |
| 4 | action index (`none` for a resting follower) |
| 5 | waiting reason: 0 none, 1 question, 2 permission |
| 6 | stalled (0/1) |
| 7 | finished (0/1, followers) |
| 8 | seed |
| 9 | parent seed (the session's; colour followers by it) |
| 10–12 | x, y, z |
| 13 | facing (radians) |
| 14 | appear (0..1) |
| 15 | highlight: 0 none, 1 selected, 2 hovered |
| 16 | pulse (1 at a new tool call, fading; `feed.pulse(id)`) |
| 17 | tool count |
| 18 | active followers (sessions) |
| 19 | reserved (0) |
| 20–35 | 16 extras |

**Link** (12 floats): a line between two things (a trail, a delegation).

| # | field |
|---|---|
| 0 | kind (the viz decides) |
| 1, 2 | from id, to id (0 when not given) |
| 3–8 | x0, y0, z0, x1, y1, z1 |
| 9 | phase |
| 10 | seed |
| 11 | alpha |

`agentviz::Frame::assign` checks the magic, the version and that the counts
match the length; a malformed buffer is refused (`error` says why) and the
last good frame stays. A change to this layout bumps the format version in
`agentviz-wire.js` and `agentviz.h` together.

## Tests here

```bash
python3 -m unittest discover -s tests     # includes the g++ test of agentviz.h and the vendoring check
node --test tests/kit/*.test.js           # feed diffing and wire packing, no dependencies
node tests/kit/pack_fixture.js --write    # after a deliberate wire change: regenerate the fixture
```

`tests/kit/wire_fixture.f32` is packed by `agentviz-wire.js` from
`wire_fixture.json`; the native test decodes it with `agentviz.h`, so the
two halves cannot drift apart.

Generic pieces start here and may move upstream (to Strata's web kit or
darkroom) once they have settled.
