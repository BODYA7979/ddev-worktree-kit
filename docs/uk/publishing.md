# Публікація на GitHub та в DDEV registry

Repository: [BODYA7979/ddev-worktree-kit](https://github.com/BODYA7979/ddev-worktree-kit). Запланована адреса docs: [GitHub Pages](https://bodya7979.github.io/ddev-worktree-kit/).

Це налаштовані адреси; успішний локальний build не означає публікацію repository, release або сайту.

## Перша публікація

1. Перегляньте source, MIT license та third-party notices; запуште перевірену гілку. Default branch — `main`.
2. Дозвольте GitHub Actions та ввімкніть **Settings → Pages → Build and deployment → Source: GitHub Actions**. Docs workflow публікує англійську й українську з `main`; PR лише збирають і перевіряють artifacts. Після ввімкнення Pages один раз запустіть Documentation workflow через `workflow_dispatch`, якщо перший push відбувся раніше.
3. Запустіть CI на Linux AMD64/ARM64 з minimum/latest stable DDEV. Перевірте результати перед tag.
4. Перегляньте `CHANGELOG.md`, узгодьте версію з runtime та локально виконайте `make check`, `make test-addon`, `make docs`, `make package`.
5. Створіть і запуште відповідний semantic tag, наприклад `v0.5.1`. Release workflow звірить tag/version/changelog, виконає contracts/docs checks, збере пакет і перевірить реальний DDEV перед публікацією GitHub Release assets.
6. Перевірте release install: `GITHUB_REPO=BODYA7979/ddev-worktree-kit ADDON_RELEASE_VERSION=v0.5.1 bats tests/test.bats --filter-tags release`.

Workflow публікує перевірений artifact після успіху validation jobs. Існуючий release не перезаписується тихо. Для зміненого payload підвищуйте версію та створюйте новий tag.

## Поява в DDEV add-on registry

Зробіть repository публічним, додайте зрозумілий description і topic **`ddev-get`**, коли готові підтримувати пакет. Опублікуйте належний release. DDEV знаходить repositories через цей topic; копіювати add-on у головний source repository DDEV не потрібно. Індексація асинхронна, тож перевірте listing після оновлення registry.

Запропонований description: “Isolated DDEV environments for Codex and Claude Code Git worktrees, with database snapshots, Drupal multisite and safe cleanup.” Topics: `ddev`, `ddev-get`, `git-worktree`, `drupal`, `codex`, `claude-code`.

Після цього користувачі встановлюють:

```sh
ddev add-on get BODYA7979/ddev-worktree-kit
```

## Офіційна підтримка DDEV — окремий крок

Registry listing не надає офіційної підтримки DDEV. Для official status відкрийте issue у [ddev/ddev](https://github.com/ddev/ddev/issues), опишіть add-on і перевірену сумісність та візьміть зобов’язання підтримувати його й реагувати на issues. Перенесення в організацію DDEV узгоджується з maintainers; автоматично це не відбувається.

Джерела: [DDEV publishing requirements](https://docs.ddev.com/en/stable/users/extend/creating-add-ons/#publishing-your-add-on), [making it official](https://docs.ddev.com/en/stable/users/extend/creating-add-ons/#making-it-official), [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Права workflow

Звичайні checks мають read-only доступ. Pages deployment отримує лише Pages/OIDC write permissions у deploy job та використовує environment `github-pages`. Release publishing отримує `contents: write` тільки після успішних validation/integration jobs. Pull requests не публікують releases і не deploy-ять сайт.

Періодично запускайте `ddev utility addon-update-checker`. Його Apache-рекомендація відображає вибір template; runtime цього add-on залишається MIT, а Apache scaffolding має окремі notices.
