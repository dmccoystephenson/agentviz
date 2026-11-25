# Security

## What agentfeed reads and shows

`agentfeed` reads Claude Code's local files on the machine it runs on:

- `~/.claude/sessions/*.json`: which sessions are running, their status and name.
- The last 96 KB of each session's transcript in `~/.claude/projects/`, and of
  its subagents' transcripts.

From those it serves `/api/agents` (docs/FEED.md). Only these leave the
process: session names, tool names, git branch names, a working directory's
**basename**, and short labels (a file's basename, a web host, a Bash
command's own one-line description, a subagent's description). The last two
are the model's own words and can mention anything about the work;
token-shaped strings in labels are replaced with `[redacted]`, but treat the
feed as sensitive. File contents, commands, prompts, responses and full paths
are never included.

The server binds to 127.0.0.1 and answers only requests whose `Host` is
127.0.0.1, localhost or [::1], so other machines and web pages using DNS
rebinding can't read it. Anyone who can run code as you on the same machine
can still read the feed, as they could read `~/.claude` itself.

Labels come from your own sessions. The visualizations render them as text,
never as HTML.

## Reporting a problem

Please report vulnerabilities privately through GitHub's
"Report a vulnerability" button on this repository's Security tab, not in a
public issue.
