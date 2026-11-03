# Drupal: host → site directory → database

Snapshot переносить всі бази source DB server. Host mapping і Drupal settings
потрібно налаштувати один раз у Git, щоб кожен worktree міг використати локальні
generated overrides без редагування tracked PHP на кожному init.

## 1. Одноразові include у проєкті

У `<docroot>/sites/sites.php` додайте **після** основного mapping:

```php
$worktree_sites = __DIR__ . '/sites.worktree-kit.php';
if (is_file($worktree_sites)) {
  require $worktree_sites;
}
```

У `settings.php` **кожного налаштованого site** додайте останнім, після
`settings.ddev.php`, local settings і trusted hosts:

```php
$worktree_settings = DRUPAL_ROOT . '/sites/settings.worktree-kit.php';
if (is_file($worktree_settings)) {
  require $worktree_settings;
}
```

Закомітьте include. Main не має generated-файлів, тому його mapping не зміниться.
Менеджер не дописує код у ваші tracked sites.php/settings.php. Він перевіряє
наявність імен include як preflight, але правильне місце/виконання include
потрібно перевірити в проєкті.

## 2. Явна конфігурація

У `.ddev/worktree-kit.yaml`:

```yaml
version: 1
drupal:
  multisite:
    enabled: true
    sites:
      english:
        hostname: en
        database: site_en
      french:
        hostname: fr
        database: site_fr
local_files:
  - .ddev/config.local.yaml
  - web/sites/english/settings.local.php
  - web/sites/french/settings.local.php
```

`web/` у `local_files` замініть на свій docroot. DB імена повинні існувати у
source snapshot і мати application tables; init це перевіряє. Якщо database не
задана, generated settings зберігає DB-name попередніх settings.

| Alias | URL worktree | Site directory | Database |
|---|---|---|---|
| `en` | `https://en.<unique-name>.ddev.site` | `sites/english` | `site_en` |
| `fr` | `https://fr.<unique-name>.ddev.site` | `sites/french` | `site_fr` |

Для default host використайте `default: ""`. Короткий формат без окремого
DB-name: `shop: shop`, `portal: portal`; ключ — site directory, значення — alias.
Розгорнутий формат вище додає явне DB-name. Кожен alias має бути унікальним.

Generated settings задає точні anchored trusted-host patterns і, коли вказано,
DB-name для `$site_path`. Решта connection settings має надходити з DDEV/ваших
local settings. Значення db-host має бути внутрішнє `db`, а не адреса source.
Окремі Drupal sites/settings.ddev.php все одно повинні підключатися коректно.

Source повинен уже мати працездатні DB credentials і grants для кожного site.
`CREATE DATABASE` через root сам по собі не дає DDEV user `db` доступу до
додаткової БД. Snapshot переносить source DB; менеджер не створює нових grants
і не переписує облікові дані. Перевірте це до init.
Джерело: [DDEV additional databases](https://docs.ddev.com/en/stable/users/usage/database-management/#additional-databases).

Перевірте кожен URL та `drush --uri=<worktree-site-url> status`. Окремий site
bootstrap задайте скриптом, який читає `DDEV_SITENAME`/`DDEV_PRIMARY_URL`; конфіг
не виконує shell expansion і не вигадує URI за вас.

## Файли

Типово uploads мають strategy `none`, а наявний Stage File Proxy залишається
відповідальністю проєкту. Якщо його настройки знаходяться в gitignored
settings.local.php, додайте цей текстовий файл до `local_files`.

Для кожного site можна явно вибрати `shared` (Docker bind) або незалежний `copy`
і пізніше запустити ручний source → worktree sync. [Файлові стратегії](files.md).

## Що тестується

Contract тести перевіряють генерацію mapping/DB settings і preflight includes.
Live smoke запускає справжній DDEV, snapshot двох БД, два hostname aliases і
виконує generated PHP includes у невеликому routing harness. Це перевірка
generated PHP та DDEV routing; повна Drupal kernel/Drush QA в конкретному
проєкті залишається adoption-перевіркою.
