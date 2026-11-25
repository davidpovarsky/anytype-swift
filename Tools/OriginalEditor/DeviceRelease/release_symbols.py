"""Complete Mach-O definitions without LLVM's quadratic dyld reconciliation.

LLVM nm adds exports missing from the symbol table when
NLIST_OUTOFSYNC_WITH_DYLDINFO is set. For the large Protobuf image, observe the
external defined table with nm and the ENTIRE export trie with Apple's native
dyld_info, then take their union. No dyld information is discarded. The unchanged
single-provider decision receives every table/export name, including weak and
thread-local definitions. Unexpected native formats fail closed.
"""
import re
from release_contract import digest, require, write
from release_process import command


def parse_export_trie(raw, binary):
    lines = raw.splitlines()
    require(len(lines) > 3 and lines[0] == str(binary) + ' [arm64]:'
            and lines[1].strip() == '-exports:'
            and lines[2].split() == ['offset', 'symbol'],
            'Unrecognized native Mach-O export listing header')
    names = set()
    kinds = {}
    for line in lines[3:]:
        match = re.fullmatch(r'\s*0x[0-9A-Fa-f]+\s+(\S+?)(?: \[(weak-def|per-thread|absolute)\])?\s*', line)
        require(match is not None, 'Unrecognized or incomplete native export row: ' + line[:200])
        name, kind = match.groups()
        require(name not in names, 'Duplicate native export-trie symbol')
        names.add(name)
        kinds[kind or 'regular'] = kinds.get(kind or 'regular', 0) + 1
    require(names, 'Empty native export trie')
    return names, kinds


def complete_definitions(binary, root, evidence, name):
    table_text = command(['xcrun', 'nm', '-gjU', '--no-dyldinfo', str(binary)],
                         root, evidence, name + '-table', 150)
    table = set(table_text.splitlines())
    require(table and all(s and not any(c.isspace() for c in s) for s in table),
            'Malformed external defined symbol table')
    trie_text = command(['xcrun', 'dyld_info', '-exports', str(binary)],
                        root, evidence, name + '-exports', 60)
    trie, kinds = parse_export_trie(trie_text, binary)
    names = table | trie
    receipt = {'status': 'COMPLETE_NLIST_AND_NATIVE_EXPORT_TRIE',
        'binary_sha256': digest(binary), 'table_definitions': len(table),
        'export_trie_definitions': len(trie), 'union_definitions': len(names),
        'table_only': len(table-trie), 'export_only': len(trie-table),
        'export_kinds': kinds,
        'table_stdout_sha256': digest(evidence / (name + '-table.stdout.log')),
        'export_stdout_sha256': digest(evidence / (name + '-exports.stdout.log')),
        'dyld_exports_omitted': 0, 'symbol_filters': ['extern-only', 'defined-only']}
    write(evidence / (name + '-complete.json'), receipt)
    return names, receipt
