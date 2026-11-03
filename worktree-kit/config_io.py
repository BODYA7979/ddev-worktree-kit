# fmt: off
#ddev-generated
# fmt: on
"""Safe YAML IO using the parser shipped with the add-on."""

import importlib
import re
import sys

sys.dont_write_bytecode = True
yaml = importlib.import_module("_vendor.yaml")


class ConfigLoader(yaml.SafeLoader):
    yaml_implicit_resolvers = {
        key: [(tag, regex) for tag, regex in entries if tag != "tag:yaml.org,2002:bool"]
        for key, entries in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key, _ in node.value:
            if key.tag == "tag:yaml.org,2002:merge":
                continue
            if key.value in seen:
                raise ValueError(
                    f"Duplicate YAML key {key.value!r} at line {key.start_mark.line + 1}"
                )
            seen.add(key.value)
        return super().construct_mapping(node, deep=deep)


ConfigLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.IGNORECASE), list("tTfF")
)


def load_yaml(text):
    try:
        return yaml.load(text, Loader=ConfigLoader)
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid YAML: {error}") from error


def dump_yaml(value):
    return yaml.safe_dump(value, sort_keys=False, default_flow_style=False, allow_unicode=True)
