# Усунення проблем

| Симптом | Перевірка або відновлення |
|---|---|
| AI створює checkout, але setup DDEV не викликається | Перевірте hooks/local-environment selection; після зміни settings перезапустіть клієнт. |
| Не знайдено `python3`, `git`, `ddev` або `docker` | Перевірте `PATH` AI-клієнта та [вимоги](requirements.md). |
| Source DDEV зупинений | Запустіть source і повторіть init. |
| Snapshot creation failed | Прочитайте помилку; fresh failure не використовує старий backup. |
| DB volume є, але seed receipt немає | Збережіть volume/snapshot і дослідіть ownership; init не скидає й не усиновлює БД. |
| Зник раніше seeded DB volume | Дослідіть вручну; init відмовляє в автоматичній заміні даних. |
| Помилка Composer/bootstrap | Виправте команду та повторіть; receipts зберігають БД і попередній прогрес. |
| Пізніший override за Kit override | Приберіть конфлікт налаштувань проєкту; неоднозначна identity відхиляється. |
| Drupal hostname відкриває не той site | Перевірте generated includes, порядок виконання та multisite mapping. |
| Shared uploads порожні в host IDE | Shared використовує container bind, а не host symlink. |
| GC зберігає missing checkout | Git може досі його реєструвати/блокувати; спочатку дослідіть Git ownership. |
| Claude removal відмовляє через nested repo | Спочатку перемістіть чи обробіть незалежний nested checkout; parent receipt ним не володіє. |
| Worktree переміщено | Збережіть БД і дослідіть registry; automatic reattach ще немає. |

Для діагностики використайте `ddev wtk status` і `git worktree list`. Не редагуйте `seeded`, tokens або ownership receipts заради обходу перевірок. Автоматичної DB refresh/reset команди немає.

## Оновлення з приватного прототипу Worktree Env

Версія 0.5 повністю переходить на Kit namespace: add-on `worktree-kit`, аліас `wtk`, runtime `.ddev/worktree-kit/`, конфіг `.ddev/worktree-kit.yaml`, generated includes і shared Git registry. Для активного старого середовища просто перейменувати YAML недостатньо. Збережіть БД і мігруйте ownership/configuration разом перед Kit init. На час оновлення зупиніть паралельні AI lifecycle дії. Оновлення приватного прототипу перевіряється окремо від чистого публічного встановлення.
