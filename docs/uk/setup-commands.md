# Setup-команди проєкту

Команди виконуються послідовно після запуску DDEV, перевірки target DB та завершення Composer, перед `phase: ready`.

```yaml
setup:
  composer_install: true
  commands:
    - "ddev drush cr"
```

Для Drupal DB updates, config import і deploy hooks замініть cache-only команду на `ddev drush deploy -y`. Deploy уже перебудовує кеш: [контракт Drush deploy](https://www.drush.org/12.x/deploycommand/).

## Правила виконання

Рядки розбираються на аргументи без shell expansion. Можна використати argv array:

```yaml
setup:
  commands:
    - [ddev, drush, deploy, '-y']
    - [bash, .ddev/scripts/worktree-setup.sh]
```

Команда з початковим `ddev` виконується на хості в target checkout. Інші команди запускаються в його контейнері через `ddev exec --raw --`. Для `&&`, pipes або розгортання змінних винесіть логіку в явний shell-скрипт. Користувацькі scripts належать проєкту; їх треба закомітити або надати через локальний setup.

## Повтори та помилки

Успішні команди отримують checkpoints. Повторний init без зміни конфігурації та Composer manifests пропускає завершений bootstrap. Зміна конфігурації/manifests або необхідне повторне встановлення Composer може знову запустити bootstrap під час наступного init. Помилка зупиняє setup; retry продовжує з незавершеної команди.

Команди повинні бути ідемпотентними: збій після їх виконання, але до збереження receipt, може повторити команду. Це setup-фаза, без гарантії exactly-once. Окремі user hooks `after_start` / `before_remove` не реалізовані. Manager пропускає звичайні DDEV hooks під час snapshot/start; потрібну ініціалізацію задавайте тут.
