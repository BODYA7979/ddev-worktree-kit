# Development and verification

Clone the source repository. Runtime users do not need these developer dependencies.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
make check PYTHON=.venv/bin/python RUFF=.venv/bin/ruff
```

`make check` runs Ruff, Python compilation, Bash syntax checks and process-level contracts using real Git with controlled DDEV/Docker doubles.

## Real DDEV tests

Install Bats core, bats-support and bats-assert, then:

```sh
make test-addon
```

The suite checks directory/archive installation, Python preflight before file copying, user-config-preserving reinstall, marker-aware uninstall, the `wtk` alias, DB snapshot seeding, repeat setup, Composer/bootstrap, shared/copy/sync, multisite HTTP and native callbacks. Fixtures use unique names and remove only their own resources. Existing projects are not selected by name prefix.

Claude's native create/remove cycle was also confirmed by a user on a real Drupal project. Codex callbacks were tested with its saved local-environment configuration; end-to-end native client coverage should still be expanded. The PHP multisite fixture validates generated includes, not a complete Drupal kernel test.

## Documentation site

English is primary; matching Ukrainian pages live under `docs/uk/`. Keep both languages in sync.

```sh
python3 -m venv .venv-docs
.venv-docs/bin/python -m pip install -r requirements-docs.txt
make docs PYTHON=.venv-docs/bin/python
```

The pinned [Zensical](https://zensical.org/docs/) generator accepts our YAML configuration. English builds at the site root and Ukrainian at `/uk/`, each with its own search/UI language. The combined build validates internal links, language coverage and project-subpath URLs. Docs dependencies require Python 3.11+ and are separate from the add-on's Python 3.10+ runtime.

For local preview, build with `python scripts/build_docs.py --site-url http://127.0.0.1:8000/`, then serve `site/` with `python -m http.server 8000 --directory site` using the docs environment.

## Release payload

`make package` creates a single-root add-on tarball and SHA-256 file under `dist/`, respecting `.gitattributes` export rules. It verifies that every manifest payload file is included. Tests, workflows, build tooling, caches and local project evidence are excluded. See [publishing](publishing.md) for the checked tag-to-release workflow.
