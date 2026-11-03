#!/usr/bin/env bats

load test_helper

setup() {
  set -eu -o pipefail
  local brew_prefix
  brew_prefix=$(brew --prefix 2>/dev/null || true)
  export BATS_LIB_PATH="${BATS_LIB_PATH:-}:${brew_prefix}/lib:/usr/lib/bats"
  bats_load_library bats-support
  bats_load_library bats-assert
  export DIR="$(cd "$(dirname "${BATS_TEST_FILENAME}")/.." && pwd -P)"
  export GITHUB_REPO="${GITHUB_REPO:-${GITHUB_REPOSITORY:-}}"
  export DDEV_NONINTERACTIVE=true
  export DDEV_NO_INSTRUMENTATION=true
  export PYTHONDONTWRITEBYTECODE=1
  export CI=true
  export PROJNAME="wtk-package-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:10])')"
  TESTDIR=$(mktemp -d "${TMPDIR:-/tmp}/wtk-package.XXXXXX")
  export TESTDIR="$(cd "${TESTDIR}" && pwd -P)"
  cd "${TESTDIR}"
  run ddev config --project-name="${PROJNAME}" --project-type=php --project-tld=ddev.site
  assert_success
  git init -q -b main
  git add .ddev/config.yaml
  git -c user.name=Fixture -c user.email=fixture@example.invalid commit -qm fixture
}

teardown() {
  set -eu -o pipefail
  # Never discover or delete a project by prefix; this is this test's UUID name.
  if [ -n "${PROJNAME:-}" ] && [ -d "${TESTDIR:-}" ]; then
    ddev --skip-hooks delete --omit-snapshot --yes "${PROJNAME}" >/dev/null 2>&1
  fi
  if [ -n "${GITHUB_ENV:-}" ]; then
    echo "TESTDIR=${TESTDIR}" >> "${GITHUB_ENV}"
  elif [ -n "${TESTDIR:-}" ]; then
    rm -rf -- "${TESTDIR}"
  fi
}

@test "install from directory and run host CLI before DDEV starts" {
  run ddev add-on get "${DIR}"
  assert_success
  health_checks
}

@test "unsupported host Python fails before installing payload" {
  mkdir "${TESTDIR}/unsupported-runtime"
  printf '#!/usr/bin/env bash\necho "fixture unsupported Python" >&2\nexit 1\n' > "${TESTDIR}/unsupported-runtime/python3"
  chmod +x "${TESTDIR}/unsupported-runtime/python3"
  run env PATH="${TESTDIR}/unsupported-runtime:${PATH}" ddev add-on get "${DIR}"
  assert_failure
  assert_output --partial 'fixture unsupported Python'
  [ ! -e .ddev/worktree-kit/manager.py ]
  [ ! -e .ddev/commands/host/worktree-kit ]
}

@test "install from archive and reinstall preserve user YAML" {
  run python3 "${DIR}/scripts/build_release.py" --output "${TESTDIR}/candidate.tar.gz"
  assert_success
  run python3 - "${TESTDIR}/candidate.tar.gz" <<'PY'
import sys, tarfile
from pathlib import PurePosixPath
with tarfile.open(sys.argv[1]) as archive:
    for entry in archive.getmembers():
        path = PurePosixPath(entry.name)
        assert not set(path.parts) & {'.git', '.github', 'tests', '__pycache__'}, entry.name
        assert not path.name.startswith('._'), entry.name
PY
  assert_success
  run ddev add-on get "${TESTDIR}/candidate.tar.gz"
  assert_success
  printf 'version: 1\nfiles:\n  strategy: none\n# keep this user comment\n' > .ddev/worktree-kit.yaml
  cp .ddev/worktree-kit.yaml expected.yaml
  run ddev add-on get "${TESTDIR}/candidate.tar.gz"
  assert_success
  cmp expected.yaml .ddev/worktree-kit.yaml
  health_checks
}

@test "removal deletes managed payload and preserves user-owned files" {
  run ddev add-on get "${DIR}"
  assert_success
  cp "${DIR}/examples/worktree-kit.yaml" .ddev/worktree-kit.yaml
  cp .ddev/worktree-kit.yaml expected.yaml
  printf 'user data\n' > .ddev/worktree-kit/keep-user.txt
  # Removing the marker is DDEV's explicit opt-out from replacement/removal.
  sed '/^#ddev-generated$/d' .ddev/worktree-kit/adapter.sh > modified.sh
  cp modified.sh .ddev/worktree-kit/adapter.sh
  run ddev add-on remove worktree-kit
  assert_success
  cmp expected.yaml .ddev/worktree-kit.yaml
  cmp modified.sh .ddev/worktree-kit/adapter.sh
  [ "$(cat .ddev/worktree-kit/keep-user.txt)" = 'user data' ]
  run python3 - "${DIR}" "${TESTDIR}" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'worktree-kit'))
from config_io import load_yaml
manifest = load_yaml((Path(sys.argv[1]) / 'install.yaml').read_text())
for relative in manifest['project_files']:
    if relative != 'worktree-kit/adapter.sh':
        assert not (Path(sys.argv[2]) / '.ddev' / relative).exists(), relative
PY
  assert_success
}

# bats test_tags=release
@test "install from release" {
  if [ -z "${GITHUB_REPO}" ] || [ -z "${ADDON_RELEASE_VERSION:-}" ]; then
    skip 'Publication check requires GITHUB_REPO and ADDON_RELEASE_VERSION'
  fi
  run ddev add-on get "${GITHUB_REPO}" --version="${ADDON_RELEASE_VERSION}"
  assert_success
  health_checks
}
