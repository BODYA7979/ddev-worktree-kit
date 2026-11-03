# Project setup commands

Commands run in order after DDEV starts, the target database is verified and Composer finishes, before `phase: ready`.

```yaml
setup:
  composer_install: true
  commands:
    - "ddev drush cr"
```

For Drupal database updates, config import and deploy hooks, use `ddev drush deploy -y` instead of the cache-only command. Drush deploy already rebuilds caches; see the [Drush deploy contract](https://www.drush.org/12.x/deploycommand/).

## Execution rules

Strings are split into arguments without shell expansion. An argv array is also supported:

```yaml
setup:
  commands:
    - [ddev, drush, deploy, '-y']
    - [bash, .ddev/scripts/worktree-setup.sh]
```

A command beginning with `ddev` runs on the host in the target checkout. Other commands are executed through `ddev exec --raw --` in its container. For `&&`, pipes or environment expansion, put the logic in an explicit shell script. User scripts are project-owned and must be committed or supplied through local setup.

## Repeat and failure behavior

Successful commands receive checkpoints. Repeat init with unchanged configuration and Composer manifests skips completed bootstrap. A changed configuration/manifest, or a required Composer re-install, can run bootstrap again on the next init. A failed command stops setup; retry resumes from the unfinished command.

Commands must be idempotent: a crash after command execution but before receipt persistence can repeat that command. This is a setup phase, not an exactly-once event bus. Separate `after_start` / `before_remove` user hooks are not implemented. DDEV's ordinary hooks are skipped during manager snapshot/start; use this setup phase for required initialization.
