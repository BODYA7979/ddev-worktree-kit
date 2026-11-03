# Codex Desktop та Claude Code

Використайте [agent-led setup](agent-setup.md), щоб налаштувати весь workflow. Встановлені templates є project-scoped; агент об’єднає їх зі збереженням сторонніх settings.


Спочатку встановіть add-on і перегляньте конфіг проєкту. Для автоматичного DDEV cleanup явно ввімкніть:

```yaml
cleanup:
  orphan_detection: true
  auto_delete: true
```

Звичайна сесія в main не створює додаткового середовища. Для fresh seed потрібні доступний Docker і source DDEV. Watcher не використовується.

## Codex Desktop

Створіть у Codex Local environment і задайте scripts:

**Setup**

```sh
bash /absolute/path/to/main/.ddev/worktree-kit/codex-setup.sh
```

**Cleanup**

```sh
bash /absolute/path/to/main/.ddev/worktree-kit/codex-cleanup.sh
```

Підставте шлях свого комп’ютера. Для спільного committed config у repository є переносимі recipes [setup](https://github.com/BODYA7979/ddev-worktree-kit/blob/main/examples/codex-setup.sh) і [cleanup](https://github.com/BODYA7979/ddev-worktree-kit/blob/main/examples/codex-cleanup.sh), які шукають fallback у main зі стандартним `.git` layout.

Виберіть це середовище для нової Worktree сесії. Codex створює Git checkout і передає абсолютний `CODEX_WORKTREE_PATH`; callbacks перевіряють repository та target навіть за cwd=main. Cleanup видаляє DDEV і його БД перед тим, як Codex прибере checkout. За `auto_delete: false` DDEV deletion пропускається.

Агент може створити `.codex/environments/environment.toml` зі встановленого version-1 template або об’єднати наявне середовище. Перевірений export має `[setup] script` та `[cleanup] script`; збережіть інші actions і platform overrides. Абсолютний callback path працює також на гілках, де add-on ще немає.

## Claude Code

Об’єднайте [template hooks](https://github.com/BODYA7979/ddev-worktree-kit/blob/main/examples/claude.settings.json) з `.claude/settings.json`, зберігаючи інші settings і hooks. Використовуйте тільки одного `WorktreeCreate` provider. Для локального налаштування потрібні три commands:

| Event | Command | Timeout |
|---|---|---|
| `WorktreeCreate` | `bash /absolute/path/to/main/.ddev/worktree-kit/claude-worktree-create.sh` | 600s |
| `WorktreeRemove` | `bash /absolute/path/to/main/.ddev/worktree-kit/claude-worktree-remove.sh` | 600s |
| `SessionStart`, matcher `startup|resume` | `bash /absolute/path/to/main/.ddev/worktree-kit/claude-session-start.sh` | 600s |

Після зміни hooks перезапустіть Claude. Створіть worktree штатним способом, наприклад `claude --worktree feature-name`.

`WorktreeCreate` підміняє вбудоване Git creation Claude. Наш adapter створює `<main>/.claude/worktrees/<name>` на `worktree-<name>`, ініціалізує DDEV і після успіху повертає тільки абсолютний path. Існуюча branch використовується без reset; чужий checkout за цим path відхиляється. На старих гілках adapter переносить лише власні hook handlers у local Claude settings.

`WorktreeRemove` спочатку прибирає власний DDEV, потім force-removes точний власний checkout. Це виконує рішення Claude відкинути його, тому незакомічені зміни checkout можуть бути втрачені. **Branches та shared source uploads зберігаються.** Nested Git checkout, locked/moved worktree, ownership mismatch і cleanup failure блокують видалення checkout. Якщо automatic DDEV deletion вимкнений, checkout видаляється, а DDEV залишається для ручного GC.

`SessionStart` дає idempotent setup/resume. `SessionEnd` не використовується: завершення сесії не означає видалення worktree. Custom `WorktreeCreate` не обробляє `.worktreeinclude` автоматично; потрібні local text settings задайте через `local_files`.

Контракти: [Claude WorktreeCreate](https://code.claude.com/docs/en/hooks#worktreecreate), [WorktreeRemove](https://code.claude.com/docs/en/hooks#worktreeremove), [Codex local environments](https://learn.chatgpt.com/docs/environments/local-environment).
