# agentviz

Ten ways to watch Claude Code sessions and their subagents at work, drawn
with [Strata](https://github.com/Preponderous-Software/strata), plus the
shared feed they all read.

Every visualization runs the same way:

```bash
cd agentviz-<name>
python3 -m vendor.agentfeed serve --web web --port <port>            # live sessions
python3 -m vendor.agentfeed serve --web web --port <port> --fixture  # demo feed
```

then open `http://127.0.0.1:<port>/` (127.0.0.1 only; the feed describes real work).

## The visualizations

| # | Repo | Port | Metaphor | Sessions are… | Subagents are… |
|---|---|---|---|---|---|
| 1 | [agentviz-office](https://github.com/dmccoystephenson/agentviz-office) | 8841 | Open-plan office | lead desks in team pods (one pod per repo) | satellite desks in the pod; tool = desk activity; waiting = note on the owner's door |
| 2 | [agentviz-kitchen](https://github.com/dmccoystephenson/agentviz-kitchen) | 8842 | Restaurant kitchen | head chefs at the pass | line cooks at stations; tickets on the rail |
| 3 | [agentviz-railway](https://github.com/dmccoystephenson/agentviz-railway) | 8843 | Railway yard | trunk lines (branches) | locomotives on sidings; signals for state |
| 4 | [agentviz-atc](https://github.com/dmccoystephenson/agentviz-atc) | 8844 | Air traffic control | airports / gates | flights out and back; holding stack = waiting on you |
| 5 | [agentviz-mine](https://github.com/dmccoystephenson/agentviz-mine) | 8845 | Mine cross-section | shafts | branching tunnels; depth = time/tool calls |
| 6 | [agentviz-hive](https://github.com/dmccoystephenson/agentviz-hive) | 8846 | Beehive | queens' cells by repo | foragers; trails where repos overlap |
| 7 | [agentviz-constellation](https://github.com/dmccoystephenson/agentviz-constellation) | 8847 | Star system | stars | orbiting planets; speed = activity |
| 8 | [agentviz-shipyard](https://github.com/dmccoystephenson/agentviz-shipyard) | 8848 | Shipyard | hulls in dry dock (repos) | welders on scaffolding |
| 9 | [agentviz-orchestra](https://github.com/dmccoystephenson/agentviz-orchestra) | 8849 | Orchestra | conductors | instrument sections; tool calls play notes (opt-in audio) |
| 10 | [agentviz-wartable](https://github.com/dmccoystephenson/agentviz-wartable) | 8850 | Campaign war table | banners on regions | scouts riding out |

The `/3d` session village in claude-code-dashboard is the ancestor of all of
these; agentfeed is its data half without the layout.

## agentfeed

`agentfeed/` is a stdlib-only Python package: `build_feed()` turns
`~/.claude/sessions` + transcripts into the document in
[docs/FEED.md](docs/FEED.md); `python3 -m agentfeed serve` serves it next to a
visualization's `web/` dir. Each visualization vendors a copy with
`tools/vendor-feed.sh <repo>` (it writes `vendor/agentfeed/PIN`).

```bash
python3 -m agentfeed dump --fixture     # the demo feed
python3 -m agentfeed dump               # this machine, now
python3 -m unittest discover -s tests
```

Building a scene: [docs/BUILDING.md](docs/BUILDING.md).
