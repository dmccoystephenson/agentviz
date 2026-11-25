# CLAUDE.md

Index of the agentviz family + the shared `agentfeed` package (stdlib-only
Python 3.8+). Tests: `python3 -m unittest discover -s tests`.

- Layout (ports and adapters): `agentfeed/core.py` is pure (records in, feed
  document out); `ports/` holds the two questions it asks (SessionSource,
  ActivitySource), one file each; `adapters/` answers them (Claude's session
  registry, transcripts, the demo feed) and serves HTTP, one file each;
  `service.py` wires them. `feed.py` and `serve.py` are compatibility shims.
  `tests/test_architecture.py` enforces the layering.
- Feed schema: docs/FEED.md. Changing a field is a schema change: bump
  `SCHEMA_VERSION` and say so in every visualization repo.
- Privacy: only tool names and short labels leave `feed.py` (basename, a Bash
  command's own description, web host, subagent description). Never contents,
  commands, prompts or paths. Fixtures are synthetic.
- Server binds 127.0.0.1 only.
- All repos in the family are PRIVATE on dmccoystephenson. Hosted Actions are
  refused for private personal repos (billing), so run localci on PRs:
  `cd /root/localci && python3 -m localci pr dmccoystephenson/<repo> <N> --post --status`.
- README table is the index: keep it in step with the repos.
