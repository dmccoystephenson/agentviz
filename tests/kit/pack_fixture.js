// Packs wire_fixture.json with kit/web/agentviz-wire.js. With --write it
// (re)writes wire_fixture.f32, which tests/kit/agentviz_test.cpp decodes;
// wire.test.js checks the committed file still matches what this packs.
"use strict";
const fs = require("fs");
const path = require("path");
const Wire = require("../../kit/web/agentviz-wire.js");

const INPUT = path.join(__dirname, "wire_fixture.json");
const OUTPUT = path.join(__dirname, "wire_fixture.f32");

function pack() {
  const spec = JSON.parse(fs.readFileSync(INPUT, "utf8"));
  const sessions = spec.doc.sessions;
  const wire = Wire.create().begin({doc: spec.doc, scene: spec.scene});
  for (const zone of spec.zones) wire.zone(zone);
  for (const a of spec.agents) {
    const session = sessions[a.session];
    const follower = a.follower != null ? session.followers[a.follower] : null;
    wire.agent(Object.assign({}, a, {session, follower}));
  }
  for (const link of spec.links) wire.link(link);
  return Buffer.from(wire.finish().slice().buffer);
}

if (require.main === module && process.argv.includes("--write")) {
  fs.writeFileSync(OUTPUT, pack());
  console.log("wrote", OUTPUT);
}

module.exports = {pack, OUTPUT};
