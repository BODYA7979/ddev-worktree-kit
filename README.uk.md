# DDEV Worktree Kit

**Окремі DDEV-середовища для Git worktrees Codex і Claude Code.** Власні URLs, незалежні БД зі snapshot основного checkout, Composer/setup-команди, Drupal multisite та безпечне очищення.

[English](README.md) · [Українська документація](docs/uk/index.md) · [Сайт документації](https://bodya7979.github.io/ddev-worktree-kit/uk/)

## Вимоги

macOS/Linux, **Python 3.10+**, **Git 2.36+**, **DDEV 1.25.4+ stable** і running local Docker provider із доступним `docker` CLI. Підтримуються MySQL/MariaDB. PHP, Composer та Drush на хості не потрібні; YAML parser уже в пакеті. Native Windows не підтримується, WSL2 end-to-end ще не перевірено. [Повні вимоги](docs/uk/requirements.md).

## Встановлення

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


Деталі: [agent-led setup](docs/uk/agent-setup.md).

### Довідник команд

Після першого опублікованого release:

```sh
ddev add-on get BODYA7979/ddev-worktree-kit
```

Для локальної розробки до публікації:

```sh
ddev add-on get /absolute/path/to/ddev-worktree-kit
cp /absolute/path/to/ddev-worktree-kit/examples/worktree-kit.yaml .ddev/worktree-kit.yaml
```

Перегляньте й закомітьте `.ddev/worktree-kit/`, `.ddev/commands/host/worktree-kit`, `.ddev/worktree-kit.yaml` та `.ddev/config.yaml`. Конфігурація проєкту — YAML. Native інтеграція агентів є частиною встановлення: [Codex/Claude setup](docs/uk/integrations.md).

## Використання

`wtk` — штатний DDEV alias для `worktree-kit`:

```sh
ddev wtk init
ddev wtk status
ddev wtk files sync          # preview
ddev wtk files sync --apply  # source → copy; зайві target files зберігаються
ddev wtk teardown            # preview DDEV removal; Git зберігається
ddev wtk gc                  # preview orphan environments
```

Codex володіє створенням/видаленням Git і викликає setup/cleanup callbacks. Claude використовує пару native `WorktreeCreate` / `WorktreeRemove`, яка володіє власним checkout та DDEV lifecycle; branches зберігаються. Watcher не потрібний.

```yaml
setup:
  composer_install: true
  commands:
    - "ddev drush cr"
files:
  strategy: none
  mappings: []
cleanup:
  orphan_detection: true
  auto_delete: false
```

Для повного Drupal setup виберіть `ddev drush deploy -y`. Uploads типово `none`; доступні явні `shared` і `copy` mappings. Automatic DDEV/DB cleanup вимагає `cleanup.auto_delete: true`. Init не скидає наявну БД. [Конфігурація](docs/uk/configuration.md) · [Setup-команди](docs/uk/setup-commands.md) · [Файли](docs/uk/files.md) · [Очищення](docs/uk/cleanup.md).

## Розробка та публікація

```sh
make check      # Ruff, syntax, real-Git contracts
make test-addon # Bats зі справжніми disposable DDEV fixtures
make docs       # англійський та український сайт; потрібні docs dependencies
make package    # tarball add-on і SHA-256 у dist/
```

[Розробка](docs/uk/development.md) описує окремі test/docs environments. [Публікація](docs/uk/publishing.md) пояснює GitHub Pages, tag-to-release automation, `ddev-get` registry та окремий запит офіційної підтримки DDEV. Workflows почнуть працювати після push; badges і сайт стануть доступні після публікації.

Runtime: [MIT](LICENSE). Template scaffolding та bundled software: [third-party notices](THIRD_PARTY_NOTICES.md).
