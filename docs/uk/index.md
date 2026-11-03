# DDEV Worktree Kit

Окреме DDEV-середовище для кожного worktree AI-агента: власний URL, незалежна БД зі snapshot основного checkout, залежності та setup-команди проєкту.

**`ddev wtk`** — короткий аліас **`ddev worktree-kit`**.

- **Codex Desktop:** Codex створює Git checkout; setup і cleanup локального середовища керують DDEV.
- **Claude Code:** пара `WorktreeCreate` / `WorktreeRemove` створює та прибирає checkout разом із його DDEV. Git-гілки зберігаються.
- **Ручний Git:** для вже створеного linked worktree використайте `ddev wtk init`.

Uploads типово мають стратегію `none`. Для кожної теки можна явно вибрати shared Docker bind або незалежну копію. Фоновий watcher не встановлюється.

[Встановіть через агента](agent-setup.md), перевірте [вимоги до хоста](requirements.md) і підключіть [Codex або Claude](integrations.md).

## Межі

Kit поєднує DDEV, Git worktrees і native lifecycle агентів в один workflow. Внутрішні manager/adapters розподіляють відповідальність за середовище та checkout. Init не скидає наявну БД. Видалення перевіряє записане володіння; звичайний gc показує preview до явного apply.

Це community add-on. Поява в registry та офіційна підтримка DDEV — окремі кроки; дивіться [публікацію](publishing.md).
