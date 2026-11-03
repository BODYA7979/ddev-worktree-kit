# Розробка та перевірки

Клонуйте source repository. Користувачам runtime ці developer dependencies не потрібні.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
make check PYTHON=.venv/bin/python RUFF=.venv/bin/ruff
```

`make check` виконує Ruff, Python compilation, Bash syntax checks та process-level contracts зі справжнім Git і контрольованими DDEV/Docker doubles.

## Тести зі справжнім DDEV

Встановіть Bats core, bats-support та bats-assert, потім:

```sh
make test-addon
```

Suite перевіряє directory/archive install, Python preflight до копіювання, reinstall зі збереженням user config, marker-aware uninstall, аліас `wtk`, snapshot seed, repeat setup, Composer/bootstrap, shared/copy/sync, multisite HTTP та native callbacks. Fixtures мають унікальні імена й видаляють лише власні ресурси. Чужі проєкти не підбираються за префіксом.

Користувач також підтвердив native create/remove Claude на справжньому Drupal-проєкті. Codex callbacks перевірені зі збереженим local-environment config; end-to-end перевірки самих клієнтів ще слід розширювати. PHP multisite fixture перевіряє generated includes, без повного Drupal kernel test.

## Сайт документації

Основна мова — англійська; відповідні українські сторінки лежать у `docs/uk/`. Оновлюйте обидва варіанти разом.

```sh
python3 -m venv .venv-docs
.venv-docs/bin/python -m pip install -r requirements-docs.txt
make docs PYTHON=.venv-docs/bin/python
```

Зафіксований [Zensical](https://zensical.org/docs/) читає наш YAML config. Англійська збирається в корені сайту, українська — у `/uk/`, кожна зі своєю мовою пошуку/UI. Combined build перевіряє internal links, мовну повноту й URLs у project subpath. Docs dependencies потребують Python 3.11+ та відділені від Python 3.10+ runtime add-on.

Для локального preview у docs environment виконайте `python scripts/build_docs.py --site-url http://127.0.0.1:8000/`, потім `python -m http.server 8000 --directory site`.

## Release payload

`make package` створює single-root tarball add-on і SHA-256 у `dist/`, враховуючи `.gitattributes`. Перевіряється наявність усіх manifest files. Tests, workflows, build tooling, caches та локальні project evidence не потрапляють до архіву. Перевірений tag-to-release workflow описано в [публікації](publishing.md).
