# Codex Desktop and Claude Code

Use the [agent-led setup](agent-setup.md) to configure the complete workflow. The installed templates are project-scoped; the agent merges them while preserving unrelated settings.


Install the add-on and review project configuration first. Enable automatic DDEV deletion explicitly:

```yaml
cleanup:
  orphan_detection: true
  auto_delete: true
```

A normal session in the main checkout does not create another environment. Docker and the source DDEV must be available for fresh seeding. A watcher is not used.

## Codex Desktop

Create a Local environment in Codex and set its scripts:

**Setup**

```sh
bash /absolute/path/to/main/.ddev/worktree-kit/codex-setup.sh
```

**Cleanup**

```sh
bash /absolute/path/to/main/.ddev/worktree-kit/codex-cleanup.sh
```

Replace the absolute path for your machine. For committed team configuration, the repository contains portable [setup](https://github.com/BODYA7979/ddev-worktree-kit/blob/main/examples/codex-setup.sh) and [cleanup](https://github.com/BODYA7979/ddev-worktree-kit/blob/main/examples/codex-cleanup.sh) recipes with main-checkout fallback for the standard `.git` layout.

Select this environment when starting a new Worktree session. Codex creates the Git checkout and provides an absolute `CODEX_WORKTREE_PATH`; callbacks validate the repository and target even when their working directory is main. Cleanup deletes DDEV and its DB before Codex removes the checkout. With `auto_delete: false`, cleanup skips DDEV deletion.

The agent can create `.codex/environments/environment.toml` from the installed version-1 template or merge an existing environment. The verified export contains `[setup] script` and `[cleanup] script`; preserve other actions and platform overrides. An absolute callback path also works on branches that do not contain the add-on yet.

## Claude Code

Merge the repository's [hook template](https://github.com/BODYA7979/ddev-worktree-kit/blob/main/examples/claude.settings.json) into `.claude/settings.json`, preserving existing settings and unrelated hooks. Use only one `WorktreeCreate` provider. For a machine-local setup, these are the three command paths:

| Event | Command | Timeout |
|---|---|---|
| `WorktreeCreate` | `bash /absolute/path/to/main/.ddev/worktree-kit/claude-worktree-create.sh` | 600s |
| `WorktreeRemove` | `bash /absolute/path/to/main/.ddev/worktree-kit/claude-worktree-remove.sh` | 600s |
| `SessionStart`, matcher `startup|resume` | `bash /absolute/path/to/main/.ddev/worktree-kit/claude-session-start.sh` | 600s |

Restart Claude after changing hooks. Start its native worktree flow, for example `claude --worktree feature-name`.

`WorktreeCreate` replaces Claude's default Git creation. Our adapter creates `<main>/.claude/worktrees/<name>` on `worktree-<name>`, initializes DDEV, and prints only its absolute path after success. An existing branch is reused without reset; an unowned checkout at that path is refused. On older branches, the adapter copies only its own hook handlers into local Claude settings.

`WorktreeRemove` first cleans the owned DDEV and then force-removes the exact owned checkout. This follows Claude's decision to discard it, so uncommitted checkout changes may be discarded. **Branches and shared source uploads are preserved.** Nested Git checkouts, locked/moved worktrees, ownership mismatches and cleanup failures block checkout removal. With automatic DDEV deletion disabled, the checkout is removed and DDEV remains for manual GC.

`SessionStart` provides idempotent setup/resume. `SessionEnd` is not used: a session ending does not imply that its worktree should be deleted. Custom `WorktreeCreate` does not automatically process `.worktreeinclude`; use explicit `local_files` for required local text settings.

Contracts: [Claude WorktreeCreate](https://code.claude.com/docs/en/hooks#worktreecreate), [WorktreeRemove](https://code.claude.com/docs/en/hooks#worktreeremove), [Codex local environments](https://learn.chatgpt.com/docs/environments/local-environment).
