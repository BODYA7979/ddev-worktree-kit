PYTHON ?= python3
RUFF ?= ruff
BATS ?= bats

.PHONY: check test lint test-addon package docs publication-check
check: lint test

lint:
	$(RUFF) check .
	$(RUFF) format --check .
	$(PYTHON) -m compileall -q worktree-kit tests scripts
	bash -n commands/host/worktree-kit worktree-kit/*.sh examples/*.sh
	bash -n tests/*.bash

test:
	$(PYTHON) -m unittest discover -s tests -v

# Real Docker/DDEV; release installation is a separate publication check.
test-addon:
	$(BATS) tests --filter-tags '!release'

package:
	$(PYTHON) scripts/build_release.py

docs:
	$(PYTHON) scripts/check_publication.py
	$(PYTHON) scripts/build_docs.py

publication-check:
	$(PYTHON) scripts/check_publication.py
