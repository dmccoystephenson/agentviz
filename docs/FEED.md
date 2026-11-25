# The agent feed (schema version 1)

`GET /api/agents` (served by `python3 -m agentfeed serve`) returns one JSON
document describing every Claude Code session on this machine and its
subagents. Every visualization in the family reads only this.

```jsonc
{
  "version": 1,
  "serverTime": 1764000000.0,     // epoch seconds
  "fixture": false,               // true when this is the demo feed
  "counts": {"offline": 0, "dim": 0, "idle": 1, "busy": 4, "waiting": 0,
             "followers": 16, "activeFollowers": 15},
  "places": [                     // one per working-directory basename
    {"id": "dansplugins-dot-com", "label": "dansplugins-dot-com", "seed": 0.41,
     "sessions": 1, "busy": 1, "waiting": 0, "followers": 6}
  ],
  "sessions": [                   // stable order: start time, then id
    {
      "id": "…", "name": "BurnishTwo",
      "state": "busy",            // offline | dim | idle | busy | waiting (= needs the owner)
      "status": "busy",           // raw registry status
      "statusAgeSec": 12.0, "uptimeSec": 960.0, "idleSec": 4.0,
      "stalled": false,           // busy but nothing written for > 300 s
      "place": "dansplugins-dot-com", "placeLabel": "dansplugins-dot-com",
      "branch": "main",           // last gitBranch in the transcript, or null
      "kind": "interactive",
      "fixture": false,
      "activity": {"tool": "Bash", "action": "run", "label": "Check lane PRs", "ageSec": 4.0},
      "action": "delegate",       // what the agent is doing NOW (see below)
      "recent": [{"tool": "Read", "action": "read", "ageSec": 30.0}],   // last 8 tool calls
      "followers": [              // subagents written to in the last 15 min, newest first, max 8
        {"id": "a1b2", "label": "DPC a11y polish lane",
         "state": "active",       // active (wrote < 120 s ago) | resting
         "tool": "Edit", "toolLabel": "nav.css", "action": "edit",
         "ageSec": 3.0, "quietSec": 3.0, "toolCount": 42, "seed": 0.77}
      ],
      "seed": 0.12,               // stable 0..1 per id: use it for colours, jitter, props
      "startedAt": 1763999000000
    }
  ]
}
```

## Actions

| action | tools | suggested reading |
|---|---|---|
| `edit` | Edit, Write, MultiEdit, NotebookEdit | making / building |
| `run` | Bash, Monitor, KillShell | operating machinery |
| `read` | Read, Grep, Glob | reading, inspecting |
| `web` | WebSearch, WebFetch | looking outward |
| `delegate` | Agent, Task, Workflow; or busy with active followers but no recent tool | directing others |
| `think` | busy, no recent tool, no active followers | pausing, pondering |
| `other` | anything else (MCP, Skill, TodoWrite…) | generic busy |
| `none` | not busy | — |

## States

`waiting` means the session is blocked on the owner (a permission prompt or a
question). Every visualization must make it obvious; it is the most useful
signal on the page. `offline` sessions (process gone, updated in the last 6 h)
are shown faded or absent. `dim` is a shell or unknown status.

## Privacy

Labels are a file's basename, a Bash command's own `description`, a web
host, or a subagent's description. Never file contents, commands, prompts or
full paths; `cwd` itself is not in the document. The server binds to
127.0.0.1. Fixtures are synthetic: never commit real transcript data or
screenshots of a live feed.

## Fixture

`agentfeed/fixture.json` uses relative times (`startedAgoSec`, `updatedAgoSec`), rebased to now on every build, so the demo feed never drifts. It covers every state and action, plus one stalled session.

## Polling

Poll every 2 s. Animate between snapshots; never rebuild the scene from
scratch on each poll. Key everything by `id`.
