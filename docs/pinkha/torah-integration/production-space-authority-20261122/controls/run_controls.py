import argparse, datetime, hashlib, json, os, pathlib, platform, shutil, subprocess, sys, time

def sha(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--result-directory', required=True)
    parser.add_argument('--only', default='')
    args = parser.parse_args()
    packet = pathlib.Path(__file__).resolve().parent
    manifest = json.loads((packet / 'INPUTS.json').read_text(encoding='utf-8'))
    result = pathlib.Path(args.result_directory).resolve()
    if result.exists():
        raise RuntimeError('Refusing to overwrite any prior execution directory')
    result.mkdir(parents=True)
    root = packet
    while not (root / '.git').exists():
        if root.parent == root:
            raise RuntimeError('Repository root not found')
        root = root.parent
    product = root / manifest['product_path']
    if sha(product) != manifest['candidate_sha256']:
        raise RuntimeError('Product candidate changed after source review')
    verified = []
    for item in manifest['source_inputs']:
        data = subprocess.check_output(['git', 'show', manifest['base'] + ':' + item['path']],
                                       cwd=root, timeout=20)
        actual = hashlib.sha256(data).hexdigest()
        if actual != item['sha256']:
            raise RuntimeError('Canonical input changed: ' + item['path'])
        verified.append(dict(item, verified=True))
    copies = []
    compiled = result / 'compiled-inputs'
    compiled.mkdir()
    for item in manifest['swift_inputs']:
        path = packet / item['name']
        if sha(path) != item['sha256']:
            raise RuntimeError('Execution input changed: ' + item['name'])
        target = compiled / item['name']
        shutil.copyfile(path, target)
        if sha(target) != item['sha256']:
            raise RuntimeError('Compiled input copy differs')
        copies.append(dict(item, compiled_path=str(target)))
    control_source = (packet / 'Controls.swift').read_text(encoding='utf-8')
    selected = args.only.split(',') if args.only else manifest['expected_controls']
    if not selected or len(selected) != len(set(selected)) or not set(selected) <= set(manifest['expected_controls']):
        raise RuntimeError('Invalid control selection')
    compiler = shutil.which('swiftc')
    if compiler is None:
        raise RuntimeError('Swift compiler not available')
    commands = []
    def run(name, command, timeout):
        started = time.monotonic()
        out = result / (name + '.stdout')
        err = result / (name + '.stderr')
        timed_out = False
        with out.open('wb') as stdout, err.open('wb') as stderr:
            try:
                process = subprocess.run(command, cwd=compiled, stdout=stdout, stderr=stderr, timeout=timeout)
                code = process.returncode
            except subprocess.TimeoutExpired:
                code = None
                timed_out = True
        entry = dict(name=name, command=list(map(str, command)), cwd=str(compiled),
                     exit_code=code, timeout=timed_out, seconds=time.monotonic()-started,
                     stdout_sha256=sha(out), stderr_sha256=sha(err))
        commands.append(entry)
        print(json.dumps(entry), flush=True)
        return code
    version_code = run('swift-version', [compiler, '--version'], 30)
    binary = result / ('spaceview-authority-controls.exe' if os.name == 'nt' else 'spaceview-authority-controls')
    syntax_code = run('full-source-syntax', [compiler, '-frontend', '-parse', str(product)], 60)
    compile_command = [compiler, '-swift-version', '5', '-strict-concurrency=complete',
                       '-parse-as-library', '-j', '1', '-whole-module-optimization', '-Onone']
    compile_command += [str(compiled / item['name']) for item in manifest['swift_inputs']]
    compile_command += ['-o', str(binary)]
    compile_code = run('compile', compile_command, 240) if syntax_code == 0 and version_code == 0 else None
    binary_sha = sha(binary) if binary.is_file() else None
    executed = None
    result_path = result / 'RESULT.json'
    if compile_code == 0:
        command = [str(binary), str(result_path)]
        if args.only:
            command.append(args.only)
        executed = run('execute', command, 120)
    actual = json.loads(result_path.read_text(encoding='utf-8')) if result_path.is_file() else None
    passed = False
    if actual:
        if actual['candidateSHA256'] != manifest['candidate_sha256']:
            raise RuntimeError('Result source binding mismatch')
        expected_order = [name for name in manifest['expected_controls'] if name in selected]
        if [case['name'] for case in actual['results']] != expected_order:
            raise RuntimeError('Result selected controls mismatch')
        raw = (result / 'execute.stdout').read_text(encoding='utf-8').splitlines()
        if raw != [case['status'] + ' ' + case['name'] for case in actual['results']]:
            raise RuntimeError('Raw named outcomes differ from structured result')
        passed = executed == 0 and all(case['status'] == 'PASS' for case in actual['results'])
    for item in copies:
        if sha(item['compiled_path']) != item['sha256']:
            raise RuntimeError('Compiled input changed during execution')
    if sha(product) != manifest['candidate_sha256']:
        raise RuntimeError('Product source changed during execution')
    execution = dict(
        schema=1, candidate_sha256=manifest['candidate_sha256'],
        expected_controls=selected, selected_count=len(selected),
        completed_controls=len(actual['results']) if actual else 0, all_passed=passed,
        source_inputs=verified, compiled_inputs=copies,
        manifest_sha256=sha(packet/'INPUTS.json'), runner_sha256=sha(pathlib.Path(__file__)),
        compiler_path=compiler, compiler_sha256=sha(compiler),
        compiler_version=(result/'swift-version.stdout').read_text(encoding='utf-8'),
        binary_sha256=binary_sha, result_sha256=sha(result_path) if actual else None,
        platform=platform.platform(), python=sys.version, commands=commands,
        original_native_calls=0, prior_suites_rerun=False,
        scope=manifest['scope'], completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    (result/'EXECUTION.json').write_text(json.dumps(execution,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(status='PASS' if passed else 'FAIL', directory=str(result),
                         result_sha256=execution['result_sha256'], binary_sha256=binary_sha,
                         completed_controls=execution['completed_controls'])), flush=True)
    return 0 if passed else 1

if __name__ == '__main__':
    raise SystemExit(main())
