# Очищення та uninstall

## Спочатку перевірте

```sh
ddev wtk status
ddev wtk teardown
ddev wtk gc
```

`teardown` показує preview видалення DDEV поточного managed worktree; Git зберігається. `gc` показує записані середовища, checkout яких відсутній і вже не зберігається Git. Missing-but-registered та moved checkout захищені.

Явне ручне видалення:

```sh
ddev wtk teardown --apply --yes
ddev wtk gc --apply --yes
```

Ці операції видаляють БД вибраного worktree. Під locks звіряються точні DDEV name, approot і наявні web/db ownership labels. Sweep за префіксом не виконується; shared source uploads залишаються. Main і unmanaged checkout захищені.

## Native cleanup

`cleanup.auto_delete: true` дозволяє Codex cleanup або Claude WorktreeRemove виконати DDEV teardown. Codex сам володіє своїм Git deletion; Claude adapter прибирає лише створений ним checkout, зберігаючи branches. За false callbacks зберігають DDEV; Claude все одно може прибрати свій checkout і залишити DDEV для explicit GC.

## Видалення коду add-on

1. Перед uninstall main завершіть активні агентські worktree-сесії. Від’єднайте Codex setup/cleanup scripts і Claude hook handlers, зберігши інші settings. Portable templates теж знаходять main checkout, тому перевірте всі linked worktrees. При завершенні інтеграції видаліть лише позначені Kit-секції з AGENTS.md/CLAUDE.md.
2. Вирішіть, які DDEV/DB зберегти. Якщо вони вже не потрібні, виконайте explicit teardown/GC, доки manager встановлений.
3. Виконайте `ddev add-on remove worktree-kit` у checkout, звідки прибираєте код.

DDEV прибирає кожен manifest file, який досі містить `#ddev-generated`. Видалення цього marker захищає файл від replacement/removal. User YAML, local settings, додані користувачем файли, uploads і runtime registry зберігаються. Видалення коду не є дозволом видаляти БД інших worktrees.

Generated runtime overrides не є install payload. Збережені overrides дозволяють наявному DDEV працювати після видалення host CLI. Не видаляйте їх навмання зі середовища, яке хочете зберегти.
