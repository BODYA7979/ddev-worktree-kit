# Agent-led setup: DDEV Worktree Kit

This is the installation runbook for a coding agent acting on the user's current project. DDEV, Git worktrees and the agent lifecycle are one workflow. Complete the chosen client integration as part of setup.

## Scope and defaults

- Work in the current repository and its actual main checkout, determined with Git. Do not modify unrelated projects or global agent settings.
- Preserve application code, databases, uploads, existing configuration and unrelated hooks. Inspect before editing and keep a local backup of each existing config you change.
- Configure both Codex Desktop and Claude Code project files unless the user names a particular client. Do not install the AI clients themselves.
- Keep uploads at `none` unless the user requests `shared` or `copy`. Preserve an existing file strategy.
- For the requested complete native lifecycle, set `cleanup.auto_delete: true` for agent-created DDEV environments; this permits deleting those worktree databases when the client removes them. Preserve the source database and uploads.
- Do not reset, import over, or reseed an existing worktree database. Do not run `drush deploy` automatically unless requested. Do not create a test worktree or remove a working one unless the task authorizes that lifecycle test.

## 1. Inspect prerequisites and the project

Find the Git main checkout using `git worktree list --porcelain -z`, not assumptions about the location of `.git`. Require a non-bare repository, Git 2.36+, Python 3.10+, Bash and DDEV 1.25.4+ stable. The same environment used by the client must find `python3`, `git`, `ddev` and `docker`. Native Windows is unsupported. Read `.ddev/config.yaml` and effective DDEV configuration to identify docroot and database type/version; current support is MySQL/MariaDB.

Check Docker and source DDEV status. If Docker is available and the configured local source project is stopped, start it with `ddev start` in main; preserve its database and do not import/reset it. Report missing system prerequisites rather than changing Docker/system configuration silently. If DDEV itself is not configured, explain that prerequisite rather than inventing a new project setup. If a private Worktree Env prototype/registry is present, preserve it and use a reviewed namespace migration; merely copying a new config is insufficient.

## 2. Install the add-on

In the main checkout, after a published GitHub release exists:

```sh
ddev add-on get BODYA7979/ddev-worktree-kit
```

For an explicitly provided local source checkout, use `ddev add-on get /absolute/path/to/ddev-worktree-kit` instead. Do not claim a release install succeeded when no release exists.

The installed boilerplates are under `.ddev/worktree-kit/templates/`. They ship with DDEV ownership markers. **Do not copy that marker into user-owned destination configuration.**

## 3. Prepare project YAML

If `.ddev/worktree-kit.yaml` is absent, copy the installed `templates/worktree-kit.yaml` while removing its `#ddev-generated` comment. If present, merge required settings and preserve its comments/values where possible; do not overwrite it with defaults.

Use the project's actual docroot in any file mappings/local settings. Add only required existing local text settings to `local_files`, such as `<docroot>/sites/default/settings.local.php`; do not print credentials. Set `worktree.auto_start: true` and `cleanup.auto_delete: true` for the requested automatic lifecycle. Preserve existing setup commands. For Drupal with Drush and no existing setup commands, `ddev drush cr` is a suitable minimal setup; ask only if a project-specific policy is genuinely unclear. Multisite requires the documented per-site includes and explicit mapping; do not guess database names.

## 4. Configure Claude Code

Read `.ddev/worktree-kit/templates/claude.settings.json`. Merge **only its `hooks`** into the project's `.claude/settings.json`; the template's `#ddev-generated` property is install metadata, not a Claude setting.

Preserve all unrelated keys, event groups and hook commands. Replace/deduplicate existing Worktree Kit handlers instead of appending duplicates. Register the paired `WorktreeCreate` / `WorktreeRemove` handlers and `SessionStart` with matcher `startup|resume`, timeout 600 seconds. The portable commands locate the main checkout through Git and exec the installed wrapper; JSON stdin and the create hook's path-only stdout are preserved.

If another tool already owns `WorktreeCreate`, report that concrete conflict and preserve its configuration until the user chooses how to replace/integrate it. Multiple create providers cannot safely return one checkout. Check local settings for conflicting overrides too.

## 5. Configure Codex Desktop

Use `.ddev/worktree-kit/templates/codex-environment.toml` for the verified version-1 native schema: `version`, `name`, `[setup] script`, `[cleanup] script`.

If no environment exists, create `.codex/environments/environment.toml` from that template without the DDEV marker. If one exists, merge the setup/cleanup callbacks into the selected project environment, preserving its display name, other actions and platform overrides. Inspect existing scripts before replacing them; retain required project setup steps in the correct order. Keep a backup, and avoid adding a second duplicate environment silently.

The supplied callbacks use Codex's `CODEX_WORKTREE_PATH` to select the target. Do not hardcode a temporary worktree path. Do not invent an undocumented native schema or edit Codex's private database. If the installed client does not recognize the verified file format, obtain its UI-generated export and adapt to that owning schema.

## 6. Record agent working instructions

Merge the marked `worktree-kit:start` / `worktree-kit:end` section from `.ddev/worktree-kit/templates/AGENTS.fragment.md` into project `AGENTS.md` and `CLAUDE.md` (for the selected clients). Remove the DDEV marker from the fragment first. Preserve existing instructions; replace the existing Kit section on repeat setup instead of duplicating it. The section tells agents to reuse their assigned worktree, run DDEV there and preserve ownership/database safety.

## 7. Verify and report

- Validate JSON/TOML/YAML and the three Claude event handlers; ensure unrelated configuration is preserved.
- Run `ddev worktree-kit --help` and `ddev wtk --help` in main, then `ddev wtk setup`; main must return `skipped`, without creating a second environment.
- Verify Docker/source availability and installed callback paths. A lifecycle test in a disposable worktree is useful only when authorized; leave current worktrees and databases intact.
- List changed files and confirm the chosen clients are configured. If needed, give only the remaining UI action: restart Claude to reload hooks; select the prepared local environment in a new Codex Worktree session.
- Explain what to commit: add-on runtime/host command, project YAML, project client configurations and the scoped agent instruction sections. Do not commit credentials, local state or unrelated changes automatically.

The intended result is that creating an agent worktree prepares its DDEV automatically and native removal cleans the owned environment. The user should not need to run `init` by hand during normal use.
