# Ліцензія та включене ПЗ

Runtime проєкту має MIT license. [LICENSE](https://github.com/BODYA7979/ddev-worktree-kit/blob/main/LICENSE) та [third-party notices](https://github.com/BODYA7979/ddev-worktree-kit/blob/main/THIRD_PARTY_NOTICES.md) включено до repository і release payload.

Pure-Python PyYAML 6.0.3 постачається за MIT у `worktree-kit/_vendor/`. C extension або host package install не потрібні. Оригінальну ліцензію збережено. Vendored files отримали DDEV ownership marker і лише whitespace normalization; під час vendoring перевірено незмінність Python AST. SHA-256 source archive:

```text
d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f
```

Config loader відхиляє unsafe object tags і duplicate keys та використовує тільки `true`/`false` як boolean literals. Runtime imports не пишуть bytecode у встановлені payload directories.

Scaffolding GitHub/editor/export із template зберігає Apache 2.0 attribution і текст license. Zensical та інші docs dependencies є build tools, без vendoring у runtime. Parser API описано в [PyYAML documentation](https://pyyaml.org/wiki/PyYAMLDocumentation).
