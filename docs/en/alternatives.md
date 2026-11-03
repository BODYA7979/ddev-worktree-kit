# Related add-ons

| Project | Model | Relationship to Kit |
|---|---|---|
| [ddev-dbrancher-addon](https://github.com/cballenar/ddev-dbrancher-addon) | Branch-specific databases in one DDEV environment | Different isolation unit; Kit isolates the checkout, including detached HEAD. |
| [Dropsolid/ddev-wt](https://github.com/Dropsolid/ddev-wt) | Broader Git worktree, DDEV and developer workflow | Kit keeps an environment-focused core and thin native client adapters. |
| [ddev-fire-worktrees](https://github.com/fourkitchens/ddev-fire-worktrees) | Separate create/start flows, snapshot seeding and registry cleanup | Closest comparison; useful principles include idempotent start, checksummed names, locks and read-only Git mounts. |
| [claude-worktree-hooks](https://github.com/tfriedel/claude-worktree-hooks) | Paired Claude create/remove hooks owning Git lifecycle | Confirms the paired-hook model; Kit preserves branches and adds DDEV ownership checks. |

Kit is a separate implementation, not a fork. It emphasizes YAML configuration, explicit Drupal mappings, setup receipts, fresh-volume-only seeding, shared/copy file strategies and checked cleanup. Review the alternatives if their workflow better fits your project.
