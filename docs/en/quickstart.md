# Manual setup reference

For the standard agent-led installation, use [Install with your agent](agent-setup.md). This page explains the commands and files that the agent prepares.

## Install in your main checkout

After the first GitHub release is published:

```sh
ddev add-on get BODYA7979/ddev-worktree-kit
```

While preparing or developing a release, install from your local source checkout:

```sh
ddev add-on get /absolute/path/to/ddev-worktree-kit
cp /absolute/path/to/ddev-worktree-kit/examples/worktree-kit.yaml .ddev/worktree-kit.yaml
```

The example is deliberately conservative: no upload synchronization, no Drupal commands and automatic deletion disabled. Review it using the [configuration reference](configuration.md). Installation checks Python before copying files; it does not start new environments or enable AI integration.

Commit the add-on runtime `.ddev/worktree-kit/`, host command `.ddev/commands/host/worktree-kit`, project config `.ddev/worktree-kit.yaml` and base `.ddev/config.yaml`. Check project ignore rules before adding those exact files.

## Start a worktree

Start your main DDEV project and Docker, create a linked Git worktree, then run from that checkout:

```sh
ddev wtk init
ddev wtk status
```

If the branch predates the add-on, use its main-checkout installation:

```sh
python3 /absolute/path/to/main/.ddev/worktree-kit/manager.py --path /absolute/path/to/worktree init
```

Successful setup returns `phase: ready`, the unique DDEV name and its URL. A second init preserves the database and completed setup receipts.

## Automate once per project

Follow [AI integration](integrations.md). Codex needs a selected local environment; Claude needs the native hook settings. A normal `ddev restart` does not create a worktree environment. The AI client invokes the registered setup callback when it creates a new worktree.
