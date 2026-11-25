// node --test tests/kit: the feed client's diffing, hashing and backoff.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const Feed = require("../../kit/web/agentviz-feed.js");

const session = (id, extra = {}) => Object.assign({id, name: id, state: "busy", action: "edit", statusAgeSec: 1,
  followers: []}, extra);
const doc = (...sessions) => ({version: 1, serverTime: 1, sessions});

test("seedOf matches agentfeed's Python seed_of, code point by code point", () => {
  // Values from: python3 -c "from agentfeed.labels import seed_of; print(seed_of(s))"
  const python = {"demo-lead": 0.6771, "": 0.6261, "a": 0.222, "démo-ü-✓-\u{1f98a}": 0.9512, "site-one": 0.5523};
  for (const [text, seed] of Object.entries(python)) assert.equal(Feed.seedOf(text), seed, text);
});

test("diff reports added, removed and changed sessions, ignoring ages", () => {
  const before = doc(session("a"), session("b"));
  const after = doc(session("a", {statusAgeSec: 99}), session("c"));
  const d = Feed.diff(before, after);
  assert.deepEqual(d.sessions, {added: ["c"], removed: ["b"], changed: []});
  const acted = Feed.diff(after, doc(session("a", {action: "run"}), session("c")));
  assert.deepEqual(acted.sessions.changed, ["a"]);
});

test("followers are keyed by lead/follower and diffed on their own", () => {
  const f = (id, extra = {}) => Object.assign({id, state: "active", action: "edit", ageSec: 1, toolCount: 1}, extra);
  const before = doc(session("a", {followers: [f("x"), f("y")]}));
  const after = doc(session("a", {followers: [f("x", {ageSec: 50, toolCount: 2}), f("z")]}));
  const d = Feed.diff(before, after);
  assert.deepEqual(d.followers, {added: ["a/z"], removed: ["a/y"], changed: ["a/x"]});
  assert.deepEqual(d.sessions.changed, [], "a follower change is not a session change");
  assert.deepEqual(d.toolCalls, ["a/x"]);
});

test("a moved lastToolAt is a new tool call", () => {
  const d = Feed.diff(doc(session("a", {lastToolAt: 10})), doc(session("a", {lastToolAt: 12})));
  assert.deepEqual(d.toolCalls, ["a"]);
  assert.deepEqual(Feed.diff(null, doc(session("a", {lastToolAt: 12}))).toolCalls, [], "first sight is not a call");
});

test("failed polls turn the status unreachable and back off; success recovers", async () => {
  let fail = true;
  const statuses = [];
  const feed = Feed.create({fixture: false, unreachableAfter: 2, intervalMs: 2000, maxBackoffMs: 30000,
    fetch: async () => (fail ? {ok: false, status: 502} : {ok: true, json: async () => doc(session("a"))}),
    onStatus: (s, info) => statuses.push([s, info.error])});
  assert.equal(await feed.pollOnce(), null);
  assert.equal(feed.status, "connecting");
  assert.equal(feed.nextDelay(), 2000);
  await feed.pollOnce();
  assert.equal(feed.status, "unreachable");
  assert.equal(feed.nextDelay(), 4000);
  for (let i = 0; i < 6; i++) await feed.pollOnce();
  assert.equal(feed.nextDelay(), 30000, "backoff is capped");
  fail = false;
  const changes = await feed.pollOnce();
  assert.deepEqual(changes.sessions.added, ["a"]);
  assert.equal(feed.status, "live");
  assert.equal(feed.nextDelay(), 2000);
  assert.deepEqual(statuses, [["unreachable", "HTTP 502"], ["live", null]]);
});

test("the fixture flag picks the demo feed URL", async () => {
  const urls = [];
  const feed = Feed.create({fixture: true, fetch: async (u) => { urls.push(u); return {ok: true, json: async () => doc()}; }});
  await feed.pollOnce();
  assert.deepEqual(urls, ["/api/agents?fixture=1"]);
});

test("pulse is 1 at a new tool call and fades", () => {
  let now = 100;
  const feed = Feed.create({fixture: false, now: () => now});
  feed.push(doc(session("a", {lastToolAt: 1})));
  feed.push(doc(session("a", {lastToolAt: 2})));
  assert.equal(feed.pulse("a"), 1);
  now += 0.6;
  assert.ok(Math.abs(feed.pulse("a") - 0.5) < 1e-9);
  now += 5;
  assert.equal(feed.pulse("a"), 0);
  assert.equal(feed.pulse("nobody"), 0);
});

test("easing helpers", () => {
  assert.equal(Feed.ease(0, 10, 0, 3), 0);
  assert.ok(Feed.ease(0, 10, 10, 3) > 9.99);
  assert.equal(Feed.smoothstep(-1), 0);
  assert.equal(Feed.smoothstep(0.5), 0.5);
  assert.equal(Feed.lerp(2, 4, 0.5), 3);
});
