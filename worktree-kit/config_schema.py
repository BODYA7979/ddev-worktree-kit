# fmt: off
#ddev-generated
# fmt: on
"""Normalize public YAML sections while accepting legacy flat configurations."""

import shlex


def section(document, name, allowed):
    value = document.get(name, {})
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError(f"Unknown keys or invalid mapping in {name}")
    return value


def normalize(document):
    if not isinstance(document, dict):
        raise ValueError("Configuration must be a mapping")
    nested = {"worktree", "database", "setup", "drupal", "cleanup"}
    if not set(document) & nested:
        return document
    if set(document) - (nested | {"version", "files", "local_files"}):
        raise ValueError("Do not mix section-based YAML and legacy flat configuration keys")
    worktree = section(document, "worktree", {"name", "auto_start", "tld"})
    database = section(
        document, "database", {"source", "strategy", "snapshot", "create_if_missing", "refresh"}
    )
    setup = section(document, "setup", {"composer_install", "composer_root", "commands"})
    drupal = section(document, "drupal", {"multisite"})
    cleanup = section(document, "cleanup", {"orphan_detection", "auto_delete"})
    if (
        database.get("strategy", "snapshot") != "snapshot"
        or database.get("refresh", "manual") != "manual"
    ):
        raise ValueError("Database strategy is snapshot and refresh is manual")
    if type(cleanup.get("auto_delete", False)) is not bool:
        raise ValueError("cleanup.auto_delete must be true or false")
    if type(cleanup.get("orphan_detection", True)) is not bool:
        raise ValueError("cleanup.orphan_detection must be true or false")
    install = setup.get("composer_install", True)
    if type(install) is not bool:
        raise ValueError("setup.composer_install must be true or false")
    commands = setup.get("commands", [])
    if not isinstance(commands, list):
        raise ValueError("setup.commands must be a list of commands or argv arrays")
    commands = [shlex.split(item) if isinstance(item, str) else item for item in commands]
    multisite = section(drupal, "multisite", {"enabled", "sites"})
    if type(multisite.get("enabled", False)) is not bool:
        raise ValueError("drupal.multisite.enabled must be true or false")
    sites = {}
    if multisite.get("enabled", False):
        configured = multisite.get("sites", {})
        if not isinstance(configured, dict):
            raise ValueError("drupal.multisite.sites must map site directories to host aliases")
        for directory, site in configured.items():
            if isinstance(site, str):
                alias, details = site, {}
            elif isinstance(site, dict) and not set(site) - {"hostname", "database"}:
                alias, details = site.get("hostname", directory), site
            else:
                raise ValueError(
                    "A multisite value must be a hostname string or hostname/database mapping"
                )
            if alias in sites:
                raise ValueError("Multisite aliases must be unique")
            sites[alias] = {"directory": directory}
            if "database" in details:
                sites[alias]["database"] = details["database"]
    result = {
        "version": document.get("version", 1),
        "source": "main" if database.get("source", "primary") == "primary" else database["source"],
        "name_template": worktree.get("name", "{project}-wt-{slug}-{hash}"),
        "auto_start": worktree.get("auto_start", True),
        "tld": worktree.get("tld", "ddev.site"),
        "snapshot": database.get("snapshot", "fresh"),
        "create_if_missing": database.get("create_if_missing", True),
        "composer": "auto" if install else "off",
        "composer_root": setup.get("composer_root", ""),
        "bootstrap": commands,
        "sites": sites,
        "files": document.get("files", {"strategy": "none", "mappings": []}),
        "orphan_detection": cleanup.get("orphan_detection", True),
        "auto_delete": cleanup.get("auto_delete", False),
    }
    if "local_files" in document:
        result["local_files"] = document["local_files"]
    return result
