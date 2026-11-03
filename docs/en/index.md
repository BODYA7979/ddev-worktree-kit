# DDEV Worktree Kit

Give each AI coding worktree its own DDEV environment: a unique URL, an independent database seeded from your main checkout, dependencies and project setup commands.

Use **`ddev wtk`** as the short form of **`ddev worktree-kit`**.

- **Codex Desktop:** Codex creates the Git checkout; local-environment setup and cleanup scripts manage DDEV.
- **Claude Code:** paired `WorktreeCreate` / `WorktreeRemove` hooks create and remove the checkout and its DDEV environment. Git branches are preserved.
- **Manual Git:** initialize an existing linked worktree with `ddev wtk init`.

Uploads default to `none`. Choose an explicit shared Docker bind or an independent copy per directory. No background watcher is installed.

[Install with your agent](agent-setup.md), check [host requirements](requirements.md), then connect [Codex or Claude](integrations.md).

## Scope

Kit coordinates DDEV, Git worktrees and native agent lifecycle as one workflow. Its internal manager/adapters divide responsibilities for environment and checkout ownership. Initialization never resets an existing database. Destructive cleanup checks recorded ownership; ordinary garbage collection previews changes until explicitly applied.

This is a community DDEV add-on. Registry discovery and official DDEV maintenance are separate steps; see [publishing](publishing.md).
