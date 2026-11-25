# The agent feed (schema version 1)

`GET /api/agents` (served by `python3 -m agentfeed serve`) returns one JSON
document describing every Claude Code session on this machine and its
subagents. Every visualization in the family reads only this.

```jsonc
{
  "version": 1,
  "serverTime": 1764000000.0,     // epoch seconds
  "fixture": false,               // true when this is the demo feed
  "counts": {"offline": 0, "dim": 0, "idle": 1, "busy": 4, "waiting": 1,
             "followers": 7, "activeFollowers": 6},
  "places": [                     // one per working-directory basename
    {"id": "plugin-site", "label": "plugin-site", "seed": 0.41,
     "sessions": 1, "busy": 1, "waiting": 0, "followers": 7,
     "toolCount": 338}            // tool calls seen across its sessions and subagents (0.3)
  ],
  "sessions": [                   // stable order: start time, then id
    {
      "id": "demo-lead-b", "name": "Otto",
      "state": "busy",            // offline | dim | idle | busy | waiting (= needs the owner)
      "status": "busy",           // raw registry status
      "statusAgeSec": 12.0, "uptimeSec": 3000.0, "idleSec": 4.0,
      "stalled": false,           // busy but nothing written for > 300 s
      "place": "plugin-site", "placeLabel": "plugin-site",
      "branch": "main",           // last gitBranch in the transcript, or null
      "kind": "interactive",      // as the registry reports it, e.g. "interactive" or "remote"
      "fixture": true,
      "activity": {"tool": "Bash", "action": "run", "label": "Check lane PRs", "ageSec": 4.0},
      "action": "run",            // what the agent is doing NOW (see below)
      "recent": [{"tool": "Read", "action": "read", "ageSec": 30.0}],   // last 8 tool calls
      "toolCount": 88,            // tool calls seen in the transcript tail (0.3)
      "lastToolAt": 1763999996.0, // epoch seconds of the newest; changes on each new call (0.3)
      "waitingSec": null,         // seconds spent waiting, when state is waiting (0.3)
      "waitingReason": null,      // "question" | "permission" when waiting (0.3)
      "followers": [              // subagents written to in the last 15 min, newest first, max 8
        {"id": "demo-b1", "label": "polish/a11y",
         "state": "active",       // active (wrote < 120 s ago) | resting
         "tool": "Edit", "toolLabel": "index.html", "action": "edit",
         "ageSec": 3.0, "quietSec": 3.0, "toolCount": 42, "seed": 0.77,
         "finished": false,       // the subagent's own "finished" flag; null when unknown (0.3)
         "stalled": false,        // not finished and quiet for > 300 s (0.3)
         "branch": "main",        // its own git branch (worktree lanes differ) (0.3)
         "startedAt": 1763997000.0}  // epoch seconds of its first transcript line (0.3)
      ],
      "seed": 0.12,               // stable 0..1 per id: use it for colours, jitter, props
      "startedAt": 1763999000000  // epoch MILLISECONDS, as the session registry stores it
    }
  ]
}
```

Fields marked (0.3) were added in agentfeed 0.3. They are additive, so the
schema stays at version 1; older pages ignore them.

## Places

`place` is the working directory's basename. The home directory becomes
`"~"` with the label `"home"`. A directory named `Owner__Repo` (a common
naming for cache clones) gets the label `Repo`.

## Actions

| action | tools | suggested reading |
|---|---|---|
| `edit` | Edit, Write, MultiEdit, NotebookEdit | making / building |
| `run` | Bash, BashOutput, Monitor, KillShell, KillBash | operating machinery |
| `read` | Read, Grep, Glob, LS | reading, inspecting |
| `web` | WebSearch, WebFetch | looking outward |
| `delegate` | Agent, Task, Workflow; or busy with active followers but no recent tool | directing others |
| `think` | busy, no recent tool, no active followers | pausing, pondering |
| `other` | anything else (MCP, Skill, TodoWrite…) | generic busy |
| `none` | not busy | — |

## States

`waiting` means the session is blocked on the owner. `waitingReason` says
which: `"question"` when its last tool call asked one (AskUserQuestion),
otherwise `"permission"`. Every visualization must make it obvious; it is the most useful
signal on the page. `offline` sessions (process gone, updated in the last 6 h)
are shown faded or absent. `dim` is a shell or unknown status.

## Privacy

What leaves the feed: session names, tool names, git branch names, a working
directory's basename (`place`), file basenames, web hosts, and short free-text labels: a
Bash command's own one-line description and a subagent's description. Those
two are written by the model, so they can contain anything it chose to say
about the work. Token-shaped strings in any label (API keys, GitHub, Slack and
AWS tokens, `Bearer ...`, `password=...`, long hex) are replaced with
`[redacted]` before they leave, but treat labels as sensitive anyway.

Never included: file contents, commands, prompts, responses, full paths or the
cwd itself. The server binds to 127.0.0.1 and refuses requests whose `Host`
isn't local (see SECURITY.md). Pages must render every string as text, never
as HTML. Fixtures are synthetic: never commit real transcript data or
screenshots of a live feed.

## Fixture

`agentfeed/fixture.json` is the demo feed (`--fixture`, `?fixture=1`). It uses
relative times (`startedAgoSec`, `updatedAgoSec`, and `startedAgoSec` on
subagents), rebased to now on every build, so it never drifts. It covers every
state, every action, a stalled session, a stalled subagent, a subagent on its
own branch, both waiting reasons, and a repo whose only session is offline.

## Polling

Poll every 2 s. Animate between snapshots; never rebuild the scene from
scratch on each poll. Key everything by `id`.
