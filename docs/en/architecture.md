# Ownership and execution model

The manager identifies the checkout, per-worktree Git directory and shared Git common directory. It supports detached worktrees and stable names independent of branch names.

Initialization writes local DDEV identity/Compose overrides, mounts Git metadata read-only, obtains a named snapshot, seeds only a fresh DB volume, verifies application tables, then runs Composer and setup commands. Existing initialized DBs are never silently reset or re-seeded.

## State

Shared Git metadata contains `ddev-worktree-kit/registry.json` and kernel locks. Receipts record path, Git directory, DDEV name, ownership token, seed completion, Composer/bootstrap fingerprints and command progress. Exact generated paths are excluded through Git's local `info/exclude`.

Claude has a separate adapter receipt and a random marker in the per-worktree Git directory. This prevents deletion after an external checkout removal/recreation at the same path. Branches are never deleted. Removal rejects nested Git boundaries and rechecks DDEV on retry.

A namespaced lock in DDEV's global directory serializes this add-on's snapshot/start/cleanup across repositories. Other tools do not share that lock; avoid concurrent manual lifecycle operations during setup or migration.

## Boundaries

The core does not create Git worktrees. Codex/manual Git owns its checkout; the native Claude adapter creates/removes only its own checkout. DB source is a different registered checkout of the same repository. File strategies are explicit and protect against source/target overlap and symlink traversal.

Custom external services/volumes, remote Docker, DB refresh, arbitrary worktree relocation and native Windows are outside the verified scope. A managed environment's database name is retained during a namespace upgrade to preserve its existing volume.
