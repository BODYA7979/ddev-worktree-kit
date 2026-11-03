# Troubleshooting

| Symptom | Check or recovery |
|---|---|
| AI creates checkout but no DDEV setup runs | Verify hooks/local-environment selection; restart the AI client after settings changes. |
| `python3`, `git`, `ddev` or `docker` not found | Check the AI client's `PATH` and [requirements](requirements.md). |
| Source DDEV stopped | Start the source, then retry init. |
| Snapshot creation fails | Read the error; a fresh failure does not reuse an older backup. |
| Existing DB volume lacks a seed receipt | Preserve the volume/snapshot and inspect ownership; init refuses reset or adoption. |
| Previously seeded DB volume is missing | Inspect manually; init refuses automatic data replacement. |
| Composer/bootstrap fails | Fix that command and retry; completed receipts preserve DB and previous setup progress. |
| Override loads after Kit's override | Resolve the conflicting project override; init refuses ambiguous identity. |
| Drupal hostname resolves to wrong site | Verify generated includes, their execution order and explicit multisite mapping. |
| Shared uploads look empty in host IDE | Shared uses a container bind, not a host symlink. |
| GC retains a missing checkout | Git may still register/lock it; investigate Git ownership before cleanup. |
| Claude removal refuses a nested repository | Move or handle the independent nested checkout first; it is not owned by the parent receipt. |
| Worktree moved | Preserve its DB and inspect the registry; automatic reattach is not implemented. |

Use `ddev wtk status` and `git worktree list` for diagnosis. Do not edit `seeded`, tokens or ownership receipts to bypass safety checks. There is no automatic DB refresh/reset command.

## Upgrade from the private Worktree Env prototype

Version 0.5 adopts the Kit namespace throughout: add-on `worktree-kit`, alias `wtk`, runtime `.ddev/worktree-kit/`, config `.ddev/worktree-kit.yaml`, generated includes and shared Git registry. Simply renaming the YAML is insufficient for an active old environment. Preserve its database and migrate its ownership/configuration together before running Kit init. Stop concurrent AI lifecycle actions during the upgrade. The private prototype upgrade is verified separately from fresh public installation.
