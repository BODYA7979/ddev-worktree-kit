# Install with your coding agent

Agent-led setup is the normal entry point: DDEV + worktrees + agents are configured together.

Paste this into Codex or Claude Code from the project's repository:

```text
Set up DDEV Worktree Kit here for Codex Desktop and Claude Code.
Read and follow this runbook:
https://raw.githubusercontent.com/BODYA7979/ddev-worktree-kit/main/AGENT_SETUP.md

Install the add-on, merge project/client settings and agent instructions,
and enable automatic setup and cleanup for agent-created worktrees.
Preserve data, unrelated settings and the existing file strategy;
otherwise leave uploads unsynchronized.
Verify setup and report changed files. Do not reset/reseed a database or
create/remove a worktree without my explicit request for that test.
```

Name just one client in the prompt if that is all you use. The agent can install the add-on, read its installed boilerplates and edit the project-scoped configurations itself. The first release must exist for the GitHub install command; before publication, give the agent the local source checkout explicitly.

The [agent runbook](https://github.com/BODYA7979/ddev-worktree-kit/blob/main/AGENT_SETUP.md) contains exact commands, defaults, merge rules, verification and conflict handling. Installed templates include YAML, Claude hooks, Codex environment TOML and an AGENTS/CLAUDE instruction fragment.

The agent preserves unrelated hooks, actions and existing project configuration. A competing WorktreeCreate provider requires a concrete integration choice; it is not overwritten silently. Setup does not require running manual init commands afterward.

After setup, reload Claude hooks and select the prepared local environment for a new Codex Worktree session if the client requires selection. Follow the [manual reference](quickstart.md) for diagnosis or controlled verification, and [integration details](integrations.md) for the native lifecycle contract.
