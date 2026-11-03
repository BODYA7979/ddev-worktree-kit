# Drupal and multisite

Snapshot seeding copies the source database server's databases. Drupal hostname/site-directory selection needs one-time project includes; the manager does not append code to tracked PHP settings automatically.

## Include generated mapping

After existing mappings in `<docroot>/sites/sites.php`, add and commit:

```php
$worktree_sites = __DIR__ . '/sites.worktree-kit.php';
if (is_file($worktree_sites)) {
  require $worktree_sites;
}
```

At the end of each configured site's `settings.php`, after DDEV/local settings and trusted hosts, add:

```php
$worktree_settings = DRUPAL_ROOT . '/sites/settings.worktree-kit.php';
if (is_file($worktree_settings)) {
  require $worktree_settings;
}
```

The main checkout has no generated includes. Init checks that include names are present, but correct PHP execution/order still needs project verification.

## Configure sites

```yaml
drupal:
  multisite:
    enabled: true
    sites:
      default: ''
      shop:
        hostname: shop
        database: shop_db
      portal:
        hostname: portal
        database: portal_db
local_files:
  - .ddev/config.local.yaml
  - docroot/sites/default/settings.local.php
  - docroot/sites/shop/settings.local.php
  - docroot/sites/portal/settings.local.php
```

Keys are site directories. Hostname aliases become `shop.<unique-name>.ddev.site` and `portal.<unique-name>.ddev.site`; an empty alias uses the default host. The short form `shop: shop` keeps the existing DB name from preceding settings. Explicit databases must already exist in source and contain application tables.

Generated settings select the site's database and exact trusted-host patterns. Other credentials must come from valid DDEV/local settings, using the internal `db` host. Source credentials and grants must already work for every database; the manager does not create grants. See [DDEV additional databases](https://docs.ddev.com/en/stable/users/usage/database-management/#additional-databases).

Validate each URL and `ddev drush --uri=<worktree-site-url> status`. For multisite deployment, run explicit per-site commands or a script that computes URIs; the manager does not invent site URIs or perform shell-variable expansion.

Uploads remain separate per-site mappings; see [files](files.md). The live suite verifies executable PHP includes and two DBs in a routing harness; full project-specific Drupal bootstrap needs adoption testing.
