# Конфігурація

Використовуйте `.ddev/worktree-kit.yaml`. Власний конфіг worktree має пріоритет; за його відсутності manager читає main checkout. Конфігурація залишається YAML; JSON output і registry у Git metadata є машинними протоколами.

## Повний типовий приклад

```yaml
version: 1

worktree:
  name: "{project}-wt-{slug}-{hash}"
  auto_start: true
  tld: ddev.site

database:
  source: primary
  strategy: snapshot
  snapshot: fresh
  create_if_missing: true
  refresh: manual

setup:
  composer_install: true
  composer_root: ''
  commands: []

local_files:
  - .ddev/config.local.yaml

files:
  strategy: none
  mappings: []

drupal:
  multisite:
    enabled: false
    sites: {}

cleanup:
  orphan_detection: true
  auto_delete: false
```

| Налаштування | Поведінка |
|---|---|
| `worktree.name` | Підтримує `{project}`, `{slug}`, `{hash}`; hash обов’язковий. Записане ім’я зберігається при повторному init. |
| `worktree.auto_start` | `false` готує файли й повертає `prepared`; `ddev wtk init --start` виконує seed/setup. |
| `database.source` | `primary` або абсолютний шлях іншого зареєстрованого checkout цього repo. |
| `database.snapshot` | `fresh` створює новий source snapshot; `latest` явно використовує останній сумісний. |
| `database.create_if_missing` | Дозволяє створити snapshot, якщо для `latest` немає сумісного backup. |
| `database.strategy`, `refresh` | Наразі `snapshot` і `manual`; автоматичної заміни БД немає. |
| `setup.composer_install` | Встановлює залежності після зміни manifests або за відсутнього vendor. |
| `setup.composer_root` | Composer directory відносно checkout; порожнє значення означає root repo. |
| `setup.commands` | Послідовні команди після DB verification та Composer; дивіться [setup-команди](setup-commands.md). |
| `local_files` | Копіює тільки відсутні текстові файли зі source; local settings проєкту додайте явно. |
| `files` | `none`, `shared`, `copy` з явними mappings тек. |
| `drupal.multisite` | Явний mapping site-directory → hostname/database. |
| `cleanup.orphan_detection` | Вмикає CLI GC. |
| `cleanup.auto_delete` | Дозволяє native callback видалити DDEV/DB свого worktree; типово false. |

Сімейство та версія source/target DB мають збігатися. Fresh seed потребує running source. Невдалий fresh snapshot не перемикається тихо на старий backup. Вибраний через `latest` backup зберігається; власні тимчасові snapshots manager прибирає лише після успішної перевірки seed.

Рекомендований section-based YAML. Legacy flat config і `worktree-kit.json` читаються для міграції формату; одночасно YAML та JSON не залишайте. Це не означає автоматичного усиновлення runtime state старого Worktree Env.
