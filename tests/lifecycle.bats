#!/usr/bin/env bats

load test_helper

setup() {
  set -eu -o pipefail
  load_libraries
}

@test "real DDEV snapshot, files, multisite and native lifecycle callbacks" {
  run python3 "${DIR}/tests/live_smoke.py"
  assert_success
  assert_output --partial 'Live verification: PASS'
}
