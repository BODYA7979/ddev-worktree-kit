# Ownership і модель виконання

Manager визначає checkout, окремий Git directory worktree та спільний Git common directory. Підтримуються detached worktrees і стабільні імена, незалежні від branch name.

Init пише локальні DDEV identity/Compose overrides, монтує Git metadata read-only, отримує named snapshot, seed лише fresh DB volume, перевіряє application tables, потім виконує Composer і setup-команди. Наявні initialized DB не скидаються й не пересіваються автоматично.

## Стан

Спільна Git metadata містить `ddev-worktree-kit/registry.json` та kernel locks. Receipts зберігають path, Git directory, DDEV name, ownership token, seed completion, Composer/bootstrap fingerprints і прогрес команд. Точні generated paths виключаються через локальний Git `info/exclude`.

Claude має окремий adapter receipt і випадковий marker у Git directory worktree. Це захищає від видалення після зовнішнього remove/recreate checkout за тим самим path. Branches не видаляються. Removal відхиляє nested Git boundaries і повторно перевіряє DDEV при retry.

Namespaced lock у глобальній DDEV directory серіалізує snapshot/start/cleanup цього add-on між repo. Інші інструменти цей lock не використовують; уникайте паралельних ручних lifecycle операцій під час setup або міграції.

## Межі

Core не створює Git worktrees. Codex/ручний Git володіє своїм checkout; native Claude adapter створює/прибирає тільки власний. Джерелом БД є інший зареєстрований checkout цього самого repo. Files strategies задаються явно та захищають від source/target overlap і symlink traversal.

Custom external services/volumes, remote Docker, DB refresh, довільне переміщення worktree та native Windows не входять до перевіреної області. Під час зміни namespace DDEV-ім’я наявного managed середовища зберігається заради його існуючого DB volume.
