# Packaging tests use real DDEV/Git and only their own temporary project names.
load_libraries() {
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
}

health_checks() {
  run ddev worktree-kit --help
  assert_success
  assert_output --partial teardown
  run ddev wtk --help
  assert_success
  assert_output --partial teardown
  run python3 "${TESTDIR}/.ddev/worktree-kit/manager.py" setup
  assert_success
  assert_output --partial 'main checkout'
}
