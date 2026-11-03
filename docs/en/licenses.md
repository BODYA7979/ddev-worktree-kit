# License and bundled software

The project runtime is MIT-licensed. [LICENSE](https://github.com/BODYA7979/ddev-worktree-kit/blob/main/LICENSE) and [third-party notices](https://github.com/BODYA7979/ddev-worktree-kit/blob/main/THIRD_PARTY_NOTICES.md) are included in the repository and release payload.

Pure-Python PyYAML 6.0.3 is bundled under MIT in `worktree-kit/_vendor/`. It needs no C extension or host package installation. Its original license is retained. Vendored files have a DDEV ownership marker and whitespace-only normalization; their Python AST was checked unchanged during vendoring. Source archive SHA-256:

```text
d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f
```

The config loader rejects unsafe object tags and duplicate keys and uses only `true`/`false` as boolean literals. Runtime imports do not write bytecode into installed payload directories.

Template-derived GitHub/editor/export scaffolding retains Apache 2.0 attribution and its license text. Zensical and other documentation dependencies are build tools, not vendored runtime dependencies. See [PyYAML documentation](https://pyyaml.org/wiki/PyYAMLDocumentation) for its parser API.
