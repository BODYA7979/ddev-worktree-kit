# Uploads: none, shared, copy та ручний sync

Стратегія задається глобально та перевизначається для кожного site:

```yaml
files:
  strategy: none
  mappings:
    - path: docroot/sites/default/files
      strategy: none
    - path: docroot/sites/shop/files
      strategy: copy
    - path: docroot/sites/portal/files
      strategy: shared
      read_only: false
```

Шляхи — відносно Git checkout і однакові в source/target. Непідтримані стратегії,
symlink paths, перетини mappings, source/target directories та шляхи поза checkout
відхиляються. Активні shared/copy mappings потребують наявної source directory.

## none

Менеджер не копіює та не монтує uploads. Використовуйте Stage File Proxy або
наповнюйте локальні файли самостійно. Значення типове і не потребує source files.

## shared

Docker bind mount підключає source directory у web container worktree за тим
самим шляхом `/var/www/html/<mapping.path>`. Це дає Drupal спільний набір файлів
без абсолютного host symlink, який може бути недоступний у контейнері.

Записи через Drupal/worktree-контейнер змінюють source uploads. Для читання
без запису задайте `read_only: true`. Такий режим може не підходити site,
якому потрібно створювати derivatives або cache-файли в цій теці.

На host каталог target залишається локальною текою; shared-вміст доступний
контейнеру через bind. Тому IDE/host filesystem не показує його як host symlink.
Наявні target host files не видаляються, але контейнер бачить bind source.

Gc видаляє контейнер/його volume; source uploads directory залишається на місці.
Для завершення shared-режиму змініть strategy і повторіть init зі start. При
`auto_start: false` зміни позначаються prepared/pending_start до запуску.

## copy

Перший init копіює відсутні файли в незалежну target directory. Наявні target
файли зберігаються. Receipt фіксує завершення; повторний init не оновлює copy
автоматично. Зміни target не впливають на source.

Копіюється вміст каталогу, включно з `.htaccess`/`.gitignore`; symlinks усередині
копії та special files відхиляються. Read/permission errors повертають помилку.
Великі uploads можуть зайняти значний час і місце — `shared` і `none` обходяться
без незалежної повної копії.

## Ручний source → worktree sync

```sh
ddev wtk files sync
ddev wtk files sync --apply
```

Без `--apply` команда показує кількість змінених/нових файлів та приклади шляхів.
З `--apply` вони оновлюються з source, включно зі зміненими target файлами.
Додаткові target файли не видаляються. Source не змінюється. Працює тільки для
`copy` mappings і тільки в managed linked worktree. Shared/none пропускаються.

Перед копіюванням повторно перевіряється, що source досі є checkout цього ж
репозиторію. Source/target uploads не можуть містити один одного. Для заміни
файлів використовуються тимчасовий файл і atomic replace; команда може бути
повторена після збою.

Для Drupal multisite кожна тека files налаштовується окремо, незалежно від
hostname/site mapping у `drupal.multisite`.
