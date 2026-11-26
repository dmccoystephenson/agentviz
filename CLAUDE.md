# CLAUDE.md

Index of the agentviz family + the shared `agentfeed` package (stdlib-only
Python 3.8+). Tests: `python3 -m unittest discover -s tests`.

- Layout (ports and adapters): `agentfeed/core.py` is pure (records in, feed
  document out); `ports/` holds the two questions it asks (SessionSource,
  ActivitySource), one file each; `adapters/` answers them (Claude's session
  registry, transcripts, the demo feed) and serves HTTP, one file each;
  `service.py` wires them. `feed.py` and `serve.py` are compatibility shims.
  `tests/test_architecture.py` enforces the layering.
- `kit/` is the shared page/scene kit every viz vendors (docs/KIT.md): web/
  (feed client, HUD, screen helpers, wire packer), scene/ (agentviz.h,
  build-scene.sh), tests/ (Playwright harness, make_gif.py), check_vendor.py.
  Changing the wire layout bumps its format version in agentviz-wire.js and
  agentviz.h together and regenerates tests/kit/wire_fixture.f32
  (`node tests/kit/pack_fixture.js --write`). Kit tests:
  `node --test tests/kit/*.test.js`. Vendor with `tools/vendor-kit.sh <repo>`.
  Feed strings reach the DOM as text only.
- Feed schema: docs/FEED.md. Changing a field is a schema change: bump
  `SCHEMA_VERSION` and say so in every visualization repo.
- Privacy: only names, tool names, branches, basenames and short labels leave
  the feed; every label goes through `labels.short_label`, which redacts
  token-shaped strings. Bash and subagent descriptions are model free text.
  Never contents, commands, prompts or paths. Fixtures are synthetic.
- Server binds 127.0.0.1 only.
- README table is the index: keep it in step with the repos.
