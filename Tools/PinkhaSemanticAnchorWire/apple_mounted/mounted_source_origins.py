"""Bind the current mounted controller separately from its immutable compiled App."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

PROTOCOL = "pinkha-page154-separate-source-origins-v1"
CONSUMER_PATH = "Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py"


def require(value, message):
    if not value:
        raise ValueError(message)


def _root(path):
    require(isinstance(path, Path) and path.is_absolute()
            and path == path.resolve() and path.is_dir() and not path.is_symlink(),
            "An existing canonical physical source root is required")
    return path


def _map_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _loaded(controller, app, inputs):
    result = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        require(not path.is_relative_to(app),
                "Compiled App source checkout must not supply controller modules: " + name)
        if path.suffix == ".py" and path.is_relative_to(controller):
            relative = path.relative_to(controller).as_posix()
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            require(inputs.get(relative) == actual,
                    "Loaded controller module is not an exact current Git input: " + relative)
            result[name] = {"path": relative, "sha256": actual}
    return result


def capture(controller, app, controller_sha, app_sha, consumer):
    """Use the unchanged actual consumer reader for both complete Git checkouts."""
    controller = _root(controller)
    app = _root(app)
    require(controller != app and not controller.is_relative_to(app)
            and not app.is_relative_to(controller), "Controller and App roots must be disjoint")
    require(all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value)
                for value in (controller_sha, app_sha)), "Both exact source identities are required")
    require(Path(__file__).resolve() ==
            controller / "Tools/PinkhaSemanticAnchorWire/apple_mounted/mounted_source_origins.py",
            "Source-origin adapter must come from the current controller")
    require(Path(consumer.__file__).resolve() == controller / CONSUMER_PATH,
            "Actual consumer helper must come from the current controller")
    # This reader checks HEAD, clean tracked state, every Git blob/physical byte,
    # and each loaded local Python source. Neither origin is inferred from a ref.
    current_inputs = consumer.checkout_inputs(controller, controller_sha)
    app_inputs = consumer.checkout_inputs(app, app_sha)
    loaded = _loaded(controller, app, current_inputs)
    require(loaded, "Actual current controller modules must be present")
    return {
        "protocol": PROTOCOL,
        "controller_root": str(controller),
        "controller_sha": controller_sha,
        "app_root": str(app),
        "app_sha": app_sha,
        "controller_inputs": current_inputs,
        "app_inputs": app_inputs,
        "loaded_controller_modules": loaded,
    }


def verify_current(before, consumer):
    after = capture(Path(before["controller_root"]), Path(before["app_root"]),
                    before["controller_sha"], before["app_sha"], consumer)
    require(after["controller_inputs"] == before["controller_inputs"],
            "Current controller source changed after admission")
    require(after["app_inputs"] == before["app_inputs"],
            "Immutable compiled App source changed after admission")
    require(all(after["loaded_controller_modules"].get(name) == value
                for name, value in before["loaded_controller_modules"].items()),
            "An admitted current controller module changed origin")
    return after


def receipt(value):
    """A compact source receipt; no Products, runtime or acceptance claim."""
    return {
        "protocol": value["protocol"],
        "controller_root": value["controller_root"],
        "controller_sha": value["controller_sha"],
        "compiled_app_root": value["app_root"],
        "compiled_app_sha": value["app_sha"],
        "controller_input_count": len(value["controller_inputs"]),
        "compiled_app_input_count": len(value["app_inputs"]),
        "controller_input_map_sha256": _map_digest(value["controller_inputs"]),
        "compiled_app_input_map_sha256": _map_digest(value["app_inputs"]),
        "loaded_controller_modules": value["loaded_controller_modules"],
        "current_controller_is_compiled_app_source": value["controller_sha"] == value["app_sha"],
        "new_builds": 0,
        "source_binding_only": True,
        "product_acceptance": False,
    }
