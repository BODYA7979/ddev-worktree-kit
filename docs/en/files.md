# Uploads and file strategies

Paths are relative to the Git checkout and use the same location in source and target. Each directory can choose its own strategy:

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

## none

The default copies or mounts no uploads. Keep Stage File Proxy or another project-managed source of files. No source upload directory is required.

## shared

An explicit Docker bind exposes the source directory at `/var/www/html/<path>` in the worktree web container. Writes there change source uploads. Set `read_only: true` if appropriate; Drupal image derivatives or caches may require write access.

The host target directory remains its own directory. This is not a host symlink: the container sees the bind mount, while an IDE sees the target host files. Existing target host files are retained but hidden under the container mount. Cleanup preserves the shared source directory.

## copy

The first initialization copies missing files into an independent target directory, preserving files already present. A completion receipt prevents repeat init from silently resynchronizing that copy. Changes in target do not affect source. Hidden files are included; symlinks and special files are rejected. Large uploads require additional disk space and time.

## Manual synchronization

```sh
ddev wtk files sync
ddev wtk files sync --apply
```

Preview reports changed/new files. Apply copies source content to `copy` mappings, replacing changed target files and preserving extra target files. It never deletes source files and skips `none`/`shared` mappings.

Source ownership is rechecked before copying. Paths outside a checkout, symlinks and overlapping source/target or mapping directories are refused. Transfers use temporary files and atomic replacement; errors can be retried. Continuous or two-way synchronization is not implemented.
