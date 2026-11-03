# Схожі add-ons

| Проєкт | Модель | Зв’язок із Kit |
|---|---|---|
| [ddev-dbrancher-addon](https://github.com/cballenar/ddev-dbrancher-addon) | Окремі БД для branches в одному DDEV | Інша одиниця ізоляції; Kit ізолює checkout, включно з detached HEAD. |
| [Dropsolid/ddev-wt](https://github.com/Dropsolid/ddev-wt) | Ширший workflow Git worktree, DDEV та developer tools | Kit має environment-focused core і тонкі native adapters клієнтів. |
| [ddev-fire-worktrees](https://github.com/fourkitchens/ddev-fire-worktrees) | Окремі create/start, snapshot seed і registry cleanup | Найближче порівняння; корисні принципи idempotent start, checksummed names, locks і read-only Git mounts. |
| [claude-worktree-hooks](https://github.com/tfriedel/claude-worktree-hooks) | Пара Claude create/remove hooks із власним Git lifecycle | Підтверджує модель парних hooks; Kit зберігає branches і додає DDEV ownership checks. |

Kit є окремою реалізацією, не fork. Основний акцент — YAML, явні Drupal mappings, setup receipts, seed лише fresh volume, shared/copy strategies та перевірене очищення. Перегляньте альтернативи, якщо їх workflow краще підходить вашому проєкту.
