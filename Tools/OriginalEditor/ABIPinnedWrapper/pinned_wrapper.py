#!/usr/bin/env python3
"""Audit a pinned-module adapter around a real, unmodified gomobile bind.

Only the generated wrapper's module preparation changes. Original Heart source,
gomobile/gobind, generated Go/ObjC bodies, targets, flags and packaging stay owned
by the original producer. This helper never qualifies a rejected archive.
"""
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
SCHEMA = 'otzaria.gomobile-pinned-wrapper-launch/1'
RESULT_SCHEMA = 'otzaria.gomobile-pinned-wrapper-observation/1'
HEART = 'github.com/anyproto/anytype-heart'
LOCAL_VERSION = 'v0.0.0-00010101000000-000000000000'
TARGETS = (('ios', 'arm64', 'iphoneos'),
           ('iossimulator', 'arm64', 'iphonesimulator'),
           ('iossimulator', 'amd64', 'iphonesimulator'))
TAGS = 'nogrpcserver gomobile nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg'
COMMAND_LABELS = ('generated-module', 'heart-module', 'retained-root-edit', 'retained-root-read',
                  'actual-tidy', 'selected-modules', 'compiler-declarations', 'actual-build')


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def row(path, name=None):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Expected regular admitted input: ' + str(path))
    before = path.stat()
    size = before.st_size
    digest, blob = hashlib.sha256(), hashlib.sha1(b'blob ' + str(size).encode() + b'\0')
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            blob.update(block)
    after = path.stat()
    require((before.st_size, before.st_mtime_ns, before.st_ino) ==
            (after.st_size, after.st_mtime_ns, after.st_ino), 'Input changed during hashing')
    return {'path': str(path) if name is None else name, 'bytes': size,
            'sha256': digest.hexdigest(), 'git_blob': blob.hexdigest()}


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.writing-' + str(uuid.uuid4()))
    with temporary.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
    os.replace(temporary, path)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def objects(text):
    decoder, offset, result = json.JSONDecoder(), 0, []
    while offset < len(text):
        while offset < len(text) and text[offset].isspace():
            offset += 1
        if offset == len(text):
            break
        item, offset = decoder.raw_decode(text, offset)
        require(isinstance(item, dict), 'Non-object Go declaration')
        result.append(item)
    require(result, 'Empty Go declaration')
    return result


def module_identity(module):
    value = {key: module.get(key, '') for key in ('Path', 'Version')}
    if module.get('Replace'):
        value['Replace'] = {key: module['Replace'].get(key, '') for key in ('Path', 'Version')}
    return value


def check_modules(actual, original, heart, source):
    original = {item['Path']: item for item in original}
    require(HEART in original and original[HEART].get('Main'), 'Original Heart module root absent')
    seen = set()
    for item in actual:
        name = item.get('Path')
        require(name and name not in seen and not item.get('Error'), 'Repeated or failed module selection')
        seen.add(name)
        if item.get('Main'):
            require(name == 'gobind' and Path(item.get('Dir', '/')).resolve() == source,
                    'Unexpected generated wrapper module')
        elif name == HEART:
            replacement = item.get('Replace', {})
            require(item.get('Version') == LOCAL_VERSION and replacement.get('Path') == str(heart)
                    and not replacement.get('Version') and Path(replacement.get('Dir', '/')).resolve() == heart,
                    'Wrapper does not select the exact original Heart root')
        else:
            require(name in original and module_identity(item) == module_identity(original[name]),
                    'Wrapper module selection differs from original Heart: ' + str(name))
    require('gobind' in seen and HEART in seen, 'Wrapper/Heart module selection is incomplete')


def check_retained_roots(actual, original, heart):
    expected = copy.deepcopy(original)
    expected['Module']['Path'] = 'gobind'
    expected['Require'] = list(expected.get('Require') or []) + [
        {'Path': HEART, 'Version': LOCAL_VERSION}]
    expected['Replace'] = list(expected.get('Replace') or []) + [
        {'Old': {'Path': HEART}, 'New': {'Path': str(heart)}}]
    def normalized(value):
        value = copy.deepcopy(value)
        for key in ('Require', 'Replace', 'Exclude', 'Retract', 'Tool'):
            if key in value:
                value[key] = sorted(value[key] or [], key=lambda x: json.dumps(x, sort_keys=True))
        return value
    require(normalized(actual) == normalized(expected),
            'Prepared module changed original root requirements, replacements or directives')


def check_generated_boundary(actual, modules):
    expected_requires, expected_replaces = [], []
    for module in modules:
        old = {'Path': module['Path']}
        if module.get('Version'):
            old['Version'] = module['Version']
        if module.get('Replace'):
            replacement = module['Replace']
            new = {'Path': replacement['Path']}
            if replacement.get('Version'):
                new['Version'] = replacement['Version']
            else:
                new['Path'] = replacement['Dir']
            expected_replaces.append({'Old': old, 'New': new})
        elif not module.get('Version'):
            expected_replaces.append({'Old': old, 'New': {'Path': module['Dir']}})
        else:
            expected_requires.append(old)
    sort = lambda values: sorted(values or [], key=lambda item: json.dumps(item, sort_keys=True))
    require(actual.get('Module') == {'Path': 'gobind'} and actual.get('Go') == '1.26.5'
            and sort(actual.get('Require')) == sort(expected_requires)
            and sort(actual.get('Replace')) == sort(expected_replaces)
            and not any(value for key, value in actual.items() if key not in ('Module', 'Go', 'Require', 'Replace')),
            'Generated module does not match the exact original gomobile promotion boundary')


def target_context(cwd, config, environment):
    cwd = Path(cwd)
    require(cwd.is_absolute() and cwd == cwd.resolve() and not cwd.is_symlink(), 'Aliased wrapper directory')
    retained = cwd.parent.parent
    temporary = Path(config['temporary'])
    require(retained.parent == temporary and retained.name.startswith('gomobile-work-')
            and retained == retained.resolve(), 'Wrapper escapes original owned gomobile work')
    target = (cwd.parent.name, cwd.name.removeprefix('src-'))
    require(cwd.name == 'src-' + target[1] and target in {(p, a) for p, a, _ in TARGETS},
            'Unexpected generated wrapper target')
    sdk = next(s for p, a, s in TARGETS if (p, a) == target)
    context = config['sdk_context'][sdk]
    arch = 'x86_64' if target[1] == 'amd64' else target[1]
    minimum = '-miphoneos-version-min=13.0' if target[0] == 'ios' else '-mios-simulator-version-min=13.0'
    flags = '-isysroot ' + context['sdk_root'] + ' ' + minimum + ' -fembed-bitcode -arch ' + arch
    expected = {'GOOS': 'ios', 'GOARCH': target[1], 'GOFLAGS': '-tags=ios', 'CGO_ENABLED': '1',
                'DARWIN_SDK': sdk, 'CC': context['clang'], 'CXX': context['clang'] + '++',
                'CGO_CFLAGS': flags, 'CGO_CXXFLAGS': flags, 'CGO_LDFLAGS': flags,
                'GOMODCACHE': config['module_cache'], 'GOPATH': str(retained / target[0]) + ':' + config['gopath'],
                'TMPDIR': str(retained)}
    require(all(environment.get(key) == value for key, value in expected.items()),
            'Actual wrapper target/compiler environment differs')
    require(not environment.get('GOWORK') or environment.get('GOWORK') == 'off', 'Unexpected workspace module selection')
    return target[0] + '-' + target[1], retained, expected


def build_argv(args, source, retained, config, require_absent=True):
    platform, architecture = source.parent.name, source.name.removeprefix('src-')
    archive = retained / ('Lib-' + platform + '-' + architecture + '.a')
    expected = ['build', '-tags', ','.join(TAGS.split()), '-x', '-ldflags', config['ldflags'],
                '-work', '-buildmode=c-archive', '-o', str(archive), './gobind']
    require(args == expected and (not require_absent or not archive.exists()), 'Unexpected/repeated original archive invocation')
    return [args[0], '-mod=readonly', *args[1:]], archive


def query_argv(args):
    require(args and args[0] in ('env', 'version', 'list'), 'Undeclared original-tool Go invocation')
    if args[0] == 'version':
        require(args == ['version'], 'Undeclared Go version query')
    elif args[0] == 'env':
        require(all(arg == '-json' or re.fullmatch(r'[A-Z][A-Z0-9_]*', arg) for arg in args[1:]),
                'Mutating or undeclared Go environment query')
    else:
        require(not any(arg.startswith(('-modfile', '-overlay', '-toolexec', '-exec', '-C'))
                        or arg.startswith('-mod=') and arg != '-mod=readonly' for arg in args[1:]),
                'Original-tool query attempts to replace source/module/compiler inputs')


def run(config, folder, label, args, cwd, environment, forward=False):
    folder.mkdir(parents=True, exist_ok=True)
    output, error = folder / (label + '.stdout.log'), folder / (label + '.stderr.log')
    require(not output.exists() and not error.exists(), 'Repeated actual command receipt')
    argv = [config['go']['path'], *args]
    target_names = {p + '-' + a for p, a, _ in TARGETS}
    receipt = {'schema': 'otzaria.pinned-wrapper-command/1', 'label': label,
               'target': folder.name if folder.name in target_names else None,
               'control_sha': config['control_sha'], 'command': argv, 'argv': argv,
               'cwd': str(cwd), 'started_at': datetime.now(timezone.utc).isoformat(),
               'timed_out': False, 'returncode': None,
               'process_group_owner': 'outer-original-gomobile-command'}
    try:
        budget = config['deadline'] - time.time()
        require(budget > 0, 'Pinned-wrapper command deadline expired')
        with output.open('xb') as stdout, error.open('xb') as stderr:
            process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=stdout, stderr=stderr)
            receipt['pid'] = process.pid
            try:
                receipt['returncode'] = process.wait(timeout=budget)
            except subprocess.TimeoutExpired:
                receipt['timed_out'] = True
                process.kill()
                process.wait()
                raise RuntimeError('Pinned-wrapper actual command timed out')
    finally:
        receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
        for name, path in (('stdout', output), ('stderr', error)):
            if path.exists():
                receipt[name] = row(path)
        write(folder / (label + '.command.json'), receipt)
        if forward:
            for path, stream in ((output, sys.stdout.buffer), (error, sys.stderr.buffer)):
                if path.exists():
                    with path.open('rb') as source:
                        shutil.copyfileobj(source, stream)
                    stream.flush()
    require(receipt['returncode'] == 0 and not receipt['timed_out'], 'Actual Go command failed: ' + label)
    return output


def validate_config(path, digest, require_live=True):
    path = Path(path)
    require(path.is_absolute() and path == path.resolve() and sha(path) == digest, 'Pinned launcher configuration differs')
    config = json.loads(path.read_bytes())
    require(config.get('schema') == SCHEMA and (not require_live or time.time() < config['deadline']),
            'Invalid/expired pinned launcher')
    for item in config['inputs']:
        require(row(item['path']) == item, 'Pinned launcher input changed: ' + item['path'])
    require(Path(config['go']['path']).is_absolute() and row(config['go']['path']) == config['go'],
            'Original Go compiler executable differs')
    require(row(config['python']['path']) == config['python'], 'Pinned launcher Python executable differs')
    require(Path(config['root']).resolve() == Path(config['root'])
            and config['control_sha'] == subprocess.check_output(
                ['git', '-C', config['root'], 'rev-parse', 'HEAD'], text=True).strip(), 'Adapter source revision changed')
    return config


def prepare(root, heart, work, evidence, environment, modules, go_root, sdk_context, ldflags, deadline):
    """Create a fresh explicit launcher; caller prepends its path only during bind."""
    root, heart, work, evidence, go_root = map(lambda x: Path(x).resolve(), (root, heart, work, evidence, go_root))
    require(work.is_relative_to(root / 'build') and evidence.is_relative_to(root / 'build'),
            'Pinned wrapper work/evidence must belong to this producer')
    require(heart.is_dir() and modules and len({m['Path'] for m in modules}) == len(modules),
            'Missing or repeated original module selection')
    require(next(m for m in modules if m.get('Main'))['Path'] == HEART, 'Unexpected original module root')
    folder, receipts = work / 'pinned-go-launcher', evidence / 'pinned-wrapper'
    folder.mkdir(exist_ok=False)
    receipts.mkdir(exist_ok=False)
    for platform, architecture, _ in TARGETS:
        (receipts / (platform + '-' + architecture)).mkdir()
    helper = Path(__file__).resolve()
    observer = root / 'Tools/OriginalEditor/ImportRPC/abi_mobile_inputs.py'
    for path in (helper, observer):
        require(path.is_relative_to(root) and subprocess.check_output(
            ['git', '-C', str(root), 'rev-parse', 'HEAD:' + path.relative_to(root).as_posix()], text=True).strip()
            == row(path)['git_blob'], 'Adapter/observer must match the committed control source')
    require(not list((work / 'tmp').glob('gomobile-work-*')), 'Refusing retained/rejected generated work')
    config = {'schema': SCHEMA, 'root': str(root), 'heart': str(heart), 'work': str(work),
              'temporary': str((work / 'tmp').resolve()), 'evidence': str(receipts),
              'control_sha': subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
              'inputs': [row(helper), row(observer), row(heart / 'go.mod'), row(heart / 'go.sum')],
              'helper': str(helper), 'observer': str(observer), 'go': row(go_root / 'bin/go'),
              'python': row(Path(sys.executable).resolve()),
              'goroot': str(go_root), 'original_modules': modules, 'sdk_context': sdk_context,
              'module_cache': str(Path(environment['GOMODCACHE']).resolve()), 'gopath': environment['GOPATH'],
              'ldflags': ldflags, 'deadline': deadline}
    require(config['temporary'] == environment['TMPDIR'] and deadline > time.time(), 'Owned preparation environment differs')
    config_path = folder / 'CONFIG.json'
    write(config_path, config)
    digest = sha(config_path)
    launcher = folder / 'go'
    launcher.write_text('#!' + sys.executable + '\nimport importlib.util, sys\n'
        + 's=importlib.util.spec_from_file_location("pinned_wrapper", ' + repr(str(helper)) + ')\n'
        + 'm=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n'
        + 'raise SystemExit(m.launch(' + repr(str(config_path)) + ', ' + repr(digest) + ', sys.argv[1:]))\n')
    launcher.chmod(0o755)
    descriptor = {'schema': SCHEMA, 'config': row(config_path), 'launcher': row(launcher),
                  'control_sha': config['control_sha'], 'source': row(helper), 'go': config['go'],
                  'path_prefix': str(folder), 'evidence': str(receipts),
                  'targets': [p + '-' + a for p, a, _ in TARGETS],
                  'original_gomobile_modified': False, 'rejected_archives_reused': False}
    write(receipts / 'LAUNCH.json', descriptor)
    return descriptor


def prepare_target(config, source, retained, name, environment):
    folder = Path(config['evidence']) / name
    require(not (folder / 'PREPARED.json').exists() and not (source / 'go.sum').exists(),
            'Generated wrapper preparation is not fresh')
    heart = Path(config['heart'])
    before = row(source / 'go.mod')
    shutil.copyfile(source / 'go.mod', folder / 'gomobile-go.mod.before')
    generated = json.loads(run(config, folder, 'generated-module', ['mod', 'edit', '-json'], source, environment).read_bytes())
    check_generated_boundary(generated, config['original_modules'])
    original = json.loads(run(config, folder, 'heart-module', ['mod', 'edit', '-json'], heart, environment).read_bytes())
    require(original['Module']['Path'] == HEART and original.get('Go') == '1.26.5', 'Original module/version differs')
    shutil.copyfile(heart / 'go.mod', source / 'go.mod')
    shutil.copyfile(heart / 'go.sum', source / 'go.sum')
    run(config, folder, 'retained-root-edit', ['mod', 'edit', '-module=gobind',
        '-require=' + HEART + '@' + LOCAL_VERSION, '-replace=' + HEART + '=' + str(heart)], source, environment)
    actual = json.loads(run(config, folder, 'retained-root-read', ['mod', 'edit', '-json'], source, environment).read_bytes())
    check_retained_roots(actual, original, heart)
    retained_roots = {n: row(source / n) for n in ('go.mod', 'go.sum')}
    run(config, folder, 'actual-tidy', ['mod', 'tidy'], source, environment, forward=True)
    tidy = {n: row(source / n) for n in ('go.mod', 'go.sum')}
    for n in ('go.mod', 'go.sum'):
        shutil.copyfile(source / n, folder / ('after-tidy.' + n))
    # Tidy may inspect dependency tests that are not actual compiler inputs.
    # None of its added checksums is admitted: the compiler receives the exact
    # original sum bytes and must load all declarations in readonly mode.
    shutil.copyfile(heart / 'go.sum', source / 'go.sum')
    selected = objects(run(config, folder, 'selected-modules', ['list', '-mod=readonly', '-m', '-json', 'all'],
                           source, environment).read_text())
    check_modules(selected, config['original_modules'], heart, source)
    declared_path = run(config, folder, 'compiler-declarations', ['list', '-mod=readonly', '-deps', '-json',
        '-tags', ','.join(TAGS.split()), './gobind'], source, environment)
    mobile = load(config['observer'], 'unchanged_original_mobile_observer')
    rows, packages = mobile.declared_files(objects(declared_path.read_text()),
        (heart, retained, config['module_cache'], config['goroot']), heart, source,
        {m['Path']: m for m in config['original_modules']}, row)
    current = {n: row(source / n) for n in ('go.mod', 'go.sum')}
    require(sha(source / 'go.sum') == sha(heart / 'go.sum'), 'Read-only preflight changed original checksums')
    value = {'schema': RESULT_SCHEMA, 'status': 'PINNED_GRAPH_PRECOMPILATION_PASS',
             'target': name, 'source': str(source), 'retained_work': str(retained),
             'original_generated_module': before, 'retained_original_roots': retained_roots,
             'tidy_outputs_not_admitted_as_checksums': tidy, 'compiler_module_inputs': current,
             'original_heart_module_inputs': {n: row(heart / n) for n in ('go.mod', 'go.sum')},
             'selected_modules': selected, 'declared_compiler_files': rows,
             'declared_compiler_file_count': len(rows),
             'packages': packages, 'no_added_checksum_admitted': True,
             'prepared_at': datetime.now(timezone.utc).isoformat(), 'control_sha': config['control_sha']}
    write(folder / 'PREPARED.json', value)


def build_target(config, source, retained, name, environment, args):
    folder, receipts = Path(config['evidence']) / name, Path(config['evidence'])
    actual, archive = build_argv(args, source, retained, config)
    expected = [p + '-' + a for p, a, _ in TARGETS]
    while not all((receipts / target / 'PREPARED.json').is_file() for target in expected):
        require(not list(receipts.glob('*/FAIL.json')), 'Another wrapper failed pre-compilation admission')
        require(time.time() < config['deadline'], 'All-target graph admission deadline expired')
        time.sleep(0.1)
    all_prepared = []
    for target in expected:
        path = receipts / target / 'PREPARED.json'
        value = json.loads(path.read_bytes())
        require(value['status'] == 'PINNED_GRAPH_PRECOMPILATION_PASS'
                and value['target'] == target and value['retained_work'] == str(retained)
                and value['control_sha'] == config['control_sha'], 'Incomplete/mixed wrapper preflight')
        all_prepared.append(row(path))
    prepared = json.loads((folder / 'PREPARED.json').read_bytes())
    for item in prepared['declared_compiler_files']:
        require(row(item['path'], item['path']) == item, 'Compiler input changed before archive build')
    require({n: row(source / n) for n in ('go.mod', 'go.sum')} == prepared['compiler_module_inputs'],
            'Prepared wrapper module changed before compilation')
    run(config, folder, 'actual-build', actual, source, environment, forward=True)
    for item in prepared['declared_compiler_files']:
        require(row(item['path'], item['path']) == item, 'Compiler input changed during archive build')
    require({n: row(source / n) for n in ('go.mod', 'go.sum')} == prepared['compiler_module_inputs'],
            'Read-only compilation changed prepared module files')
    write(folder / 'BUILT.json', {'schema': RESULT_SCHEMA, 'status': 'ACTUAL_PINNED_ARCHIVE_BUILD_PASS',
        'target': name, 'source': str(source), 'retained_work': str(retained),
        'original_gomobile_argv': args, 'actual_go_argv': [config['go']['path'], *actual],
        'all_targets_admitted_before_compile': all_prepared, 'prepared': row(folder / 'PREPARED.json'),
        'build_command': row(folder / 'actual-build.command.json'), 'archive': row(archive),
        'original_go_sum_preserved': True, 'control_sha': config['control_sha']})


def launch(config_path, digest, args):
    config, folder = None, None
    try:
        config = validate_config(config_path, digest)
        environment = os.environ.copy()
        source = Path.cwd().resolve()
        if source.is_relative_to(Path(config['temporary'])):
            name, retained, witnessed = target_context(source, config, environment)
            folder = Path(config['evidence']) / name
            write(folder / ('environment-' + str(os.getpid()) + '.json'), witnessed)
            if args == ['mod', 'tidy']:
                prepare_target(config, source, retained, name, environment)
            elif args and args[0] == 'build':
                build_target(config, source, retained, name, environment, args)
            else:
                raise RuntimeError('Unexpected generated-wrapper Go invocation')
        else:
            require(source == Path(config['heart']), 'Unexpected Go invocation outside generated wrappers')
            query_argv(args)
            folder = Path(config['evidence']) / 'original-tool-queries' / (str(os.getpid()) + '-' + str(uuid.uuid4()))
            run(config, folder, 'actual-query', args, source, environment, forward=True)
        return 0
    except BaseException as error:
        if folder is not None:
            write(folder / 'FAIL.json', {'status': 'FAIL', 'error_type': type(error).__name__, 'error': str(error)})
        sys.stderr.write('Pinned wrapper refused: ' + str(error) + '\n')
        return 1


def validate_observation(descriptor, require_live):
    """Read and validate the complete closure; never create or rewrite evidence."""
    for key in ('config', 'launcher', 'source', 'go'):
        require(row(descriptor[key]['path']) == descriptor[key], 'Pinned wrapper launch identity changed')
    config = validate_config(descriptor['config']['path'], descriptor['config']['sha256'], require_live=require_live)
    receipts = Path(descriptor['evidence'])
    require(not list(receipts.rglob('FAIL.json')), 'Pinned wrapper recorded a refusal')
    require(descriptor['targets'] == [p + '-' + a for p, a, _ in TARGETS], 'Incomplete/reordered target inventory')
    all_prepared = [row(receipts / name / 'PREPARED.json') for name in descriptor['targets']]
    heart = Path(config['heart'])
    original_module_rows = {name: next(item for item in config['inputs'] if item['path'] == str(heart / name))
                            for name in ('go.mod', 'go.sum')}
    retained_work = None
    queries = []
    query_paths = sorted((receipts / 'original-tool-queries').glob('*/actual-query.command.json'))
    require(3 <= len(query_paths) <= 128, 'Original-tool query inventory is incomplete or unbounded')
    module_queries = 0
    for path in query_paths:
        command = json.loads(path.read_bytes())
        require(command['schema'] == 'otzaria.pinned-wrapper-command/1' and command['label'] == 'actual-query'
                and command['target'] is None and command['control_sha'] == config['control_sha']
                and command['command'] == command['argv'] and command['argv'][0] == config['go']['path']
                and command['cwd'] == str(heart) and command['returncode'] == 0 and command['timed_out'] is False,
                'Original-tool query provenance differs')
        query_argv(command['argv'][1:])
        if command['argv'][1:4] == ['list', '-m', '-json'] and command['argv'][-1] == 'all':
            module_queries += 1
        for stream in ('stdout', 'stderr'):
            require(row(command[stream]['path']) == command[stream], 'Original-tool query stream differs')
        queries.append(row(path))
    require(module_queries == 3, 'Original gomobile did not observe exactly the three target module graphs')
    targets = []
    for name in descriptor['targets']:
        folder = receipts / name
        prepared = json.loads((folder / 'PREPARED.json').read_bytes())
        built = json.loads((folder / 'BUILT.json').read_bytes())
        source, retained = Path(prepared['source']), Path(prepared['retained_work'])
        require(source == source.resolve() and retained == source.parent.parent
                and retained.parent == Path(config['temporary']) and retained.name.startswith('gomobile-work-')
                and source.parent.name + '-' + source.name.removeprefix('src-') == name,
                'Actual wrapper source/target differs')
        require(retained_work in (None, str(retained)), 'Mixed original gomobile work roots')
        retained_work = str(retained)
        require(prepared['schema'] == RESULT_SCHEMA and built['schema'] == RESULT_SCHEMA
                and prepared['status'] == 'PINNED_GRAPH_PRECOMPILATION_PASS'
                and built['status'] == 'ACTUAL_PINNED_ARCHIVE_BUILD_PASS'
                and prepared['target'] == built['target'] == name
                and prepared['control_sha'] == built['control_sha'] == config['control_sha']
                and built['source'] == str(source) and built['retained_work'] == str(retained)
                and built['all_targets_admitted_before_compile'] == all_prepared
                and built['prepared'] == row(folder / 'PREPARED.json')
                and built['archive'] == row(built['archive']['path']), 'Target did not retain its actual pinned archive')
        require(prepared['original_heart_module_inputs'] == original_module_rows
                and prepared['no_added_checksum_admitted'] is True and built['original_go_sum_preserved'] is True
                and {n: row(source / n) for n in ('go.mod', 'go.sum')} == prepared['compiler_module_inputs']
                and sha(source / 'go.sum') == original_module_rows['go.sum']['sha256'],
                'Original Heart module/checksum proof differs')
        check_modules(prepared['selected_modules'], config['original_modules'], heart, source)
        compiler_rows = prepared['declared_compiler_files']
        require(compiler_rows and prepared['declared_compiler_file_count'] == len(compiler_rows)
                and len({item['path'] for item in compiler_rows}) == len(compiler_rows), 'Incomplete compiler source closure')
        for item in compiler_rows:
            require(row(item['path'], item['path']) == item, 'Declared compiler source changed after actual archive build')
        actual_args, archive = build_argv(built['original_gomobile_argv'], source, retained, config, require_absent=False)
        require(built['actual_go_argv'] == [config['go']['path'], *actual_args]
                and built['archive']['path'] == str(archive), 'Actual readonly archive argv differs')
        expected_commands = {
            'generated-module': ['mod', 'edit', '-json'], 'heart-module': ['mod', 'edit', '-json'],
            'retained-root-edit': ['mod', 'edit', '-module=gobind', '-require=' + HEART + '@' + LOCAL_VERSION,
                                   '-replace=' + HEART + '=' + str(heart)],
            'retained-root-read': ['mod', 'edit', '-json'], 'actual-tidy': ['mod', 'tidy'],
            'selected-modules': ['list', '-mod=readonly', '-m', '-json', 'all'],
            'compiler-declarations': ['list', '-mod=readonly', '-deps', '-json', '-tags', ','.join(TAGS.split()), './gobind'],
            'actual-build': actual_args}
        require({p.name for p in folder.glob('*.command.json')} == {label + '.command.json' for label in COMMAND_LABELS},
                'Actual wrapper command set is incomplete or expanded')
        for label in COMMAND_LABELS:
            path = folder / (label + '.command.json')
            command = json.loads(path.read_bytes())
            require(command['schema'] == 'otzaria.pinned-wrapper-command/1' and command['label'] == label
                    and command['control_sha'] == config['control_sha'] and command['target'] == name
                    and command['command'] == command['argv'] == [config['go']['path'], *expected_commands[label]]
                    and command['cwd'] == str(heart if label == 'heart-module' else source)
                    and command['returncode'] == 0 and command['timed_out'] is False, 'Target actual command differs or failed')
            for stream in ('stdout', 'stderr'):
                require(row(command[stream]['path']) == command[stream], 'Actual target command stream differs')
            if label == 'actual-build':
                require(built['build_command'] == row(path), 'Actual archive build command receipt differs')
                started = datetime.fromisoformat(command['started_at'])
                require(all(started >= datetime.fromisoformat(json.loads(Path(item['path']).read_bytes())['prepared_at'])
                            for item in all_prepared), 'An archive started before all target graph admissions')
        targets.append({'target': name, 'prepared': row(folder / 'PREPARED.json'), 'built': row(folder / 'BUILT.json'),
                        'commands': [row(p) for p in sorted(folder.glob('*.command.json'))]})
    result = {'schema': RESULT_SCHEMA, 'status': 'THREE_ACTUAL_PINNED_WRAPPERS_PASS',
              'control_sha': config['control_sha'], 'launch': descriptor, 'targets': targets,
              'original_tool_queries': queries,
              'original_gomobile_modified': False, 'rejected_archives_reused': False,
              'original_go_sum_preserved': True, 'all_targets_admitted_before_compile': True,
              'outer_command_drain_must_be_verified_by_producer': True}
    return result


def collect(descriptor):
    """Call once after real bind and after restoring the ordinary Go PATH."""
    result = validate_observation(descriptor, require_live=True)
    path = Path(descriptor['evidence']) / 'RESULT.json'
    require(not path.exists(), 'Refusing to rewrite a retained wrapper result')
    write(path, result)
    return row(path), result


def verify(result_path, expected_sha256, root, source_sha):
    """Read-only ABI intake before/after SDK, including after a past deadline."""
    root, result_path = Path(root).resolve(), Path(result_path)
    require(result_path.is_absolute() and result_path == result_path.resolve()
            and result_path.is_relative_to(root / 'build') and not result_path.is_symlink()
            and re.fullmatch(r'[0-9a-f]{64}', expected_sha256 or '')
            and sha(result_path) == expected_sha256, 'Exact owned wrapper result is required')
    result = json.loads(result_path.read_bytes())
    require(result.get('schema') == RESULT_SCHEMA and result.get('control_sha') == source_sha
            and source_sha == subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
            'Pinned wrapper result/control source differs')
    launch = result['launch']
    require(Path(launch['evidence']) == result_path.parent and launch['control_sha'] == source_sha
            and launch['source'] == row(Path(__file__).resolve())
            and Path(launch['source']['path']) == root / 'Tools/OriginalEditor/ABIPinnedWrapper/pinned_wrapper.py'
            and Path(launch['config']['path']).is_relative_to(root / 'build')
            and Path(launch['launcher']['path']).is_relative_to(root / 'build'), 'Pinned wrapper source/launch path differs')
    require(subprocess.check_output(['git', '-C', str(root), 'rev-parse',
            'HEAD:Tools/OriginalEditor/ABIPinnedWrapper/pinned_wrapper.py'], text=True).strip()
            == launch['source']['git_blob'], 'Verifier differs from committed control source')
    config = json.loads(Path(launch['config']['path']).read_bytes())
    require(config['root'] == str(root) and config['control_sha'] == source_sha,
            'Wrapper configuration belongs to another source/root')
    require(validate_observation(launch, require_live=False) == result,
            'Authenticated wrapper result differs from complete actual evidence')
    return {'schema': RESULT_SCHEMA, 'status': result['status'], 'control_sha': source_sha,
            'receipt_sha256': expected_sha256, 'targets': launch['targets'],
            'original_go_sum_preserved': True, 'all_targets_admitted_before_compile': True,
            'original_gomobile_modified': False, 'rejected_archives_reused': False}
