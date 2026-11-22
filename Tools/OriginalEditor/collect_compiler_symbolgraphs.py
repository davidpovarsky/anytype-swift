"""Retain full symbol graphs emitted by the original successful framework build.

This does not invoke an extractor or change the compiler's public/SPI surface.
The original driver still owns source qualification, the fresh build directory,
the full public-surface verifier, and the later binary-only consumer gates.
"""
import argparse
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import stat

from framework_profile import TARGET, sha256, source_observation
from pbx_source import require


def option_values(arguments, option):
    indices = [index for index, value in enumerate(arguments) if value == option]
    require(all(index + 1 < len(arguments) for index in indices),
            'Missing compiler/build option value: ' + option)
    return [arguments[index + 1] for index in indices]


def owned_path(path, parent, *, directory):
    """Reject aliases in the existing, driver-owned portion of an output path."""
    path, parent = Path(path), Path(parent)
    require(path.is_absolute() and path.is_relative_to(parent) and path != parent
            and '..' not in path.parts, 'Unowned symbol graph input/output path')
    current = parent
    for part in path.relative_to(parent).parts:
        current = current / part
        details = current.lstat()
        require(not stat.S_ISLNK(details.st_mode), 'Aliased symbol graph input/output path')
        if current != path:
            require(stat.S_ISDIR(details.st_mode), 'Non-directory symbol graph ancestor')
    require(stat.S_ISDIR(details.st_mode) if directory else stat.S_ISREG(details.st_mode),
            'Unexpected symbol graph input/output type')
    return path


def regular_bytes(path):
    """Read one stable regular file without following a final symlink."""
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode), 'Symbol graph evidence is not a regular file')
        raw = stream.read()
        after = os.fstat(stream.fileno())
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    require(identity(before) == identity(after) and len(raw) == before.st_size,
            'Symbol graph evidence changed while reading')
    return raw, before


def record(raw):
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    require(parsed.tzinfo is not None, 'Build timestamp has no time zone')
    return parsed.timestamp()


def collect(root, derived, evidence, sdk, output_dir):
    root = Path(root).resolve(strict=True)
    derived, evidence, output_dir = map(Path, (derived, evidence, output_dir))
    require(derived.name == 'producer-derived'
            and not derived.is_relative_to(evidence) and not evidence.is_relative_to(derived),
            'Unowned or overlapping producer/evidence directory')
    owned_path(root / 'build', root, directory=True)
    owned_path(derived, root / 'build', directory=True)
    owned_path(evidence, root / 'build', directory=True)
    require(output_dir == evidence / 'actual-public-symbol-graphs'
            and not os.path.lexists(output_dir), 'Refusing stale or foreign collected symbol graphs')
    collection_path = evidence / 'compiler-symbolgraph-collection.json'
    require(not os.path.lexists(collection_path), 'Refusing stale symbol graph collection receipt')

    input_paths = [evidence / name for name in
                   ['source-before.json', 'framework-build.command.json', 'framework-build.stdout.log']]
    for path in input_paths:
        owned_path(path, evidence, directory=False)
    before_raw, _ = regular_bytes(input_paths[0])
    before = json.loads(before_raw)
    require(before == source_observation(root), 'Source differs from original build admission')
    command_raw, _ = regular_bytes(input_paths[1])
    build = json.loads(command_raw)
    log_raw, _ = regular_bytes(input_paths[2])
    require(build.get('returncode') == 0 and build.get('timed_out') is False
            and build.get('cwd') == str(root)
            and build.get('stdout_sha256') == record(log_raw)['sha256']
            and build.get('timeout_seconds') == 6000,
            'Symbol graphs are not bound to the successful original framework build')
    build_arguments = build.get('command')
    require(isinstance(build_arguments, list) and build_arguments[:2] == ['xcodebuild', 'build']
            and option_values(build_arguments, '-project') == [str(root / 'Anytype.xcodeproj')]
            and option_values(build_arguments, '-scheme') == [TARGET]
            and option_values(build_arguments, '-configuration') == ['Debug-Anytype']
            and option_values(build_arguments, '-derivedDataPath') == [str(derived)]
            and option_values(build_arguments, '-resultBundlePath') == [str(evidence / 'framework-build.xcresult')],
            'Original framework build identity or owned derived directory differs')
    started, finished = timestamp(build['started_at']), timestamp(build['finished_at'])
    require(started < finished, 'Invalid original framework build interval')

    candidates = []
    for line in log_raw.decode('utf-8').splitlines():
        if 'builtin-SwiftDriver --' not in line:
            continue
        arguments = shlex.split(line.strip())
        if TARGET in option_values(arguments, '-module-name'):
            candidates.append((line, arguments))
    require(len(candidates) == 1, 'Missing or ambiguous original target compiler command')
    line, arguments = candidates[0]
    require(arguments[:2] == ['builtin-SwiftDriver', '--']
            and len(arguments) > 2 and Path(arguments[2]).name == 'swiftc'
            and option_values(arguments, '-module-name') == [TARGET]
            and option_values(arguments, '-target') == ['arm64-apple-ios27.0-simulator']
            and option_values(arguments, '-sdk') == [str(sdk)]
            and option_values(arguments, '-swift-version') == ['5']
            and option_values(arguments, '-working-directory') == [str(root)],
            'Actual compiler module, target, SDK, language or checkout differs')
    definitions = set(option_values(arguments, '-D')) | {
        value[2:] for value in arguments if value.startswith('-D') and value != '-D'}
    require({'DEBUG', 'PINKHA_NATIVE_DERIVED'} <= definitions,
            'Original Debug/Heart compiler definitions were not preserved')
    graph_options = {'-emit-symbol-graph', '-emit-symbol-graph-dir',
                     '-symbol-graph-minimum-access-level', '-include-spi-symbols'}
    require(all(value in graph_options for value in arguments if value.startswith('-')
                and ('symbol-graph' in value or 'symbolgraph' in value or value.startswith('-include-spi')))
            and not any(value.startswith(('-skip-synthesized', '-skip-inherited', '-minimum-access-level'))
                        for value in arguments)
            and arguments.count('-emit-symbol-graph') == 1
            and arguments.count('-include-spi-symbols') == 1
            and option_values(arguments, '-symbol-graph-minimum-access-level') == ['public'],
            'Full public/SPI compiler emission is absent, filtered or ambiguous')
    module_paths = option_values(arguments, '-emit-module-path')
    graph_paths = option_values(arguments, '-emit-symbol-graph-dir')
    require(len(module_paths) == 1 and len(graph_paths) == 1,
            'Missing or ambiguous original target output paths')
    target_build = derived / ('Build/Intermediates.noindex/Anytype.build/'
                              'Debug-Anytype-iphonesimulator/' + TARGET + '.build')
    require(Path(module_paths[0]) == target_build / 'Objects-normal/arm64' / (TARGET + '.swiftmodule')
            and Path(graph_paths[0]) == target_build / 'DerivedSources/OriginalEditorSymbolGraphs',
            'Graph directory is not the actual owned framework target DerivedSources directory')
    graph_directory = owned_path(Path(graph_paths[0]), derived, directory=True)
    members = sorted(graph_directory.iterdir())
    require(members and graph_directory / (TARGET + '.symbols.json') in members
            and all(path.name.endswith('.symbols.json') for path in members),
            'Original full target symbol graph or complete graph-only directory is absent')

    output_dir.mkdir()
    graphs = []
    for path in members:
        owned_path(path, graph_directory, directory=False)
        raw, details = regular_bytes(path)
        # Permit only the file-system's one-second timestamp granularity. The
        # original source-bound driver also refuses a pre-existing work tree.
        require(math.floor(started) * 1_000_000_000 <= details.st_mtime_ns
                <= math.ceil(finished) * 1_000_000_000,
                'Symbol graph was not written within this original build interval')
        graph = json.loads(raw)
        require(isinstance(graph, dict) and isinstance(graph.get('module'), dict)
                and isinstance(graph['module'].get('name'), str)
                and isinstance(graph.get('symbols'), list)
                and isinstance(graph.get('relationships'), list), 'Malformed full compiler symbol graph')
        if path.name == TARGET + '.symbols.json':
            require(graph['module']['name'] == TARGET and bool(graph['symbols']),
                    'Original framework public/SPI graph is empty or names another module')
        destination = output_dir / path.name
        with destination.open('xb') as stream:
            stream.write(raw)
        require(sha256(destination) == record(raw)['sha256'], 'Collected full graph bytes differ')
        graphs.append({'source': str(path), 'collected': str(destination), **record(raw),
                       'module': graph['module']['name'], 'symbols': len(graph['symbols']),
                       'relationships': len(graph['relationships']), 'source_mtime_ns': details.st_mtime_ns})

    require(sorted(graph_directory.iterdir()) == members, 'Compiler graph membership changed during collection')
    for graph in graphs:
        raw, _ = regular_bytes(Path(graph['source']))
        require(record(raw) == {'sha256': graph['sha256'], 'bytes': graph['bytes']},
                'Original compiler graph changed during collection')
    require(regular_bytes(input_paths[0])[0] == before_raw
            and regular_bytes(input_paths[1])[0] == command_raw
            and regular_bytes(input_paths[2])[0] == log_raw
            and source_observation(root) == before, 'Original source/build evidence changed during collection')
    receipt = {'schema': 1, 'status': 'ACTUAL_COMPILER_FULL_GRAPHS_COLLECTED_SURFACE_NOT_YET_VERIFIED',
               'source_sha': before['head_sha'], 'run_id': before['run_id'], 'run_attempt': before['run_attempt'],
               'source_admission': record(before_raw), 'framework_build_command': record(command_raw),
               'framework_build_stdout': record(log_raw), 'compiler_line_sha256': record(line.encode())['sha256'],
               'compiler_arguments': arguments, 'module': TARGET, 'sdk': str(sdk),
               'target': 'arm64-apple-ios27.0-simulator', 'swift_version': '5',
               'minimum_access_level': 'public', 'include_spi_symbols': True,
               'source_graph_directory': str(graph_directory), 'output_directory': str(output_dir),
               'graphs': graphs, 'all_emitted_graphs_copied_without_filtering': True,
               'standalone_extractor_invocations': 0, 'native_editor_ui_tests': 0,
               'build_started_at': build['started_at'], 'build_finished_at': build['finished_at']}
    with collection_path.open('x') as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ['root', 'derived', 'evidence', 'sdk', 'output-dir']:
        parser.add_argument('--' + option, type=Path, required=True)
    arguments = parser.parse_args()
    receipt = collect(arguments.root, arguments.derived, arguments.evidence,
                      arguments.sdk, arguments.output_dir)
    print(json.dumps({'status': receipt['status'], 'graphs': len(receipt['graphs']),
                      'source_sha': receipt['source_sha'], 'native_editor_ui_tests': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
