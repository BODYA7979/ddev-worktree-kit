# Ручний довідник setup

Основне встановлення через агента описано в [цьому розділі](agent-setup.md). Тут наведено команди та файли, які готує агент.

## Встановлення в основному checkout

Після першого опублікованого GitHub release:

```sh
ddev add-on get BODYA7979/ddev-worktree-kit
```

Під час підготовки або розробки релізу встановлюйте з локальної копії:

```sh
ddev add-on get /absolute/path/to/ddev-worktree-kit
cp /absolute/path/to/ddev-worktree-kit/examples/worktree-kit.yaml .ddev/worktree-kit.yaml
```

Приклад має обережні defaults: uploads не синхронізуються, Drupal-команд немає, автоматичне видалення вимкнене. Перегляньте [довідник конфігурації](configuration.md). Install перевіряє Python перед копіюванням файлів; нові середовища не стартують і AI інтеграція сама не підключається.

Закомітьте runtime `.ddev/worktree-kit/`, команду `.ddev/commands/host/worktree-kit`, конфіг `.ddev/worktree-kit.yaml` та базовий `.ddev/config.yaml`. Перевірте ignore rules проєкту перед додаванням цих точних шляхів.

## Запуск worktree

Запустіть основний DDEV і Docker, створіть linked Git worktree та виконайте в ньому:

```sh
ddev wtk init
ddev wtk status
```

Для гілки, яка ще не має add-on, використайте встановлення з main:

```sh
python3 /absolute/path/to/main/.ddev/worktree-kit/manager.py --path /absolute/path/to/worktree init
```

Успішний setup повертає `phase: ready`, унікальне DDEV-ім’я та URL. Повторний init зберігає БД і receipts завершених setup-кроків.

## Одноразова автоматизація проєкту

Виконайте [налаштування AI інтеграції](integrations.md). У Codex треба вибрати local environment, у Claude — підключити native hooks. Звичайний `ddev restart` не створює worktree-середовище. Після створення нового worktree AI-клієнт викликає зареєстрований setup callback.
