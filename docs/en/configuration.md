# Configuration

Use `.ddev/worktree-kit.yaml`. A worktree's own config takes precedence; if absent, the manager reads the main checkout's config. Configuration stays YAML; JSON output and the internal Git-metadata registry are machine protocols.

## Complete default example

```yaml
version: 1

worktree:
  name: "{project}-wt-{slug}-{hash}"
  auto_start: true
  tld: ddev.site

database:
  source: primary
  strategy: snapshot
  snapshot: fresh
  create_if_missing: true
  refresh: manual

setup:
  composer_install: true
  composer_root: ''
  commands: []

local_files:
  - .ddev/config.local.yaml

files:
  strategy: none
  mappings: []

drupal:
  multisite:
    enabled: false
    sites: {}

cleanup:
  orphan_detection: true
  auto_delete: false
```

| Setting | Behavior |
|---|---|
| `worktree.name` | Supports `{project}`, `{slug}`, `{hash}`; the hash is required. Recorded names stay stable on repeat init. |
| `worktree.auto_start` | `false` prepares files and returns `prepared`; `ddev wtk init --start` performs seed/setup. |
| `database.source` | `primary` or an absolute path to a different registered checkout in this repository. |
| `database.snapshot` | `fresh` creates a new source snapshot; `latest` explicitly reuses the latest compatible one. |
| `database.create_if_missing` | Allows creating a snapshot when `latest` has no compatible backup. |
| `database.strategy`, `refresh` | Currently `snapshot` and `manual`; automatic DB replacement is not supported. |
| `setup.composer_install` | Installs dependencies when manifests change or vendor is missing. |
| `setup.composer_root` | Checkout-relative Composer directory; empty means repository root. |
| `setup.commands` | Ordered commands after DB verification and Composer; see [setup commands](setup-commands.md). |
| `local_files` | Copies only missing text files from source; add project-specific local settings explicitly. |
| `files` | `none`, `shared`, `copy` with explicit per-directory mappings. |
| `drupal.multisite` | Explicit site-directory → hostname/database mapping. |
| `cleanup.orphan_detection` | Enables CLI GC. |
| `cleanup.auto_delete` | Allows native cleanup callbacks to delete their worktree DDEV/DB; defaults to false. |

Source/target DB family and version must match. Fresh seeding requires a running source. A failed fresh snapshot never silently falls back to an older backup. User-selected `latest` backups are retained; manager-created temporary snapshots are removed only after successful seed verification.

Section-based YAML is preferred. Legacy flat configuration and `worktree-kit.json` remain readable for configuration-format migration; do not keep YAML and JSON together. This does not adopt old Worktree Env runtime state automatically.
