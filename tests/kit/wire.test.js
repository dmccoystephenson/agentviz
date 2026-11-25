// node --test tests/kit: the wire packer's layout.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const Wire = require("../../kit/web/agentviz-wire.js");
const Feed = require("../../kit/web/agentviz-feed.js");
const {pack, OUTPUT} = require("./pack_fixture.js");

const close = (a, b) => Math.abs(a - b) < 1e-6;

test("the committed wire fixture is what the packer writes now", () => {
  assert.deepEqual(pack(), fs.readFileSync(OUTPUT), "run: node tests/kit/pack_fixture.js --write");
});

test("header, strides and counts", () => {
  const data = new Float32Array(pack().buffer.slice(0));
  assert.equal(data[0], Wire.MAGIC);
  assert.equal(data[1], Wire.FORMAT_VERSION);
  assert.deepEqual([data[2], data[3], data[4]], [1, 4, 1]);
  assert.equal(data[5], 1, "one session waiting");
  assert.equal(data[6], 1, "fixture");
  assert.equal(data[8], 1);
  assert.equal(data[23], 16);
  assert.equal(data.length, Wire.HEADER + Wire.ZONE_STRIDE + 4 * Wire.AGENT_STRIDE + Wire.LINK_STRIDE);
});

test("agent records carry the feed's vocabulary", () => {
  const data = new Float32Array(pack().buffer.slice(0));
  const agent = (i) => data.subarray(Wire.HEADER + Wire.ZONE_STRIDE + i * Wire.AGENT_STRIDE);
  const lead = agent(0), resting = agent(2), waiting = agent(3);
  assert.equal(lead[0], Feed.fnv1a("demo-lead") & 0xffffff);
  assert.equal(lead[1], lead[0], "a session is its own parent");
  assert.equal(lead[3], Wire.STATES.indexOf("busy"));
  assert.equal(lead[4], Wire.ACTIONS.indexOf("run"));
  assert.equal(lead[18], 1, "one active follower");
  assert.ok(close(lead[16], 0.5));
  assert.equal(lead[20], 7);
  assert.equal(resting[0], Feed.fnv1a("demo-lead/f-two") & 0xffffff);
  assert.equal(resting[1], lead[0]);
  assert.equal(resting[2], Wire.KIND.follower);
  assert.equal(resting[3], Wire.STATES.indexOf("idle"));
  assert.equal(resting[4], 0, "a resting follower does nothing");
  assert.equal(resting[6], 1, "stalled");
  assert.ok(close(resting[9], 0.25), "parent seed");
  assert.equal(waiting[3], Wire.STATES.indexOf("waiting"));
  assert.equal(waiting[5], Wire.WAITING_REASONS.indexOf("permission"));
  assert.ok(close(waiting[8], Feed.seedOf("démo-ü-✓-\u{1f98a}")), "missing seed falls back to seedOf");
  assert.equal(waiting[35], 99);
});

test("records must be written zones, then agents, then links", () => {
  const wire = Wire.create().begin({});
  wire.agent({session: {id: "a", state: "idle"}});
  assert.throws(() => wire.zone({id: "z", x0: 0, z0: 0, x1: 1, z1: 1}), /zones, then agents, then links/);
});

test("send copies into the heap and calls _agentviz_frame", () => {
  const heap = new Float32Array(4096);
  const calls = [];
  const mod = {HEAPF32: heap, _malloc: () => 64, _free: () => {}, _agentviz_frame: (ptr, n) => calls.push([ptr, n])};
  const wire = Wire.create().begin({scene: [5]});
  wire.zone({id: "z", x0: 0, z0: 0, x1: 1, z1: 1});
  wire.send(mod);
  assert.deepEqual(calls, [[64, Wire.HEADER + Wire.ZONE_STRIDE]]);
  assert.equal(heap[16], Wire.MAGIC);
  assert.equal(heap[16 + 8], 5);
});
