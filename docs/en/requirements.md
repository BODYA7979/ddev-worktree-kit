# Host requirements

| Requirement | Reason |
|---|---|
| macOS or Linux | The host scripts use Unix `fcntl.flock` locks. |
| Python 3.10+ as `python3` | Host manager and adapters; this requirement is additional to DDEV. |
| Git 2.36+ | Uses `git worktree list --porcelain -z` and absolute Git metadata paths. |
| DDEV 1.25.4+ stable | Fresh-volume `start --seed-snapshot` support; prereleases are rejected. |
| Accessible `docker` CLI and running provider | Volume/container ownership checks and bind mounts. |
| A non-bare main checkout with DDEV | Seed source and shared Git metadata. |
| MySQL or MariaDB | Current snapshot verification supports these database families. |

No host PHP, Composer or Drush installation is needed: these run through DDEV. PyYAML is bundled as pure Python source; no runtime `pip`, virtualenv, Node.js, `jq` or `rsync` setup is needed. Bats, Ruff and Zensical are development tools only.

The AI client's environment must find `python3`, `git`, `ddev` and `docker` in `PATH`. GUI applications can inherit a different path from your terminal. Python and DDEV versions are checked at installation; a comprehensive host doctor is not implemented yet.

## Platform coverage

macOS ARM64 has passed real DDEV tests. Linux AMD64/ARM64 and minimum/latest stable DDEV are configured in CI; remote results must be checked after publication. Native Windows is unsupported. WSL2 is a possible Linux host, but its AI-to-WSL integration has not been tested end to end. Git, hooks, Python and DDEV must run in the same Linux environment.

Docker must be able to bind-mount both checkouts and shared Git metadata. Remote daemons, Podman compatibility and arbitrary custom service volumes have not been validated. Each worktree needs its own database volume and container resources.

[Official DDEV installation](https://docs.ddev.com/en/stable/users/install/) covers Docker/provider and certificate setup. Our Python, Git-version and Unix-lock restrictions are additional. Git 2.36 introduced the required NUL-delimited worktree output in its [release notes](https://github.com/git/git/blob/v2.36.0/Documentation/RelNotes/2.36.0.txt).
