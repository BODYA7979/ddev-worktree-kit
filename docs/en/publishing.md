# Publishing to GitHub and the DDEV registry

Repository: [BODYA7979/ddev-worktree-kit](https://github.com/BODYA7979/ddev-worktree-kit). Intended documentation URL: [GitHub Pages](https://bodya7979.github.io/ddev-worktree-kit/).

These are configured destinations; a local successful build does not mean the repository, release or site has been published.

## First publication

1. Review the source, MIT license and third-party notices; push the reviewed branch to the repository. Use `main` as the default branch.
2. Allow GitHub Actions and enable **Settings → Pages → Build and deployment → Source: GitHub Actions**. The docs workflow publishes English and Ukrainian from `main`; pull requests only build/check artifacts. After enabling Pages, run the Documentation workflow once with `workflow_dispatch` if the initial push happened before Pages was enabled.
3. Run the repository CI on Linux AMD64/ARM64 with minimum/latest stable DDEV. Inspect those results before tagging.
4. Review `CHANGELOG.md`, keep its version aligned with the runtime, and run `make check`, `make test-addon`, `make docs` and `make package` locally.
5. Create and push a matching semantic version tag, for example `v0.5.1`. The release workflow validates the tag/version/changelog, runs contracts and docs checks, builds the package, and runs real DDEV tests before publishing GitHub Release assets.
6. Verify the release install with `GITHUB_REPO=BODYA7979/ddev-worktree-kit ADDON_RELEASE_VERSION=v0.5.1 bats tests/test.bats --filter-tags release`.

The release workflow uses the built artifact after its validation jobs pass. It does not silently overwrite an existing release. Bump the version and create a new tag for changed payloads.

## Appear in the DDEV add-on registry

Make the repository public, give it a clear description and add the GitHub topic **`ddev-get`** when ready to maintain it. Publish a proper release. DDEV discovers repositories through that topic; no copy into DDEV's main source repository is required. Registry indexing is asynchronous, so verify the listing after it refreshes.

Suggested description: “Isolated DDEV environments for Codex and Claude Code Git worktrees, with database snapshots, Drupal multisite and safe cleanup.” Useful topics include `ddev`, `ddev-get`, `git-worktree`, `drupal`, `codex` and `claude-code`.

Then users can install:

```sh
ddev add-on get BODYA7979/ddev-worktree-kit
```

## Official DDEV maintenance is a separate step

Registry inclusion does not confer official DDEV support. To request official status, open an issue in [ddev/ddev](https://github.com/ddev/ddev/issues), describe the add-on and tested compatibility, and commit to maintaining it and responding to issues. Any transfer to the DDEV organization is coordinated with its maintainers; it is not automatic.

Sources: [DDEV publishing requirements](https://docs.ddev.com/en/stable/users/extend/creating-add-ons/#publishing-your-add-on), [making it official](https://docs.ddev.com/en/stable/users/extend/creating-add-ons/#making-it-official), [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Workflow permissions

Normal checks use read-only repository access. Pages deployment receives only Pages/OIDC write permissions in its deployment job and uses the `github-pages` environment. Release publishing receives `contents: write` only after validation and integration jobs succeed. Pull-request workflows do not publish releases or deploy the site.

Run `ddev utility addon-update-checker` periodically. Its Apache-license suggestion reflects the template's choice; this add-on's runtime remains MIT, with template-derived Apache scaffolding credited separately.
