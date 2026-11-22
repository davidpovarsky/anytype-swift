"""One retained-artifact intake and read-only bundle/load-command inspection."""
import datetime
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import plistlib
import stat
import struct
import subprocess
import zipfile

ROOT = Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-sdk-runtime-watch-45054111060')
DEST = ROOT / 'signed-consumer-intake'
GH = r'C:\Program Files\GitHub CLI\gh.EXE'
ARTIFACT = 14766857451
OUTER_SHA = '54e2a4b191d1248ab446273628f397bb2763c26efcf1c9648c208c3ae0469302'
EXPECTED_HEAD = '0b792c7f2906f375e34b30a0cb42b85d98c0ba56'

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def emit(name, value):
    (DEST / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def packed_version(value):
    return '%d.%d.%d' % (value >> 16, (value >> 8) & 255, value & 255)

def macho(stream, size):
    # Constants and load-command layouts are from Apple's published loader.h.
    stream.seek(0)
    first = stream.read(4)
    slices = []
    if first in (b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf'):
        count = struct.unpack('>I', stream.read(4))[0]
        assert 0 < count <= 32
        wide = first[-1] == 0xbf
        for _ in range(count):
            if wide:
                cpu, subtype, offset, length, align, reserved = struct.unpack('>IIQQII', stream.read(32))
            else:
                cpu, subtype, offset, length, align = struct.unpack('>IIIII', stream.read(20))
            assert 0 <= offset < size and 0 < length <= size-offset
            slices.append((offset, length))
    elif first == b'\xcf\xfa\xed\xfe':
        slices = [(0, size)]
    else:
        return None
    result = []
    for offset, length in slices:
        stream.seek(offset)
        header = stream.read(32)
        magic, cpu, subtype, kind, count, command_bytes, flags, reserved = struct.unpack('<8I', header)
        assert magic == 0xfeedfacf and count <= 4096 and 0 < command_bytes <= min(length-32, 1024*1024)
        data = stream.read(command_bytes)
        assert len(data) == command_bytes
        item = {'cpu_type': cpu, 'cpu_subtype': subtype, 'file_type': kind, 'flags': flags,
                'load_commands': count, 'load_command_bytes': command_bytes, 'rpaths': [], 'dylibs': []}
        cursor = 0
        for _ in range(count):
            cmd, cmdsize = struct.unpack_from('<II', data, cursor)
            assert cmdsize >= 8 and cmdsize % 8 == 0 and cursor+cmdsize <= len(data)
            part = data[cursor:cursor+cmdsize]
            def string_at(index):
                assert 0 <= index < len(part)
                end = part.find(b'\0', index)
                assert end >= index
                return part[index:end].decode('utf-8')
            if cmd in (0xc, 0xd, 0x80000018, 0x8000001f, 0x20, 0x80000023):
                index, stamp, current, compatible = struct.unpack_from('<4I', part, 8)
                item['dylibs'].append({'command': hex(cmd), 'path': string_at(index),
                    'current': packed_version(current), 'compatibility': packed_version(compatible)})
            elif cmd == 0x8000001c:
                item['rpaths'].append(string_at(struct.unpack_from('<I', part, 8)[0]))
            elif cmd == 0x32:
                platform, minimum, sdk, tool_count = struct.unpack_from('<4I', part, 8)
                item['build_version'] = {'platform': platform, 'minimum': packed_version(minimum),
                                         'sdk': packed_version(sdk), 'tool_count': tool_count}
            elif cmd == 0x1b:
                item['uuid_hex'] = part[8:24].hex()
            cursor += cmdsize
        assert cursor == command_bytes
        result.append(item)
    return result

assert not DEST.exists(), 'This artifact intake must not be repeated automatically'
DEST.mkdir()
artifact = next(row for row in json.loads((ROOT/'ARTIFACTS.json').read_bytes())['artifacts'] if row['id'] == ARTIFACT)
assert artifact['workflow_run']['id'] == 45054111060 and artifact['workflow_run']['head_sha'] == EXPECTED_HEAD
assert artifact['digest'] == 'sha256:'+OUTER_SHA and artifact['expired'] is False
outer_path = DEST / ('artifact-%s.zip' % ARTIFACT)
attempt = {'artifact_id': ARTIFACT, 'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'download_attempts': 1, 'runtime_executed': False}
emit('DOWNLOAD_ATTEMPT.json', attempt)
with outer_path.open('xb') as output:
    command = [GH, 'api', 'repos/davidpovarsky/anytype-swift/actions/artifacts/%s/zip' % ARTIFACT]
    outcome = subprocess.run(command, stdout=output, stderr=subprocess.PIPE, timeout=180)
(DEST/'download.stderr').write_bytes(outcome.stderr)
assert outcome.returncode == 0
assert outer_path.stat().st_size == artifact['size_in_bytes'] and digest(outer_path) == OUTER_SHA
with zipfile.ZipFile(outer_path) as outer:
    assert outer.testzip() is None
    assert len(outer.namelist()) == 3 and set(outer.namelist()) == {'consumer-app.zip','consumer-app-inventory.json','consumer-app-retention.json'}
    retained_raw = outer.read('consumer-app-retention.json')
    retained = json.loads(retained_raw)
    assert retained == json.loads((ROOT/'evidence/retained-consumer.json').read_bytes())
    inventory_raw = outer.read('consumer-app-inventory.json')
    inventory = json.loads(inventory_raw)
    assert inventory_raw == (ROOT/'evidence/consumer-app-inventory.json').read_bytes()
    assert hashlib.sha256(inventory_raw).hexdigest() == retained['consumer_inventory_sha256']
    with outer.open('consumer-app.zip') as stream, (DEST/'consumer-app.zip').open('xb') as output:
        while chunk := stream.read(1024*1024):
            output.write(chunk)
    (DEST/'consumer-app-retention.json').write_bytes(retained_raw)
    (DEST/'consumer-app-inventory.json').write_bytes(inventory_raw)
inner_path = DEST/'consumer-app.zip'
assert inner_path.stat().st_size == retained['archive_bytes'] and digest(inner_path) == retained['archive_sha256']
prefix = 'OriginalEditorConsumer.app/'
expected = {prefix+path for path in inventory}
expected |= {prefix if path == '.' else prefix+path+'/' for path in retained['directories']}
machos, plists = {}, {}
with zipfile.ZipFile(inner_path) as inner:
    names = inner.namelist()
    assert len(names) == len(set(names)) and set(names) == expected and inner.testzip() is None
    for item in inner.infolist():
        path = PurePosixPath(item.filename)
        assert not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename
        assert stat.S_IFMT(item.external_attr >> 16) in (stat.S_IFREG, stat.S_IFDIR)
    for name, mode in retained['directories'].items():
        path = prefix if name == '.' else prefix+name+'/'
        entry = inner.getinfo(path)
        assert entry.is_dir() and stat.S_IMODE(entry.external_attr >> 16) == mode
    for name, info in inventory.items():
        entry = inner.getinfo(prefix+name)
        assert not entry.is_dir() and entry.file_size == info['bytes']
        assert stat.S_IMODE(entry.external_attr >> 16) == retained['file_modes'][name]
        with inner.open(entry) as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == info['sha256']
        with inner.open(entry) as stream:
            parsed = macho(stream, entry.file_size) if entry.file_size >= 32 else None
        if parsed is not None:
            machos[name] = {'bytes': info['bytes'], 'sha256': info['sha256'], 'slices': parsed}
        if name == 'Info.plist' or name.startswith('Frameworks/') and name.count('/') == 2 and name.endswith('/Info.plist'):
            plists[name] = plistlib.loads(inner.read(entry))
    assert len(inventory) == retained['consumer_files'] == 642
    assert sum(row['bytes'] for row in inventory.values()) == retained['consumer_bytes'] == 500498107
result = {'status':'AUTHENTICATED_SIGNED_CONSUMER_STATIC_INSPECTION_ONLY','artifact_id':ARTIFACT,
    'outer_bytes':outer_path.stat().st_size,'outer_sha256':OUTER_SHA,
    'inner_bytes':inner_path.stat().st_size,'inner_sha256':digest(inner_path),
    'consumer_files_verified':len(inventory),'consumer_bytes_verified':sum(row['bytes'] for row in inventory.values()),
    'directory_count_verified':len(retained['directories']),'file_and_directory_modes_verified':True,
    'download_attempts':1,'runtime_executed':False,'runtime_qualified':False,'macho':machos,'bundle_plists':plists,
    'primary_format_source':'https://github.com/apple-oss-distributions/xnu/blob/main/EXTERNAL_HEADERS/mach-o/loader.h',
    'limitations':['Load-command inspection is not dyld execution or code-signature revalidation.','Original launch failure is retained unchanged.']}
emit('STATIC_INSPECTION.json',result)
print(json.dumps(result))
