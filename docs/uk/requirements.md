# Вимоги до хоста

| Вимога | Причина |
|---|---|
| macOS або Linux | Host-скрипти використовують Unix-блокування `fcntl.flock`. |
| Python 3.10+ як `python3` | Host manager і adapters; це додаткова вимога понад DDEV. |
| Git 2.36+ | Використовуються `git worktree list --porcelain -z` та абсолютні Git metadata paths. |
| DDEV 1.25.4+ stable | Потрібний fresh-volume `start --seed-snapshot`; prerelease відхиляється. |
| Доступний `docker` CLI і запущений provider | Ownership-перевірки volumes/containers та bind mounts. |
| Non-bare main checkout з DDEV | Джерело seed та спільна Git metadata. |
| MySQL або MariaDB | Поточна перевірка snapshot підтримує ці сімейства БД. |

PHP, Composer і Drush на хості не потрібні: вони запускаються через DDEV. Pure-Python PyYAML уже в пакеті; runtime не потребує встановлення `pip`, virtualenv, Node.js, `jq` чи `rsync`. Bats, Ruff та Zensical потрібні лише розробникам пакета.

AI-клієнт має знаходити `python3`, `git`, `ddev` і `docker` у `PATH`. Графічна програма може успадкувати інший path, ніж термінал. Install перевіряє Python і DDEV; повного host doctor поки немає.

## Перевірені платформи

macOS ARM64 пройшла реальні DDEV-тести. Linux AMD64/ARM64 та minimum/latest stable DDEV налаштовані в CI; результати remote CI слід перевірити після публікації. Native Windows не підтримується. WSL2 є можливим Linux-хостом, але AI-to-WSL інтеграцію наскрізно ще не тестували. Git, hooks, Python і DDEV мають виконуватися в одному Linux-середовищі.

Docker повинен мати доступ до bind mounts обох checkout і спільної Git metadata. Remote daemons, сумісність із Podman та довільні custom service volumes не перевірені. Кожен worktree потребує окремого DB volume і ресурсів контейнерів.

[Офіційна інсталяція DDEV](https://docs.ddev.com/en/stable/users/install/) охоплює Docker/provider і certificates. Наші обмеження Python, Git-version та Unix-lock є додатковими. Потрібний NUL-формат worktree output з’явився у Git 2.36: [release notes](https://github.com/git/git/blob/v2.36.0/Documentation/RelNotes/2.36.0.txt).
