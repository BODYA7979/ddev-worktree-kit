# Changelog

Versions before the first GitHub publication were local prototype packages.

## [0.5.1] - 2026-11-04

### Fixed
- Distinguish a new checkout from a removed worktree when Git reuses its internal metadata directory. Preserve the old environment receipt and database while creating an independent environment.
- Verify checkout generation before reusing a database or running cleanup; keep moved worktrees and unknown ownership protected.

## [0.5.0] - 2026-11-03

### Added
- Agent-led setup prompts/runbook and installed YAML, Claude, Codex and AGENTS/CLAUDE boilerplates.
- English-primary and Ukrainian documentation, a Zensical site and GitHub Pages workflow.
- Checked tag-to-release automation with runtime/docs/package and real DDEV gates.
- Native DDEV alias `wtk` for the `worktree-kit` command.

### Changed
- Fully adopt DDEV Worktree Kit naming: add-on id, runtime/config paths, generated files, registry namespace and ownership labels.
- Correct the minimum Git requirement to 2.36 for NUL-delimited worktree output.
- Keep local adoption evidence outside the public source and release payload.

## [0.4.1] - 2026-11-03

- Align the prototype package with the DDEV template, add Bats/CI and clean archive builds.

## [0.4.0] - 2026-11-03

- Add native Claude WorktreeCreate/WorktreeRemove lifecycle with ownership protection.

## [0.3.0] - 2026-11-03

- Add scoped Codex setup/cleanup and environment teardown.

## [0.2.1] - 2026-11-03

- Correct DDEV's MySQL DB volume naming check without resetting existing data.

## [0.2.0] - 2026-11-03

- Add YAML configuration, shared/copy uploads and explicit file synchronization.

## [0.1.0] - 2026-11-03

- Initial environment manager prototype.
