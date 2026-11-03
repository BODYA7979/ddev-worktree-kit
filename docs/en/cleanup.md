# Cleanup and uninstall

## Inspect first

```sh
ddev wtk status
ddev wtk teardown
ddev wtk gc
```

`teardown` previews removal of the current managed worktree's DDEV. It preserves Git. `gc` previews recorded environments whose checkout is absent and no longer retained by Git. A missing-but-registered or moved checkout is protected.

Explicit manual deletion:

```sh
ddev wtk teardown --apply --yes
ddev wtk gc --apply --yes
```

These operations delete the selected worktree database. They verify exact DDEV name, approot and available web/db ownership labels under locks. They do not sweep resources by prefix and preserve shared source uploads. Main and unmanaged checkouts are protected.

## Native cleanup

`cleanup.auto_delete: true` permits Codex cleanup or Claude WorktreeRemove to apply DDEV teardown. Codex owns its Git deletion; the Claude adapter removes only the checkout it created, preserving branches. With false, callbacks retain DDEV; Claude can still remove its owned checkout, leaving DDEV for explicit GC.

## Remove the add-on code

1. Finish active agent worktree sessions before uninstalling main. Detach Codex setup/cleanup scripts and Claude hook handlers, preserving unrelated settings. Portable templates resolve the main checkout too, so check all linked worktrees. Remove only the marked Kit sections from AGENTS.md/CLAUDE.md when retiring their integration.
2. Decide which DDEV environments/DBs to retain. Run explicit teardown/GC while the manager is still installed if they should be deleted.
3. Run `ddev add-on remove worktree-kit` in the checkout where code should be removed.

DDEV removes each manifest-listed file that still contains `#ddev-generated`. Removing that marker opts a file out of replacement/removal. User YAML, local settings, extra user files, uploads and runtime registry are retained. Removing the code is not permission to delete other worktree databases.

Generated runtime overrides are not install payload. Retained overrides let an existing DDEV continue working after host CLI removal. Do not remove them arbitrarily from an environment you intend to keep.
