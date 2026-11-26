# The agentviz kit

Every visualization in the family needs the same things around its scene:
read the feed, show who needs you, show what was tapped, label the world,
pass the frame to the engine, build the wasm, and test the page. `kit/` is
that shared half, vendored into each viz repo next to `agentfeed`. A viz
keeps only its metaphor: the layout, the motion and the drawing.

| File | What it is for |
|---|---|
| `kit/web/agentviz-feed.js` | `AgentvizFeed`: polls `/api/agents` every 2 s (`?fixture=1` / `?demo=1` pick the demo feed), keys sessions and followers by id, reports added / removed / changed and new tool calls, backs off on failure with an explicit `"unreachable"` status. Also `fnv1a`, `seedOf` (identical to Python's `seed_of`), `ease`, `lerp`, `smoothstep`. |
| `kit/web/agentviz-hud.js` + `agentviz-hud.css` | `AgentvizHud`: top bar (title, "needs you" chip that cycles waiting sessions and says why each waits, counts, demo-feed badge, the page's buttons, legend toggle), unreachable banner, empty-state hint, and the selection panel (a card on desktop, a bottom sheet with a swipe-down grab on phones). Opt-in one-row phone bar; the panel's resting rect, the uncovered area and keep-clear label placement (see "Phones"). |
| `kit/web/agentviz-screen.js` | `AgentvizScreen`: action icons, state dots, a keyed world-label pool for `StrataKit.placeLabels`, nearest-point tap picking, and the pure maths behind "Phones": `keepClear`, `freeArea`, `projectWith`, `aim`, `reveal`, `fitPoints`, `sameView`. |
| `kit/web/agentviz-wire.js` | `AgentvizWire`: packs one frame into a `Float32Array` (layout below) and hands it to the engine. |
| `kit/scene/agentviz.h` | Decodes that buffer in the scene; the vocabulary enums, `seed_of`, easing. Header-only C++17, no Strata dependency. |
| `kit/scene/build-scene.sh` | Downloads the pinned Strata 0.10.0 wasm tarball, checks its SHA-256, activates emsdk from `$EMSDK`, runs the tarball's `kit/build-kit.sh` with the repo's `scene/kit.conf`. |
| `kit/scene/emsdk-env.sh` | Activates emsdk 6.0.11 from `$EMSDK` (build-scene.sh sources it); picks a Python 3.10+ for emsdk and keeps `EMSDK_PYTHON` set across `emsdk_env.sh`. |
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
   theme it by overriding the `--av-*` custom properties. `--av-badge` (the
   demo-feed badge) defaults to `--av-note` and can be set on its own; the
   "need you" chip's throb follows `--av-wait`.

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

## Phones

Every viz needs the same three things on a phone: a top bar that keeps to
one row, world labels that stay out from under the bar and the bottom sheet,
and a tap that slides what was tapped out from under the sheet. All of it is
opt-in; a page that uses none of it looks and behaves as before.

**Bar classes.** Each count chip is `av-chip av-count av-count-<key>` (`busy`,
`followers`, `idle`, `offline`; `AgentvizHud.countClass(key)`), the page's
buttons and the legend toggle are `av-btn` (the toggle also `av-legend-btn`),
and the demo badge reads `demo` + `<span class="av-badge-more"> feed</span>`.
Style or hide a chip by class, never by `title` or `:has()`. `hud.bar` is
the bar element.

**One row.** `AgentvizHud.create({oneRow: true, ...})` adds `av-one-row` to
the bar and puts the counts and the badge in `.av-bar-scroll`. On a desktop
that wrapper is `display: contents`, so nothing moves. At 640px and below the
bar does not wrap (`white-space: nowrap`), the title and " feed" give way, the
"need you" chip and the buttons stay put, and the counts scroll sideways
between them. A page that wants fewer counts hides them by class:
`.av-one-row .av-count-offline { display: none; }`. A page that inserts its
own button into the bar (`bar.insertBefore(b, bar.lastElementChild)`) still
lands among the fixed buttons.

**Keep-clear labels.** Instead of `StrataKit.placeLabels(items)`:

```js
hud.placeLabels(items, {canvas});   // keepClear, then StrataKit.placeLabels
```

`hud.clearArea(canvas)` measures `{W, H, top, avoid}` in canvas pixels: the
bar's foot (+4px) and the open panel's resting rect and the open legend
(each padded 4px). `AgentvizScreen.keepClear(items, area)` then, before
placement: clamps each label inside the screen's sides once it has been
measured (a rank > 0 label whose anchor is off the side is left to fall off;
a rank <= 0 one is pulled in); hides a label under the panel or legend
(rank <= 0 stays); hides a label that reaches into the top band, or for
rank <= 0 pins it just under the band, stacked downwards clear of other
pinned labels; and caps `tries` near the band so no label steps up into it.
It replaces `q` and never mutates it. Options (`{keep: {...}}` on
`hud.placeLabels`): `margin` (4), `gap` (2, as placeLabels), `labelH` (18,
before a label is measured). `{place: {...}}` passes options on to
`StrataKit.placeLabels`.

Strata kit 1.4 (Strata PRs #122/#123, not merged when this was written) adds
`topInset` / `avoid` to `placeLabels` itself. Once a viz vendors it,
`hud.placeLabels(items, {canvas, strataAvoid: true})` hands the same area
over as `AgentvizScreen.strataAvoid(area)` = `{topInset, avoid: [{left, top,
right, bottom}]}` and keepClear only clamps the sides. That shape is the one
the PRs propose: check it against the merged API before switching.

**Tap-to-reveal.** `hud.panelRect()` is the panel's resting rect in viewport
pixels (from `offset*`, so it is right while the sheet is still sliding in),
with `sheet: true` when it spans the width, or null while closed.
`hud.freeRect(canvas, {panel: true})` is the area nothing covers: below the
bar and, with the panel open, above the sheet or beside the card (whichever
leaves more). The camera maths is Strata's orbit camera (`sk_frame`, 50°
vertical field of view) as plain functions, so a view can be fitted before it
is drawn:

```js
const {reveal, fitPoints, sameView} = AgentvizScreen;
function onSelect(target, how) {          // the HUD has drawn the panel already
  const p = worldPointOf(target);         // [x, y, z]
  const to = reveal(kit.cam, p, hud.freeRect(canvas), how === "tap" ? {} : {set: {dist: 16}, force: true});
  if (to) flyTo(to);                      // null: already in view, the camera stays
}
let lastFit = null;
function fit() { lastFit = fitPoints(startCam, cornersOfTheWorld, hud.freeRect(canvas, {panel: false})); flyTo(lastFit); }
addEventListener("resize", () => requestAnimationFrame(() => { if (sameView(kit.cam, lastFit)) fit(); }));
```

`reveal(cam, p, free, o)`: null when `p` is inside `free` by `o.pad` (40, or
`{top, right, bottom, left}`) unless `o.force`; otherwise a copy of `cam`
(with `o.set` applied) aimed so `p` sits at the free area's middle, `o.dy`
(20) px low. `aim(cam, x, y, z, sx, sy, W, H)` moves only the target.
`fitPoints(cam, points, free, {mid, minDist, maxDist, inset, iterations})`
keeps `cam`'s yaw and pitch. `projectWith(cam, x, y, z, W, H)` returns
`{x, y, w}` like `kit.project`; keep it in step with `strata_kit.h` (a page
test can compare the two). A page that follows a moving thing (atc) can call
`reveal(..., {force: true})` each frame and ease towards the result.

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
node --test tests/kit/*.test.js           # feed diffing, wire packing, phone maths, no dependencies
node tests/kit/pack_fixture.js --write    # after a deliberate wire change: regenerate the fixture
```

`tests/kit/wire_fixture.f32` is packed by `agentviz-wire.js` from
`wire_fixture.json`; the native test decodes it with `agentviz.h`, so the
two halves cannot drift apart.

Generic pieces start here and may move upstream (to Strata's web kit or
darkroom) once they have settled.

## Licence notices

`kit/NOTICES-emscripten.md` holds the licence texts for what emsdk compiles
into every engine (the Emscripten runtime, musl libc, libc++ and libc++abi). It
is vendored with the kit as `vendor/agentviz-kit/NOTICES-emscripten.md`; each
viz's THIRD_PARTY_NOTICES.md points to it, next to Strata's own notices.

## Guard tests

`kit/tests/guards.py` holds the tests every viz runs: no `innerHTML` in the
page's own scripts and HTML, no empty `catch` blocks, no machine-local paths in
tracked text (CLAUDE.md's "while private" line is exempt). Load it by path in a
unit test and subclass `GuardTests` with `REPO` set; see the file's docstring.

## What check_vendor.py proves

It proves each vendored copy matches the digest in its own PIN, so an edit to
a vendored file (or to a `web/agentviz-*` copy) without re-vendoring fails.
It does not prove the PIN's commit is the one named on its first line: re-run
`tools/vendor-kit.sh` from that agentviz commit to be sure.

## Portability

`build-scene.sh` checks the Strata tarball with `sha256sum`, or `shasum -a 256`
where that is missing (macOS). `emsdk-env.sh` stops with a message when no
Python 3.10+ is found. The test harness runs `python3` (or `python` on
Windows); set `AGENTVIZ_PYTHON` to override.
