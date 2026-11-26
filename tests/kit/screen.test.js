// node --test tests/kit: the phone helpers' pure maths (keep-clear labels,
// free area, camera aim / reveal / fit) and the HUD's chip classes.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const Screen = require("../../kit/web/agentviz-screen.js");
const Hud = require("../../kit/web/agentviz-hud.js");

const label = (x, y, rank, w = 60, h = 18, extra = {}) =>
  Object.assign({el: {_skW: w, _skH: h}, q: {x, y, w: 10}, rank}, extra);
const AREA = {W: 400, H: 800, top: 50, avoid: []};

test("count chips carry one class per count, so pages never match on title", () => {
  assert.deepEqual(Hud.COUNTS.map((c) => c.key), ["busy", "followers", "idle", "offline"]);
  for (const {key} of Hud.COUNTS) {
    const cls = Hud.countClass(key).split(" ");
    assert.ok(cls.includes("av-chip") && cls.includes("av-count") && cls.includes("av-count-" + key), key);
  }
});

test("keepClear clamps a label inside the screen's sides", () => {
  const items = [label(10, 300, 2), label(395, 300, 1)];
  Screen.keepClear(items, AREA);
  assert.equal(items[0].q.x, 34);    // 60 / 2 + 4
  assert.equal(items[1].q.x, 366);
  assert.equal(items[0].q.w, 10, "depth is kept");
});

test("keepClear leaves an off-screen quiet label to fall off, but pulls in a waiting one", () => {
  const items = [label(-80, 300, 2), label(-80, 300, 0)];
  Screen.keepClear(items, AREA);
  assert.equal(items[0].q.x, -80);
  assert.equal(items[1].q.x, 34);
});

test("keepClear does not clamp before placeLabels has measured the label", () => {
  const it = {el: {}, q: {x: 2, y: 300}, rank: 2};
  Screen.keepClear([it], AREA);
  assert.equal(it.q.x, 2);
});

test("a label reaching into the top band hides; a must-show one pins under it", () => {
  const quiet = label(100, 60, 2), waiting = label(300, 30, 0);
  Screen.keepClear([quiet, waiting], AREA);
  assert.equal(quiet.q, null);
  assert.deepEqual([waiting.q.y, waiting.tries], [68, 1]);    // top 50 + h 18
});

test("pinned labels stack downwards instead of overlapping each other", () => {
  const a = label(100, 10, 0), b = label(120, 20, 0), c = label(300, 20, 0);
  Screen.keepClear([a, b, c], AREA);
  assert.equal(a.q.y, 68);
  assert.equal(b.q.y, 88);    // overlaps a: one row down (h 18 + gap 2)
  assert.equal(c.q.y, 68);    // clear of both sideways: stays on the first row
});

test("near the band a label may not step up into it", () => {
  const near = label(100, 90, 0), mid = label(250, 90, 1), far = label(100, 500, 0);
  Screen.keepClear([near, mid, far], AREA);
  assert.equal(near.tries, 2);     // 1 + floor((90 - 18 - 50) / 20)
  assert.equal(mid.tries, 2);
  assert.equal(far.tries, 6, "far below: placeLabels' default");
  const given = label(100, 500, 2, 60, 18, {tries: 3});
  Screen.keepClear([given], AREA);
  assert.equal(given.tries, 3, "a page's own tries is kept when there is room");
});

test("a label under the panel hides unless it must show", () => {
  const area = Object.assign({}, AREA, {avoid: [{x0: 0, y0: 500, x1: 400, y1: 800}]});
  const quiet = label(200, 600, 2), waiting = label(200, 600, 0), above = label(200, 450, 2);
  Screen.keepClear([quiet, waiting, above], area);
  assert.equal(quiet.q, null);
  assert.equal(waiting.q.y, 600);
  assert.equal(above.q.y, 450);
});

test("keepClear never mutates the item's q object", () => {
  const q = {x: 2, y: 300, w: 1}, it = {el: {_skW: 60, _skH: 18}, q, rank: 2};
  Screen.keepClear([it], AREA);
  assert.equal(q.x, 2);
  assert.notEqual(it.q, q);
});

test("strataAvoid hands the same area over in placeLabels' proposed 1.4 shape", () => {
  assert.deepEqual(Screen.strataAvoid({W: 1, H: 1, top: 52, avoid: [{x0: 1, y0: 2, x1: 3, y1: 4}]}),
    {topInset: 52, avoid: [{left: 1, top: 2, right: 3, bottom: 4}]});
});

test("freeArea: under the bar, above a bottom sheet, beside a tall card", () => {
  assert.deepEqual(Screen.freeArea({W: 400, H: 800, top: 50}), {x0: 8, y0: 58, x1: 392, y1: 792, W: 400, H: 800});
  const sheet = Screen.freeArea({W: 400, H: 800, top: 50, panel: {x0: 0, y0: 420, x1: 400, y1: 800}});
  assert.deepEqual([sheet.x0, sheet.y1], [8, 412]);
  const card = Screen.freeArea({W: 1400, H: 800, top: 50, panel: {x0: 12, y0: 300, x1: 352, y1: 788}});
  assert.deepEqual([card.x0, card.y1], [360, 792]);
  const lowCard = Screen.freeArea({W: 1400, H: 800, top: 50, panel: {x0: 12, y0: 640, x1: 352, y1: 788}});
  assert.deepEqual([lowCard.x0, lowCard.y1], [8, 632]);
});

const CAM = {yaw: 0.8, pitch: 0.7, dist: 30, tx: 0, ty: 0, tz: 0};

test("projectWith puts the target in the middle and refuses points behind the camera", () => {
  const q = Screen.projectWith(CAM, 0, 0, 0, 400, 800);
  assert.ok(Math.abs(q.x - 200) < 1e-6 && Math.abs(q.y - 400) < 1e-6);
  assert.ok(Math.abs(q.w - 30) < 1e-6);
  const eye = [Math.cos(0.8) * Math.cos(0.7) * 30, Math.sin(0.7) * 30, Math.sin(0.8) * Math.cos(0.7) * 30];
  assert.equal(Screen.projectWith(CAM, eye[0] * 2, eye[1] * 2, eye[2] * 2, 400, 800), null);
  const up = Screen.projectWith(CAM, 0, 5, 0, 400, 800);
  assert.ok(up.y < 400, "higher in the world is higher on screen");
});

test("aim lands a world point on the asked-for screen point", () => {
  const c = Screen.aim(Object.assign({}, CAM), 6, 1, -4, 120, 200, 400, 800);
  const q = Screen.projectWith(c, 6, 1, -4, 400, 800);
  assert.ok(Math.abs(q.x - 120) < 0.5 && Math.abs(q.y - 200) < 0.5, JSON.stringify(q));
  assert.deepEqual([c.yaw, c.pitch, c.dist], [CAM.yaw, CAM.pitch, CAM.dist], "only the target moves");
});

test("reveal leaves a visible point alone and slides a covered one above the sheet", () => {
  const free = Screen.freeArea({W: 400, H: 800, top: 50, panel: {x0: 0, y0: 420, x1: 400, y1: 800}});
  const high = Screen.aim(Object.assign({}, CAM), 0, 0, 0, 200, 230, 400, 800);   // in the clear band
  assert.equal(Screen.reveal(high, [0, 0, 0], free), null, "already clear: no move");
  const low = Screen.aim(Object.assign({}, CAM), 0, 0, 0, 200, 650, 400, 800);   // under the sheet
  const c = Screen.reveal(low, {x: 0, y: 0, z: 0}, free);
  const q = Screen.projectWith(c, 0, 0, 0, 400, 800);
  assert.ok(q.y > free.y0 && q.y < free.y1, JSON.stringify(q));
  assert.equal(low.tx, Screen.aim(Object.assign({}, CAM), 0, 0, 0, 200, 650, 400, 800).tx, "cam is not changed");
  const zoom = Screen.reveal(CAM, [0, 0, 0], free, {set: {dist: 12}, force: true});
  assert.equal(zoom.dist, 12);
});

test("fitPoints frames every point inside the free area", () => {
  const pts = [[-20, 0, -10], [20, 0, -10], [-20, 0, 10], [20, 0, 10], [0, 3, -10]];
  for (const [W, H] of [[400, 800], [1400, 800]]) {
    const free = Screen.freeArea({W, H, top: 50});
    const c = Screen.fitPoints({yaw: Math.PI / 2, pitch: 0.9, dist: 60, tx: 0, ty: 0, tz: 0}, pts, free, {maxDist: 400});
    for (const p of pts) {
      const q = Screen.projectWith(c, p[0], p[1], p[2], W, H);
      assert.ok(q.x >= free.x0 - 2 && q.x <= free.x1 + 2 && q.y >= free.y0 - 2 && q.y <= free.y1 + 2,
        W + "x" + H + " " + JSON.stringify(q));
    }
  }
});

test("sameView tells an untouched view from a moved one", () => {
  assert.ok(Screen.sameView(CAM, Object.assign({}, CAM, {tx: 1e-4})));
  assert.ok(!Screen.sameView(CAM, Object.assign({}, CAM, {dist: 31})));
  assert.ok(!Screen.sameView(null, CAM));
});
