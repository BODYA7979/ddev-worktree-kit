# Встановлення через свого агента

Основний шлях — agent-led setup: DDEV + worktrees + agents налаштовуються разом.

Вставте цей промпт у Codex або Claude Code з repository проєкту:

```text
Налаштуй тут DDEV Worktree Kit для Codex Desktop та Claude Code.
Прочитай і виконай цей runbook:
https://raw.githubusercontent.com/BODYA7979/ddev-worktree-kit/main/AGENT_SETUP.md

Встанови add-on, об’єднай project/client settings та інструкції агентам.
Увімкни автоматичні setup і cleanup агентських worktrees.
Збережи дані, сторонні settings і наявну стратегію файлів;
інакше залиш uploads без синхронізації.
Перевір setup і назви змінені файли. Не скидай/пересівай БД та не створюй/
видаляй worktree без мого прямого запиту на такий тест.
```

Якщо користуєтеся одним клієнтом, залиште у промпті лише його. Агент сам встановить add-on, прочитає встановлені boilerplates і відредагує project-scoped configs. Для GitHub install потрібний перший release; до публікації явно дайте агенту локальний source checkout.

[Runbook для агента](https://github.com/BODYA7979/ddev-worktree-kit/blob/main/AGENT_SETUP.md) містить точні команди, defaults, правила merge, verification і роботу з конфліктами. Installed templates включають YAML, Claude hooks, Codex environment TOML та fragment інструкцій AGENTS/CLAUDE.

Агент зберігає сторонні hooks, actions і конфігурацію проєкту. Якщо інший інструмент володіє WorktreeCreate, потрібне конкретне рішення інтеграції; конфіг не перезаписується тихо. Після setup ручний init для звичайної роботи не потрібний.

Після налаштування перезавантажте Claude hooks та за потреби виберіть готовий local environment для нової Worktree сесії Codex. [Ручний довідник](quickstart.md) корисний для діагностики й контрольованої перевірки, [деталі інтеграції](integrations.md) — для native lifecycle contract.
