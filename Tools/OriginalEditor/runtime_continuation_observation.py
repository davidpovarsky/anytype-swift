"""Bounded observations and owned cleanup for the retained-framework consumer.

This module neither repairs the host nor qualifies a framework. App retention is
explicitly unqualified; the original runner still owns all runtime acceptance.
"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import stat
import time
import uuid
import zipfile

from product_inventory import inventory
from runtime_continuation_process import Commands, digest, write_json

ENVIRONMENT_KEYS = ('PATH', 'HOME', 'TMPDIR', 'LANG', 'LC_ALL', 'DEVELOPER_DIR',
                    'USER', 'LOGNAME', 'SHELL', '__CF_USER_TEXT_ENCODING')
DIAGNOSTIC_STAGES = {'before-boot', 'after-boot', 'after-runtime-failure', 'before-cleanup', 'after-cleanup'}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def runtime_environment(environment):
    selected = {key: environment[key] for key in ENVIRONMENT_KEYS if key in environment}
    require(all(isinstance(value, str) and '\0' not in value and len(value) <= 16384
                for value in selected.values()), 'Malformed ordinary runtime environment')
    return selected


def validate_ownership(owned, expected_name, device, runtime, original_device_ids):
    require(isinstance(owned, dict) and owned.get('name') == expected_name
            and owned.get('device') == device and owned.get('runtime') == runtime,
            'Owned simulator provenance differs')
    identifier = owned.get('udid')
    require(isinstance(identifier, str) and str(uuid.UUID(identifier)).upper() == identifier.upper()
            and identifier.upper() not in {value.upper() for value in original_device_ids},
            'Simulator is not the newly created owned identity')
    return identifier


def diagnostic_catalog(root):
    """Read-only commands; ps deliberately excludes command-line arguments."""
    return [
        ('host-resources', ['sysctl', '-n', 'hw.memsize', 'hw.logicalcpu', 'vm.swapusage']),
        ('host-memory', ['vm_stat']),
        ('owned-filesystem-space', ['df', '-k', str(root)]),
        ('process-identities', ['ps', '-axo', 'pid=,ppid=,pgid=,comm=']),
        ('devices-observed', ['xcrun', 'simctl', 'list', 'devices', '-j']),
    ]


def observe_runtime(evidence, stage, root, environment, deadline_unix, owned,
                    commands_factory=Commands):
    require(stage in DIAGNOSTIC_STAGES, 'Unexpected diagnostic stage')
    require(runtime_environment(environment) == environment, 'Unapproved diagnostic environment')
    destination = Path(evidence) / 'diagnostics' / stage
    destination.mkdir(parents=True, exist_ok=False)
    # The whole snapshot gets at most 35 seconds of requested work, each child
    # at most 8. Actual overrun and owned group drain remain in the command log.
    deadline = min(deadline_unix, time.time() + 35)
    commands = commands_factory(destination, environment, deadline)
    result = {'stage': stage, 'scope': 'READ_ONLY_HOST_AND_OWNED_SIMULATOR_OBSERVATION',
              'requested_snapshot_budget_seconds': 35, 'requested_child_budget_seconds': 8,
              'owned_udid': owned.get('udid') if owned else None,
              'environment': dict(environment), 'commands': [], 'owned_device_state': 'NOT_OBSERVED',
              'device_plist': 'NOT_OBSERVED'}
    for label, argv in diagnostic_catalog(root):
        if not commands.owned_groups_drained or time.time() >= deadline:
            result['remaining_commands_not_started'] = True
            break
        try:
            code, output, error = commands.run(label, argv, root, 8)
            result['commands'].append({'label': label, 'effective_returncode': code})
            if label == 'devices-observed' and code == 0:
                require(output.stat().st_size <= 8 * 1024 * 1024, 'Oversized simulator diagnostic')
                devices = json.loads(output.read_bytes())['devices']
                require(isinstance(devices, dict) and all(isinstance(rows, list) for rows in devices.values()),
                        'Malformed simulator observation')
                if owned:
                    matching = [row for rows in devices.values() for row in rows
                                if isinstance(row, dict) and row.get('udid') == owned['udid']]
                    require(len(matching) <= 1, 'Ambiguous owned simulator observation')
                    result['owned_device_state'] = matching[0] if matching else 'ABSENT_IN_THIS_OBSERVATION'
        except BaseException as error:
            result['commands'].append({'label': label, 'error_type': type(error).__name__, 'error': str(error)})
            if not isinstance(error, Exception):
                result['interrupted'] = True
                break
    # This is an independent read of the exact owned device's persisted record,
    # useful when the CoreSimulator service cannot answer its list request.
    if owned and 'HOME' in environment and not result.get('interrupted'):
        try:
            identifier = owned['udid']
            require(str(uuid.UUID(identifier)).upper() == identifier.upper(), 'Invalid diagnostic owned identity')
            parent = Path(environment['HOME']) / 'Library/Developer/CoreSimulator/Devices'
            path = parent / identifier / 'device.plist'
            if not path.exists():
                result['device_plist'] = 'ABSENT_AT_EXACT_OWNED_PATH'
            else:
                require(not path.is_symlink() and path.resolve().is_relative_to(parent.resolve())
                        and path.is_file() and path.stat().st_size <= 2 * 1024 * 1024,
                        'Unexpected owned simulator plist')
                raw = path.read_bytes()
                value = plistlib.loads(raw)
                require(value.get('UDID', identifier).upper() == identifier.upper(), 'Owned device plist identity differs')
                (destination / 'owned-device.plist').write_bytes(raw)
                result['device_plist'] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                    'represented_fields': {key: value[key] for key in ['UDID', 'name', 'state', 'deviceType', 'runtime'] if key in value}}
        except BaseException as error:
            result['device_plist'] = {'error_type': type(error).__name__, 'error': str(error)}
            if not isinstance(error, Exception):
                result['interrupted'] = True
    result['owned_groups_drained'] = commands.owned_groups_drained
    write_json(destination / 'OBSERVATION.json', result)
    return result


def retain_signed_consumer(app, expected_inventory, signature, destination, producer, framework_producer,
                           source_sha256, source_inventory_sha256, deadline_unix):
    """Retain real signed bytes before boot without granting runtime acceptance."""
    app, destination = Path(app), Path(destination)
    require(app.name == 'OriginalEditorConsumer.app' and app.is_dir() and not app.is_symlink(),
            'Unexpected signed consumer root')
    require(signature.get('label') == 'external-consumer-signature'
            and signature.get('argv') == ['codesign', '--verify', '--strict', str(app)]
            and signature.get('status') == 'TERMINAL' and signature.get('returncode') == 0
            and signature.get('effective_returncode') == 0 and signature.get('timed_out') is False,
            'A successful actual consumer signature command is required')
    require(inventory(app) == expected_inventory and 0 < len(expected_inventory) <= 20000
            and sum(row['bytes'] for row in expected_inventory.values()) <= 2 * 1024 * 1024 * 1024,
            'Signed consumer inventory differs or exceeds its retention bound')
    require(time.time() + 45 < deadline_unix, 'No bounded consumer retention budget remains')
    destination.mkdir(parents=True, exist_ok=False)
    archive = destination / 'consumer-app.zip'
    partial = destination / 'consumer-app.zip.partial'
    modes, directories = {}, {}
    paths = [app, *sorted(app.rglob('*'))]
    with zipfile.ZipFile(partial, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in paths:
            require(time.time() < deadline_unix, 'Consumer retention deadline expired')
            mode = path.lstat().st_mode
            require(stat.S_ISREG(mode) or stat.S_ISDIR(mode), 'Aliased or special consumer member')
            require(not stat.S_IMODE(mode) & ~0o777, 'Special consumer permission bits')
            relative = path.relative_to(app).as_posix()
            if path.is_dir():
                directories[relative] = stat.S_IMODE(mode)
            else:
                modes[relative] = stat.S_IMODE(mode)
            output.write(path, app.name + ('/' + relative if relative != '.' else ''))
    with zipfile.ZipFile(partial) as retained:
        expected_names = {app.name + ('/' + key if key != '.' else '') + '/' for key in directories}
        expected_names |= {app.name + '/' + key for key in expected_inventory}
        require(set(retained.namelist()) == expected_names and len(retained.namelist()) == len(expected_names),
                'Retained consumer membership differs')
        for relative, mode in directories.items():
            name = app.name + ('/' + relative if relative != '.' else '') + '/'
            entry = retained.getinfo(name)
            require(entry.is_dir() and stat.S_IMODE(entry.external_attr >> 16) == mode,
                    'Retained consumer directory mode differs')
        for relative, expected in expected_inventory.items():
            require(time.time() < deadline_unix, 'Consumer archive verification deadline expired')
            entry = retained.getinfo(app.name + '/' + relative)
            with retained.open(entry) as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            require(entry.file_size == expected['bytes'] and actual == expected['sha256']
                    and stat.S_IMODE(entry.external_attr >> 16) == modes[relative], 'Retained signed consumer byte/mode differs')
    require(inventory(app) == expected_inventory, 'Consumer changed while being retained')
    require(all(stat.S_IMODE((app / name).stat().st_mode) == value for name, value in modes.items()),
            'Consumer file mode changed while being retained')
    require(all((app / name).is_dir() and stat.S_IMODE((app / name).stat().st_mode) == value
                for name, value in directories.items()), 'Consumer directory mode changed while being retained')
    partial.rename(archive)
    write_json(destination / 'consumer-app-inventory.json', expected_inventory)
    receipt = {'schema': 1, 'status': 'SIGNED_CONSUMER_RETAINED_WITHOUT_RUNTIME_QUALIFICATION',
        'runtime_qualified': False, 'restore_as_original_sdk_allowed': False,
        'consumer_producer': producer, 'framework_producer': framework_producer,
        'consumer_probe_sha256': source_sha256, 'consumer_source_inventory_sha256': source_inventory_sha256,
        'consumer_inventory_sha256': digest(destination / 'consumer-app-inventory.json'),
        'consumer_files': len(expected_inventory), 'consumer_bytes': sum(row['bytes'] for row in expected_inventory.values()),
        'archive_name': archive.name, 'archive_bytes': archive.stat().st_size, 'archive_sha256': digest(archive),
        'file_modes': modes, 'directories': directories, 'signature_command': signature,
        'scope': 'Exact signed external consumer only; original framework retains its original producer and inventory.'}
    write_json(destination / 'consumer-app-retention.json', receipt)
    return receipt


def cleanup_owned_simulator(commands, root, owned, expected_name, device, runtime, original_device_ids):
    """A drained shutdown failure cannot hide the targeted delete/post-state."""
    identifier = validate_ownership(owned, expected_name, device, runtime, original_device_ids)
    result = {'owned_udid': identifier, 'shutdown': None, 'delete': None, 'post_state': None,
              'owned_device_proven_absent': False, 'completed': False}
    operations = [('shutdown', 'shutdown-owned-simulator', ['xcrun', 'simctl', 'shutdown', identifier], 60),
                  ('delete', 'delete-owned-simulator', ['xcrun', 'simctl', 'delete', identifier], 60),
                  ('post_state', 'devices-after-cleanup', ['xcrun', 'simctl', 'list', 'devices', '-j'], 30)]
    for operation, label, argv, seconds in operations:
        if not commands.owned_groups_drained:
            result[operation] = {'status': 'NOT_ATTEMPTED_OWNED_COMMAND_GROUP_NOT_DRAINED'}
            continue
        try:
            code, output, error = commands.run(label, argv, root, seconds)
            result[operation] = {'effective_returncode': code,
                                 'timed_out': commands.items[-1].get('timed_out')}
            if operation == 'post_state' and code == 0:
                require(output.stat().st_size <= 8 * 1024 * 1024, 'Oversized cleanup device list')
                devices = json.loads(output.read_bytes())['devices']
                require(isinstance(devices, dict) and all(isinstance(rows, list) for rows in devices.values())
                        and all(isinstance(row, dict) and isinstance(row.get('udid'), str)
                                for rows in devices.values() for row in rows), 'Malformed cleanup device list')
                result['owned_device_proven_absent'] = not any(row['udid'].upper() == identifier.upper()
                    for rows in devices.values() for row in rows)
        except Exception as error:
            result[operation] = {'error_type': type(error).__name__, 'error': str(error)}
    result['owned_groups_drained'] = commands.owned_groups_drained
    result['completed'] = (commands.owned_groups_drained and result['owned_device_proven_absent']
                           and result['delete'].get('effective_returncode') == 0
                           and result['post_state'].get('effective_returncode') == 0)
    write_json(commands.evidence / 'OWNED_SIMULATOR_CLEANUP.json', result)
    return result
