#!/usr/bin/env python3
"""Compare complete table+trie sets with preserved successful native nm outputs."""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_contract import digest, require, timestamp, write
from release_symbols import complete_definitions


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--cases', nargs='+', choices=['SDK-Release-Simulator/AnytypeOriginalEditor',
        'SDK-Release-Simulator/OriginalEditorSharedFirebase', 'SDK-Release-Simulator/AnytypeCore',
        'SDK/ProtobufMessages'])
    args = p.parse_args()
    require(args.root.resolve() == args.root and args.evidence.resolve() == args.evidence
            and args.evidence.is_relative_to(args.root / 'build') and not args.evidence.exists(),
            'Parity check requires a fresh owned evidence root')
    args.evidence.mkdir()
    rows = []
    receipt = {'status':'FAIL', 'started_at':timestamp(), 'checks':rows}
    try:
        cases = [('SDK-Release-Simulator', name) for name in
                 ['AnytypeOriginalEditor','OriginalEditorSharedFirebase','AnytypeCore']]
        cases.append(('SDK','ProtobufMessages'))
        if args.cases:
            cases = [tuple(item.split('/')) for item in args.cases]
        for kind, name in cases:
            old = args.root / ('build/' + kind + '-Evidence')
            work = args.root / ('build/' + kind + '-Work')
            relative = 'Frameworks/' + name + '.framework/' + name
            binary = work / 'distribution' / relative
            manifest = json.loads((old / 'framework-distribution.json').read_text())
            require(digest(binary) == manifest['files'][relative]['sha256'],
                    'Reference native binary changed')
            prior = old / ('shared-provider-definitions-' + name + '.command.json')
            command = json.loads(prior.read_text())
            log = old / ('shared-provider-definitions-' + name + '.stdout.log')
            require(command['command'] == ['xcrun','nm','-gjU',str(binary)]
                    and command['returncode'] == 0 and command.get('timed_out', False) is False
                    and digest(log) == command['stdout_sha256'],
                    'Reference exact native nm result is absent, failed or modified')
            expected = set(log.read_text().splitlines())
            observed, extraction = complete_definitions(binary, args.root, args.evidence,
                                                        kind + '-' + name)
            require(observed == expected,
                    'Full native symbol set differs: ' + name +
                    ' missing=' + str(len(expected-observed)) + ' extra=' + str(len(observed-expected)))
            rows.append({'case':kind + '/' + name, 'status':'EXACT_SET_EQUAL',
                'binary_sha256':digest(binary), 'original_command_sha256':digest(prior),
                'original_stdout_sha256':digest(log), 'symbol_count':len(observed),
                'complete_extraction':extraction})
        receipt['status'] = 'PASS_EXACT_NATIVE_SYMBOL_SET_PARITY'
    finally:
        receipt['finished_at'] = timestamp()
        write(args.evidence / 'SYMBOL_PARITY.json', receipt)
        print(json.dumps({'status':receipt['status'], 'checks':len(rows)}, indent=2))


if __name__ == '__main__':
    main()
