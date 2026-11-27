#!/usr/bin/env python3
"""DRAFT: exact off-host custody of four frozen compressed E products only.

No application, compiler, account or old test runs. All four Windows copies,
Flush(true) acknowledgements and full Oracle streamed readbacks must pass before
any source is retired. Failed transfers retain every source and remote partial.
"""
from pathlib import Path
import base64, ctypes, errno, hashlib, io, json, os, selectors, shutil, signal, stat, subprocess, sys, time, uuid

BLOBS = [
    ('/mnt/development/projects/evidence/pinkha-e-failed-binary-custody-relocated-20261127/retained/attempt2-cutover-core.test.xz', 63324388, 'a42de5bbe39b11191e6157e8a958fd8b5c53874eaabdb300b4449a7528aedd33'),
    ('/mnt/development/projects/evidence/pinkha-e-failed-binary-custody-relocated-20261127/retained/attempt4-cutover-core.test.xz', 63314432, '8f565b8a8e0e6c42b474ca6b6a1ba50a1b73feb1356f66a67ec69ee92d75b587'),
    ('/mnt/development/projects/evidence/pinkha-e-failed-binary-custody-relocated-20261127/retained/attempt5-cutover-core.test.xz', 63326424, '8e81e08b84ce221b2c627e3d916461b637a53b50708fe001fafe1e33e88353b7'),
    ('/mnt/development/projects/evidence/pinkha-e-core40-binary-custody-20261127/cutover-core.test.gz', 81769778, '42cffc27d6a08905966f74828d6741d0abc37be6a486ca669b2837a05f76e4b8'),
]
PINS = {
    '/var/lib/pinkha-root-t2-linux-20261126/build1/current/any': '1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636',
    '/var/lib/pinkha-c-filesv2-20261126/lan-progress-native1/any': '0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07',
    '/mnt/development/projects/caches/pinkha-e-cutover-rpc-core-attempt5-20261127/cutover-core.test': 'bbd8d9f28d7a948684d9771c5b0effe25abb00570ac0383b0324a56cb6ce1f75',
}
CONTROL_PINS = {
    '/mnt/development/projects/evidence/pinkha-e-failed-binary-custody-relocated-20261127/retained/attempt2-completed.json': '9d19390881cd014be2f10b483a778eabaaad6644dde4b38b0120c3bb41f6c73b',
    '/mnt/development/projects/evidence/pinkha-e-failed-binary-custody-relocated-20261127/retained/attempt2-verified-custody.json': '1da7e4578ffb0c95e4494f816cdd4de09c90a790fdfca9210347cb232804e3c8',
    '/mnt/development/projects/evidence/pinkha-e-failed-binary-custody-relocated-20261127/retained/attempt4-completed.json': '3704640d6567bdab3ecd62ea59cf7a086343ea24156fcf0c9d0ec5ca1ba58371',
    '/mnt/development/projects/evidence/pinkha-e-failed-binary-custody-relocated-20261127/retained/attempt4-verified-custody.json': 'acc2c13983d4aca3c7f3cedb1f3f8b757f636e9b0c50ef3bddfa9da78b3151c6',
    '/mnt/development/projects/evidence/pinkha-e-failed-binary-custody-relocated-20261127/retained/attempt5-completed.json': '62ca183b4ce52282bd689ed01eb1bf5b4ec92f8edb3c4686ad878a71d01fd7cc',
    '/mnt/development/projects/evidence/pinkha-e-failed-binary-custody-relocated-20261127/retained/attempt5-verified-custody.json': 'e89748c16bec709ac46d6b21456e552eb44dd56a3d2e791cbebbada1fc8d36cc',
    '/mnt/development/projects/evidence/pinkha-e-failed-binary-custody-relocated-20261127/retained/original-manifest.json': '8534bda6cdd579b7f294f7679bb59899c37dc58486296c44999e1f64d001bea7',
    '/mnt/development/projects/evidence/pinkha-e-failed-binary-custody-relocated-20261127/retained/receipt.json': '5e1843f8943a8c88c82e1b53b97dacc3a6bf5b4cf60923bab083f6d6c4df7ee9',
    '/mnt/development/projects/evidence/pinkha-e-core40-binary-custody-20261127/gzip-original.log': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    '/mnt/development/projects/evidence/pinkha-e-core40-binary-custody-20261127/receipt.json': 'b9fb7c110d2d619522c418122e7d6d582cf754e63b59c4bb5774434966df4d30',
    '/mnt/development/projects/evidence/pinkha-e-core40-binary-custody-20261127/restore.json': '6378a655ec0a8c96c22010e7fef473c597b6fd4c15d0a54c157e2595c545485f',
    '/mnt/development/projects/evidence/pinkha-e-core40-binary-custody-20261127/started.json': '85cf81a5e28eb3efa5209ea9988911c6a164c8a72d9693ea90ae991a606f4eae',
    '/mnt/development/projects/evidence/pinkha-e-core40-binary-custody-20261127/verified-custody-before-retirement.json': 'ba0e83a20c9e46ac045180f6a6a2d258ecb0aa59abe733c840c6fdff51f44bc5',
    '/mnt/development/projects/evidence/pinkha-e-failed-binary-custody-relocated-20261127/relocation-receipt.json': 'f05188217a3b6b4c554dfc4ed88112bd12ac73562bcbb017759f77b3d5e04f2e',
}
WIN_PARENT = r'C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence'
WIN_HOST = 'DAVID_AND_GOLDY'
MIB = 1024**2


def read_noatime(path):
    return os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME), 'rb')


def sha_file(path):
    h = hashlib.sha256()
    with read_noatime(path) as f:
        for chunk in iter(lambda: f.read(MIB), b''): h.update(chunk)
    return h.hexdigest()


def metadata(path):
    s = Path(path).lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'frozen source must be an ordinary unshared inode'
    attrs = {name: base64.b64encode(os.getxattr(path, name, follow_symlinks=False)).decode('ascii')
             for name in sorted(os.listxattr(path, follow_symlinks=False))}
    assert sum(len(k) + len(v) for k, v in attrs.items()) <= MIB
    return {'device': s.st_dev, 'inode': s.st_ino, 'mode': stat.S_IMODE(s.st_mode), 'uid': s.st_uid,
            'gid': s.st_gid, 'bytes': s.st_size, 'allocatedBytes': s.st_blocks * 512, 'links': s.st_nlink,
            'atime_ns': s.st_atime_ns, 'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns, 'xattrs': attrs}


def require_canonical_file(path):
    path = Path(path)
    assert path.is_absolute() and not path.parent.is_symlink() and path.parent.resolve(strict=True) == path.parent
    assert not path.is_symlink() and path.resolve(strict=True) == path


def capture_original_controls():
    captured = {}
    assert len(CONTROL_PINS) == 14  # Eight + five original files, plus parent receipt.
    for path, expected in CONTROL_PINS.items():
        require_canonical_file(path)
        before = metadata(path); actual = sha_file(path)
        assert actual == expected and metadata(path) == before
        captured[path] = {'sha256': actual, 'metadata': before}
    return captured


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def atomic_json(path, value):
    path = Path(path); tmp = path.with_name(path.name + '.writing-' + uuid.uuid4().hex)
    with tmp.open('xb') as f:
        f.write((json.dumps(value, sort_keys=True, indent=2) + '\n').encode()); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path); fsync_dir(path.parent)


def no_live_inodes(paths):
    """Required bounded fd/maps inspection, without reading command lines."""
    targets = {(Path(p).stat().st_dev, Path(p).stat().st_ino): str(p) for p in paths}
    found = []; inspected = 0; deadline = time.monotonic() + 30
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit(): continue
        assert time.monotonic() < deadline, 'bounded no-live inode inspection'
        try:
            for fd in (proc / 'fd').iterdir():
                inspected += 1; assert inspected <= 250000
                try: s = fd.stat()
                except (FileNotFoundError, ProcessLookupError): continue
                if (s.st_dev, s.st_ino) in targets: found.append({'pid': int(proc.name), 'fd': fd.name, 'path': targets[(s.st_dev, s.st_ino)]})
            with (proc / 'maps').open('rb') as f: raw = f.read(4 * MIB + 1)
            assert len(raw) <= 4 * MIB, 'bounded maps inspection'
            for line in raw.splitlines():
                fields = line.split(None, 5)
                if len(fields) < 5 or not fields[4].isdigit(): continue
                major, minor = fields[3].split(b':'); key = (os.makedev(int(major, 16), int(minor, 16)), int(fields[4]))
                if key in targets: found.append({'pid': int(proc.name), 'mapping': True, 'path': targets[key]})
        except (FileNotFoundError, ProcessLookupError): continue
    assert not found, 'frozen source has a live fd or mapping: ' + json.dumps(found)
    return {'fdEntriesInspected': inspected, 'matchingLiveUsers': 0}


def rename_exclusively(source, destination):
    """Linux atomic capture of a pathname; never overwrite quarantine/restore."""
    libc = ctypes.CDLL(None, use_errno=True)
    call = libc.renameat2
    call.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    call.restype = ctypes.c_int
    if call(-100, os.fsencode(source), -100, os.fsencode(destination), 1) != 0:
        code = ctypes.get_errno(); raise OSError(code, os.strerror(code), str(destination))


def install_exclusively(tmp, dst):
    """Same exclusive-link boundary as the four accepted restore race controls."""
    assert tmp.parent == dst.parent
    os.link(tmp, dst, follow_symlinks=False)
    fd = os.open(dst.parent, os.O_RDONLY)
    try:
        os.fsync(fd); tmp.unlink(); os.fsync(fd)
    finally: os.close(fd)


def q(value): return "'" + str(value).replace("'", "''") + "'"


def ps_header(root, token, owned=True):
    code = "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
    code += "if([Environment]::MachineName -cne 'DAVID_AND_GOLDY'){throw 'wrong Windows host'};"
    code += '$r=' + q(root) + ';$t=' + q(token) + ';'
    if owned:
        code += "if(-not [IO.Directory]::Exists($r)){throw 'missing owned root'};if(([IO.File]::GetAttributes($r)-band [IO.FileAttributes]::ReparsePoint)-ne 0){throw 'root reparse point'};"
        code += "$o=[IO.File]::ReadAllText(($r+'\\OWNER.json'))|ConvertFrom-Json;if($o.token-cne $t -or $o.root-cne $r -or $o.host-cne 'DAVID_AND_GOLDY' -or $o.sid-cne [Security.Principal.WindowsIdentity]::GetCurrent().User.Value){throw 'owner mismatch'};"
    return code


def ps_wrap(code): return 'try{' + code + ';exit 0}catch{[Console]::Error.WriteLine($_.Exception.Message);exit 1}'


def ps_create(root, token, reserve):
    code = ps_header(root, token, False) + '$p=' + q(WIN_PARENT) + ';'
    code += "if(-not [IO.Directory]::Exists($p) -or ([IO.File]::GetAttributes($p)-band [IO.FileAttributes]::ReparsePoint)-ne 0){throw 'invalid verified parent'};"
    code += "if([IO.Directory]::Exists($r)-or [IO.File]::Exists($r)){throw 'exclusive root exists'};"
    code += 'if([IO.DriveInfo]::new(\'C\').AvailableFreeSpace-lt ' + str(2 * 1024**3 + reserve) + "){throw 'Windows reserve'};"
    code += "$m=& $env:ComSpec /D /C ('mkdir \"'+$r+'\"') 2>&1;if($LASTEXITCODE-ne 0){throw ('exclusive mkdir failed: '+$m)};"
    code += "$owner=@{token=$t;root=$r;host=[Environment]::MachineName;sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value};"
    code += "$b=[Text.UTF8Encoding]::new($false).GetBytes(($owner|ConvertTo-Json -Compress));$f=[IO.File]::Open(($r+'\\OWNER.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);try{$f.Write($b,0,$b.Length);$f.Flush($true)}finally{$f.Dispose()};"
    code += '[Console]::Out.WriteLine(($owner|ConvertTo-Json -Compress))'
    return ps_wrap(code)


def ps_upload(root, token, name, size, digest, remaining):
    assert name and all(c.isalnum() or c in '._-' for c in name)
    code = ps_header(root, token) + '$p=$r+' + q('\\' + name) + ';$n=' + str(size) + ';'
    code += 'if([IO.DriveInfo]::new(\'C\').AvailableFreeSpace-lt ' + str(2 * 1024**3 + remaining) + "){throw 'Windows remaining-byte reserve'};"
    code += "$f=[IO.FileStream]::new($p,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None,65536,[IO.FileOptions]::WriteThrough);$i=[Console]::OpenStandardInput();$b=New-Object byte[] 65536;$total=0L;$sw=[Diagnostics.Stopwatch]::StartNew();"
    code += "try{while($total-lt $n){$left=240000-[int]$sw.ElapsedMilliseconds;if($left-le 0){throw 'receiver deadline'};$task=$i.ReadAsync($b,0,[int][Math]::Min(65536,$n-$total));if(-not $task.Wait($left)){throw 'receiver read deadline'};$got=$task.Result;if($got-le 0){throw 'truncated stdin'};$f.Write($b,0,$got);$total+=$got};"
    code += "$last=$i.ReadAsync($b,0,1);if(-not $last.Wait(10000)-or $last.Result-ne 0){throw 'extra bytes or missing EOF'};$f.Flush($true)}finally{$f.Dispose();$i.Dispose()};"
    code += "$s=[IO.File]::Open($p,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read);try{$h=[Security.Cryptography.SHA256]::Create();$actual=[BitConverter]::ToString($h.ComputeHash($s)).Replace('-','').ToLowerInvariant()}finally{$s.Dispose();$h.Dispose()};"
    code += 'if($actual-cne ' + q(digest) + " -or [IO.FileInfo]::new($p).Length-ne $n){throw 'stored hash/length mismatch'};[IO.File]::SetAttributes($p,[IO.FileAttributes]::ReadOnly);"
    code += "[Console]::Out.WriteLine((@{host=[Environment]::MachineName;root=$r;token=$t;name=" + q(name) + ";bytes=$total;sha256=$actual;flushToDisk=$true;createNew=$true;readOnly=$true}|ConvertTo-Json -Compress))"
    return ps_wrap(code)


def ps_readback(root, token, name, size):
    code = ps_header(root, token) + '$p=$r+' + q('\\' + name) + ';'
    code += "if(([IO.File]::GetAttributes($p)-band [IO.FileAttributes]::ReparsePoint)-ne 0){throw 'file reparse point'};"
    code += '$f=[IO.File]::Open($p,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read);try{if($f.Length-ne ' + str(size) + "){throw 'readback length'};$o=[Console]::OpenStandardOutput();$task=$f.CopyToAsync($o,65536);if(-not $task.Wait(240000)){throw 'readback deadline'};$o.Flush()}finally{$f.Dispose()}"
    return ps_wrap(code)


def ps_sftp_admit(root, token, name, size, remaining):
    assert name and len(name)<=128 and all(c.isalnum() or c in '._-' for c in name)
    code=ps_header(root,token)+'$p=$r+'+q('\\'+name)+';'
    code+="if([IO.File]::Exists($p)-or [IO.Directory]::Exists($p)){throw 'exclusive SFTP target already exists'};"
    code+="$free=[IO.DriveInfo]::new('C').AvailableFreeSpace;if($free-lt "+str(2*1024**3+remaining)+"){throw 'Windows remaining-byte reserve'};"
    code+="[Console]::Out.WriteLine((@{host=[Environment]::MachineName;root=$r;token=$t;name="+q(name)+";bytes="+str(size)+";destinationAbsent=$true;availableFreeBytes=$free}|ConvertTo-Json -Compress))"
    return ps_wrap(code)


def ps_sftp_seal(root, token, name, size, digest):
    assert name and len(name)<=128 and all(c.isalnum() or c in '._-' for c in name)
    code=ps_header(root,token)+'$p=$r+'+q('\\'+name)+';$n='+str(size)+';'
    code+="if(([IO.File]::GetAttributes($p)-band ([IO.FileAttributes]::ReparsePoint -bor [IO.FileAttributes]::Directory))-ne 0){throw 'SFTP target must be an ordinary file'};"
    code+="if([IO.FileInfo]::new($p).Length-ne $n){throw 'SFTP stored size'};"
    code+="$f=[IO.File]::Open($p,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);$h=$null;try{$f.Flush($true);$h=[Security.Cryptography.SHA256]::Create();$actual=[BitConverter]::ToString($h.ComputeHash($f)).Replace('-','').ToLowerInvariant()}finally{$f.Dispose();if($h){$h.Dispose()}};"
    code+='if($actual-cne '+q(digest)+"){throw 'SFTP stored hash'};"
    code+="if([IO.DriveInfo]::new('C').AvailableFreeSpace-lt "+str(2*1024**3)+"){throw 'Windows seal reserve'};[IO.File]::SetAttributes($p,[IO.FileAttributes]::ReadOnly);"
    code+="[Console]::Out.WriteLine((@{host=[Environment]::MachineName;root=$r;token=$t;name="+q(name)+";bytes=$n;sha256=$actual;flushToDisk=$true;sealedClosedSFTPFile=$true;readOnly=$true}|ConvertTo-Json -Compress))"
    return ps_wrap(code)


def ssh_stream(code, label, save, guard, rows, source=None, expected_size=None, expected_sha=None, destination=None):
    """One bounded dedicated SSH process; raw file bytes never enter receipts."""
    encoded = base64.b64encode(code.encode('utf-16le')).decode('ascii')
    assert len(encoded) < 7600, 'bounded Windows command line'
    command = ['sudo','-n','-u','ubuntu','ssh','-T','-o','StrictHostKeyChecking=yes','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=2','-o','ControlMaster=no','-o','ControlPath=none','-o','ControlPersist=no','david-win','powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',encoded]
    row = {'label': label, 'powershellSHA256': hashlib.sha256(code.encode()).hexdigest(), 'forcedCleanup': False, 'status': 'DISPATCH_INTENT'}
    rows.append(row); save()
    reader = None; sink = None
    p = None; stdout = bytearray(); stderr = bytearray(); sent = 0; received = 0; input_hash = hashlib.sha256(); output_hash = hashlib.sha256(); pending = b''; began = time.monotonic()
    try:
        reader = read_noatime(source) if isinstance(source, Path) else io.BytesIO(source) if source is not None else None
        sink = destination.open('xb') if destination is not None else None
        p = subprocess.Popen(command, stdin=subprocess.PIPE if reader is not None else subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, bufsize=0)
        row['pid'] = p.pid; save()
        with selectors.DefaultSelector() as selector:
            for stream, kind in [(p.stdout, 'out'), (p.stderr, 'err')]: os.set_blocking(stream.fileno(), False); selector.register(stream, selectors.EVENT_READ, kind)
            if reader is not None: os.set_blocking(p.stdin.fileno(), False); selector.register(p.stdin, selectors.EVENT_WRITE, 'in')
            while selector.get_map():
                guard(); assert time.monotonic() - began < 260, 'bounded SSH stream deadline'
                for key, _ in selector.select(.2):
                    if key.data == 'in':
                        if not pending:
                            pending = reader.read(65536)
                            if pending: input_hash.update(pending)
                            else: selector.unregister(key.fileobj); key.fileobj.close(); continue
                        try: count = os.write(key.fd, pending)
                        except BlockingIOError: continue
                        pending = pending[count:]; sent += count
                    else:
                        try: data = os.read(key.fd, 65536)
                        except BlockingIOError: continue
                        if not data: selector.unregister(key.fileobj); key.fileobj.close(); continue
                        if key.data == 'err': stderr.extend(data); assert len(stderr) <= 131072
                        else:
                            received += len(data)
                            if expected_sha is not None:
                                assert received <= expected_size, 'readback exceeded exact length'
                                output_hash.update(data)
                                if sink is not None: sink.write(data)
                            else: stdout.extend(data); assert len(stdout) <= 131072
        p.wait(timeout=10)
        try: os.killpg(p.pid, 0); absent = False
        except ProcessLookupError: absent = True
        row.update(exitCode=p.returncode, groupPositivelyAbsent=absent)
        assert p.returncode == 0 and absent, 'SSH command did not terminate cleanly'
        if source is not None: row.update(inputBytes=sent, inputSHA256=input_hash.hexdigest())
        if expected_sha is not None:
            assert received == expected_size and output_hash.hexdigest() == expected_sha, 'full streamed readback mismatch'
            row.update(readbackBytes=received, readbackSHA256=output_hash.hexdigest())
        if sink is not None: sink.flush(); os.fsync(sink.fileno())
        row['status'] = 'PASS'
    except BaseException as error:
        row.update(status='FAIL', errorType=type(error).__name__, error=str(error))
        raise
    finally:
        if reader is not None: reader.close()
        if sink is not None: sink.close()
        if p is not None:
            try:
                # Once positively absent, never signal that historical PGID.
                alive = False
                if not row.get('groupPositivelyAbsent'):
                    p.poll()
                    try: os.killpg(p.pid, 0); alive = True
                    except ProcessLookupError: pass
                if alive:
                    row['forcedCleanup'] = True
                    for sig in (signal.SIGTERM, signal.SIGKILL):
                        try: os.killpg(p.pid, sig)
                        except ProcessLookupError: alive = False; break
                        deadline = time.monotonic() + 5
                        while time.monotonic() < deadline:
                            p.poll()
                            try: os.killpg(p.pid, 0)
                            except ProcessLookupError: alive = False; break
                            time.sleep(.05)
                        if not alive: break
                row['groupPositivelyAbsent'] = not alive
                row['exitCode'] = p.returncode
            except BaseException as cleanup_error:
                row.update(status='FAIL', groupPositivelyAbsent=False,
                           cleanupErrorType=type(cleanup_error).__name__, cleanupError=str(cleanup_error))
            finally:
                for stream in (p.stdin, p.stdout, p.stderr):
                    if stream is not None and not stream.closed:
                        try: stream.close()
                        except OSError as close_error: row.update(status='FAIL', streamCloseError=str(close_error))
        row.update(seconds=round(time.monotonic()-began,3), stderr=stderr.decode('utf-8','replace'))
        if p is None: row.update(processStarted=False, groupPositivelyAbsent=True)
        if row['forcedCleanup'] or not row.get('groupPositivelyAbsent'): row['status'] = 'FAIL'
        save()
    assert row['status']=='PASS' and row.get('groupPositivelyAbsent') and not row['forcedCleanup'] and row['exitCode']==0, 'SSH lifecycle was not a clean success'
    return bytes(stdout)


"""Finite SFTPv3 exclusive-file writer over the already pinned SSH alias.

Protocol framing: IETF draft-ietf-secsh-filexfer-02, sections 3, 4, 6.3,
6.4 and 7. No SSH credentials are read. No rename, removal, truncation,
attribute change, directory scan, or general SFTP operation is implemented.
"""
import hashlib,io,os,re,selectors,signal,struct,subprocess,time
from pathlib import Path


def sftp_upload(path, source, expected_size, expected_sha, label, save, guard, rows):
    """CREATE|WRITE|EXCL, <=8 outstanding 32KiB writes, correlated status."""
    allowed=r'C:\\Users\\DAVID\\AppData\\Local\\SentinelX\\anytapy-immutable-evidence\\(?:pinkha-frozen-e-20261127-|pinkha-root-closed-builds-20261127-)[0-9a-f]{32}\\[A-Za-z0-9][A-Za-z0-9._-]{0,127}'
    assert re.fullmatch(allowed,path) and '..' not in path and expected_size>=0
    command=['sudo','-n','-u','ubuntu','ssh','-T','-o','StrictHostKeyChecking=yes','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=2','-o','ControlMaster=no','-o','ControlPath=none','-o','ControlPersist=no','-s','david-win','sftp']
    row={'label':label,'transport':'sftp-v3','openFlags':42,'maximumWriteBytes':32768,'maximumOutstandingWrites':8,'status':'DISPATCH_INTENT','forcedCleanup':False,'sourceBytesRead':0,'writeBytesAcknowledged':0,'writeStatusesAcknowledged':0,'closeConfirmed':False}
    rows.append(row);save()
    p=None;reader=None;own_reader=False;selector=None;output=bytearray();stderr=bytearray();pending={};started=time.monotonic();input_hash=hashlib.sha256()
    stdout_eof=False;next_id=1
    def bounded():guard();assert time.monotonic()-started<260,'bounded SFTP operation deadline'
    def parse_string(data,at,maximum=65536):
        assert at+4<=len(data),'truncated SFTP string length'
        size=struct.unpack_from('>I',data,at)[0];at+=4
        assert size<=maximum and at+size<=len(data),'bounded SFTP string'
        return data[at:at+size],at+size
    def s(value):return struct.pack('>I',len(value))+value
    def read_event(key):
        nonlocal stdout_eof
        try:data=os.read(key.fd,65536)
        except BlockingIOError:return
        if not data:
            selector.unregister(key.fileobj);key.fileobj.close()
            if key.data=='out':stdout_eof=True
            return
        if key.data=='out':output.extend(data);assert len(output)<=2*1024**2,'bounded SFTP receive buffer'
        else:stderr.extend(data);assert len(stderr)<=131072,'bounded SFTP stderr'
    def send(kind,payload):
        bounded();frame=struct.pack('>IB',len(payload)+1,kind)+payload
        assert len(frame)<=65536,'bounded SFTP outgoing packet'
        view=memoryview(frame);done=0
        selector.register(p.stdin,selectors.EVENT_WRITE,'in')
        try:
            while done<len(view):
                bounded();assert not stdout_eof,'SFTP closed before complete request dispatch'
                for key,_ in selector.select(.1):
                    if key.data=='in':
                        try:wrote=os.write(key.fd,view[done:])
                        except BlockingIOError:continue
                        assert wrote>0;done+=wrote
                    else:read_event(key)
        finally:selector.unregister(p.stdin)
    def receive():
        while True:
            bounded()
            if len(output)>=4:
                size=struct.unpack_from('>I',output,0)[0]
                assert 1<=size<=1024**2,'bounded SFTP incoming packet'
                if len(output)>=4+size:
                    packet=bytes(output[4:4+size]);del output[:4+size];return packet
            assert not stdout_eof,'truncated SFTP response/early EOF'
            for key,_ in selector.select(.1):read_event(key)
    def status(packet):
        assert len(packet)>=9 and packet[0]==101,'expected typed SFTP STATUS'
        request_id,code=struct.unpack_from('>II',packet,1)
        message,at=parse_string(packet,9);language,at=parse_string(packet,at,1024)
        assert at==len(packet),'trailing SFTP STATUS data'
        if code:
            row['lastServerError']={'requestId':request_id,'code':code,'message':message.decode('utf-8','replace'),'language':language.decode('ascii','replace')}
        return request_id,code
    try:
        if isinstance(source,Path):
            reader=os.fdopen(os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME),'rb');own_reader=True;row['sourceKind']='ordinary-file'
        elif isinstance(source,(bytes,bytearray)):
            reader=io.BytesIO(source);own_reader=True;row['sourceKind']='in-memory-bytes'
        else:
            assert callable(getattr(source,'read',None)),'only a supplied bounded read stream is accepted'
            reader=source;row['sourceKind']='borrowed-bounded-read-stream';row['producerLifecycleOwnedByCaller']=True
        bounded();p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,bufsize=0)
        row['pid']=p.pid;save();selector=selectors.DefaultSelector()
        for stream,kind in ((p.stdout,'out'),(p.stderr,'err')):os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,kind)
        os.set_blocking(p.stdin.fileno(),False)
        send(1,struct.pack('>I',3));packet=receive()
        assert len(packet)>=5 and packet[0]==2 and struct.unpack_from('>I',packet,1)[0]==3,'SFTP version3 required'
        at=5;extensions=[]
        while at<len(packet):
            name,at=parse_string(packet,at,4096);_,at=parse_string(packet,at,65536)
            extensions.append(name.decode('ascii','replace'));assert len(extensions)<=64
        row['negotiatedVersion']=3;row['advertisedExtensionNames']=extensions
        # No READ, APPEND or TRUNC bit: existing destinations must fail.
        open_id=next_id;next_id+=1
        send(3,struct.pack('>I',open_id)+s(path.replace('\\','/').encode('utf-8'))+struct.pack('>II',42,0))
        packet=receive()
        if packet[0]==101:
            response_id,code=status(packet);assert response_id==open_id
            raise RuntimeError('SFTP exclusive OPEN refused with status '+str(code))
        assert packet[0]==102 and len(packet)>=9 and struct.unpack_from('>I',packet,1)[0]==open_id,'correlated SFTP HANDLE required'
        handle,at=parse_string(packet,5,256);assert handle and at==len(packet)
        row['exclusiveOpenConfirmed']=True;row['phase']='writing';save()
        offset=0;highest_outstanding=0
        while offset<expected_size or pending:
            while offset<expected_size and len(pending)<8:
                want=min(32768,expected_size-offset);assembled=bytearray()
                while len(assembled)<want:
                    bounded();piece=reader.read(want-len(assembled))
                    assert isinstance(piece,(bytes,bytearray)) and 0<len(piece)<=want-len(assembled),'source ended before pinned size or exceeded bounded read'
                    assembled.extend(piece)
                chunk=bytes(assembled)
                input_hash.update(chunk);request_id=next_id;next_id+=1
                pending[request_id]=(offset,len(chunk));row['sourceBytesRead']+=len(chunk)
                row.update(lastWriteRequestId=request_id,lastWriteOffset=offset)
                send(6,struct.pack('>I',request_id)+s(handle)+struct.pack('>Q',offset)+s(chunk))
                offset+=len(chunk);row['writeBytesDispatched']=offset
                highest_outstanding=max(highest_outstanding,len(pending))
            request_id,code=status(receive())
            assert request_id in pending,'unknown/duplicate SFTP write response id'
            assert code==0,'SFTP write rejected; existing partial retained'
            _,length=pending.pop(request_id);row['writeBytesAcknowledged']+=length;row['writeStatusesAcknowledged']+=1
        assert reader.read(1)==b'' and offset==expected_size and input_hash.hexdigest()==expected_sha,'complete pinned source hash/length required'
        row.update(inputBytes=offset,inputSHA256=input_hash.hexdigest(),actualMaximumOutstandingWrites=highest_outstanding)
        close_id=next_id
        send(4,struct.pack('>I',close_id)+s(handle));response_id,code=status(receive())
        assert response_id==close_id and code==0,'correlated successful SFTP CLOSE required'
        row['closeConfirmed']=True;row['phase']='closed';p.stdin.close()
        while selector.get_map():
            bounded()
            for key,_ in selector.select(.1):read_event(key)
        assert not output,'unexpected response after final CLOSE'
        p.wait(timeout=5)
        try:os.killpg(p.pid,0);absent=False
        except ProcessLookupError:absent=True
        row.update(exitCode=p.returncode,groupPositivelyAbsent=absent)
        assert p.returncode==0 and absent,'SFTP SSH group must exit cleanly'
        assert row['writeBytesAcknowledged']==expected_size
        row['status']='PASS'
    except BaseException as error:
        row.update(status='FAIL',errorType=type(error).__name__,error=str(error));raise
    finally:
        if reader is not None and own_reader:reader.close()
        if selector is not None:selector.close()
        if p is not None:
            try:
                if p.stdin is not None and not p.stdin.closed:p.stdin.close()
                if not row.get('groupPositivelyAbsent'):
                    try:p.wait(timeout=1)
                    except subprocess.TimeoutExpired:pass
                    try:os.killpg(p.pid,0);alive=True
                    except ProcessLookupError:alive=False
                    if alive:
                        row['forcedCleanup']=True
                        for sig in (signal.SIGTERM,signal.SIGKILL):
                            try:os.killpg(p.pid,sig)
                            except ProcessLookupError:alive=False;break
                            deadline=time.monotonic()+5
                            while time.monotonic()<deadline:
                                p.poll()
                                try:os.killpg(p.pid,0)
                                except ProcessLookupError:alive=False;break
                                time.sleep(.05)
                            if not alive:break
                    row['groupPositivelyAbsent']=not alive
                row['exitCode']=p.returncode
            except BaseException as error:row.update(status='FAIL',groupPositivelyAbsent=False,cleanupError=str(error))
            finally:
                for stream in (p.stdin,p.stdout,p.stderr):
                    if stream is not None and not stream.closed:
                        try:stream.close()
                        except OSError as error:row.update(status='FAIL',streamCloseError=str(error))
        else:row.update(processStarted=False,groupPositivelyAbsent=True)
        if row['forcedCleanup'] or not row.get('groupPositivelyAbsent'):row['status']='FAIL'
        row.update(seconds=round(time.monotonic()-started,3),sourceSHA256Observed=input_hash.hexdigest(),unacknowledgedWriteRequests=len(pending),stderr=stderr.decode('utf-8','replace'))
        save()
    assert row['status']=='PASS' and row['groupPositivelyAbsent'] and not row['forcedCleanup'] and row['exitCode']==0
    return row


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True); parser.add_argument('--oracle-hostname', required=True)
    args = parser.parse_args()
    if sys.flags.optimize: raise RuntimeError('acceptance assertions must remain enabled')
    assert os.geteuid() == 0 and os.uname().nodename == args.oracle_hostname
    out = args.output; assert out.is_absolute() and out.parent.resolve() == out.parent and str(out).startswith('/var/lib/pinkha-w1-offhost-custody-20261127/')
    os.umask(0o077); out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic(); initial_free = shutil.disk_usage('/var/lib').free; token = uuid.uuid4().hex
    remote_root = WIN_PARENT + '\\pinkha-frozen-e-20261127-' + token
    result = {'protocol': 'four-frozen-compressed-native-offhost-custody-v1', 'status': 'RUNNING', 'token': token, 'windowsRoot': remote_root, 'windowsHost': WIN_HOST, 'commands': [], 'blobs': [], 'retirements': [], 'errors': [], 'accountOpens': 0, 'compilerRuns': 0, 'nativeRuns': 0, 'originalTestReruns': 0, 'originalReceiptOrRestoreFileWrites': 0}
    def save(): result['seconds'] = round(time.monotonic()-started,3); atomic_json(out/'result.json', result)
    def guard():
        assert time.monotonic()-started < 1800, 'bounded complete custody operation'
        free = shutil.disk_usage('/var/lib').free; result['minimumRootFreeBytes'] = min(result.get('minimumRootFreeBytes',free), free)
        result['observedGlobalRootFreeDeltaBytes'] = free-initial_free
        assert free >= 256*MIB, 'recovery-only absolute emergency root floor'
        assert not (out/'abort').exists(), 'owned recovery abort'
        allocated = sum(p.stat().st_blocks*512 for p in out.iterdir() if p.is_file())
        result['ownedOutputAllocatedBytes'] = allocated
        assert allocated <= 4*MIB, 'bounded owned root control records'
    def interrupted(*_): raise RuntimeError('owned frozen-blob recovery interrupted')
    signal.signal(signal.SIGTERM, interrupted); signal.signal(signal.SIGINT, interrupted); signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
    def remote(code,label,**kwargs): return ssh_stream(code,label,save,guard,result['commands'],**kwargs)
    def upload_verified(name, data, length, digest, remaining):
        admitted=json.loads(remote(ps_sftp_admit(remote_root,token,name,length,remaining),'admit-sftp-'+name))
        assert admitted['host']==WIN_HOST and admitted['root']==remote_root and admitted['token']==token and admitted['name']==name
        assert admitted['bytes']==length and admitted['destinationAbsent'] is True and admitted['availableFreeBytes']>=2*1024**3+remaining
        sent=sftp_upload(remote_root+'\\'+name,data,length,digest,'sftp-upload-'+name,save,guard,result['commands'])
        assert sent['exclusiveOpenConfirmed'] and sent['openFlags']==42 and sent['closeConfirmed'] and sent['writeBytesAcknowledged']==length
        assert sent['inputBytes']==length and sent['inputSHA256']==digest
        ack=json.loads(remote(ps_sftp_seal(remote_root,token,name,length,digest),'flush-and-seal-'+name))
        assert ack['host']==WIN_HOST and ack['root']==remote_root and ack['token']==token and ack['name']==name
        assert ack['bytes']==length and ack['sha256']==digest and ack['flushToDisk'] is True and ack['sealedClosedSFTPFile'] is True and ack['readOnly'] is True
        ack.update(createNew=True,creationTransport='sftp-v3',exclusiveOpenFlags=sent['openFlags'],sftpCloseConfirmed=True)
        remote(ps_readback(remote_root,token,name,length),'readback-'+name,expected_size=length,expected_sha=digest)
        return ack
    try:
        guard(); result['resourcePolicy']={'recoveryOnly':True,'recoveryEmergencyRootFloorBytes':256*MIB,'initialGlobalRootFreeBytes':initial_free,'globalFreeDeltaAuditedButNotAttributedToOwnedWrites':True,'rootControlAllocationCapBytes':4*MIB,'newLargeBytesOnWindowsOnly':True,'unchangedNativeRootFloorBytes':2*1024**3,'unchangedNativeDevelopmentFloorBytes':512*MIB}
        assert all(len(d)==64 for _,_,d in BLOBS)
        result['nativePinsBefore']={p:sha_file(p) for p in PINS}; assert result['nativePinsBefore']==PINS
        result['originalControlFilesBefore']=capture_original_controls()
        result['originalDirectoryMtimeEqualityClaimed']=False
        for source, size, digest in BLOBS:
            p=Path(source); require_canonical_file(p)
            before=metadata(p); assert before['bytes']==size and sha_file(p)==digest and metadata(p)==before
            result['blobs'].append({'source':source,'name':p.name,'bytes':size,'sha256':digest,'metadata':before,'windowsPath':remote_root+'\\'+p.name})
        result['noLiveBefore']=no_live_inodes([p for p,_,_ in BLOBS]); save()
        # Exercise the exclusive rename primitive only on tiny disposable data.
        a=out/'rename-probe-a';b=out/'rename-probe-b';a.write_bytes(b'A');b.write_bytes(b'B')
        try: rename_exclusively(a,b); raise AssertionError('exclusive rename overwrote destination')
        except OSError as error: assert error.errno==errno.EEXIST
        assert a.read_bytes()==b'A' and b.read_bytes()==b'B';b.unlink();rename_exclusively(a,b);assert not a.exists() and b.read_bytes()==b'A';b.unlink();fsync_dir(out)
        result['exclusiveRenameDisposableControl']='PASS';save()
        total=sum(size for _,size,_ in BLOBS)
        probe=bytes(range(256))*4097+b'\x00\x1a\r\n\xffEND'; probe_sha=hashlib.sha256(probe).hexdigest()
        owner=json.loads(remote(ps_create(remote_root,token,total+len(probe)+MIB),'create-exclusive-windows-root'))
        assert owner['root']==remote_root and owner['token']==token and owner['host']==WIN_HOST; result['windowsOwner']=owner;save()
        result['tinyBinaryRoundtrip']=upload_verified('transport-probe.bin',probe,len(probe),probe_sha,total+len(probe)+MIB);save()
        script=Path(__file__).read_bytes(); restore=Path(__file__).with_name('restore_offhost_frozen_blob.py').read_bytes()
        manifest={'protocol':'four-frozen-compressed-native-restoration-map-v1','token':token,'windowsRoot':remote_root,'windowsHost':WIN_HOST,'blobs':result['blobs'],'controllerSHA256':hashlib.sha256(script).hexdigest(),'restoreHelperSHA256':hashlib.sha256(restore).hexdigest(),'nativePins':PINS,'originalControlFilePins':CONTROL_PINS,'oldBlobPathsWillBeAbsent':True,'restorePrerequisite':'Restore the exact compressed blob to its exact original Oracle path before invoking its existing native-product restore script. No stable old blob path is promised after retirement.','metadataRestored':['mode','uid','gid','atime_ns','mtime_ns','xattrs'],'inodeDeviceCtimeRecordedButNotRecreatable':True}
        atomic_json(out/'restoration-map.json',manifest)
        result['restorationMapSHA256']=sha_file(out/'restoration-map.json');save()
        for name,data in [('offhost_frozen_blobs.py',script),('restore_offhost_frozen_blob.py',restore),('restoration-map.json',(out/'restoration-map.json').read_bytes())]:
            if name != 'restoration-map.json':
                with (out/name).open('xb') as f: f.write(data);f.flush();os.fsync(f.fileno())
            else: assert (out/name).read_bytes()==data
            upload_verified(name,data,len(data),hashlib.sha256(data).hexdigest(),total+MIB)
        remaining=total
        for row in result['blobs']:
            guard(); p=Path(row['source']); assert metadata(p)==row['metadata'] and sha_file(p)==row['sha256']
            row['windowsAcknowledgement']=upload_verified(row['name'],p,row['bytes'],row['sha256'],remaining+MIB)
            assert metadata(p)==row['metadata']; row['fullOracleReadbackVerified']=True;remaining-=row['bytes'];save()
        assert all(x['fullOracleReadbackVerified'] for x in result['blobs'])
        assert all(x.get('status')=='PASS' and x.get('groupPositivelyAbsent') and not x['forcedCleanup'] and x['exitCode']==0 for x in result['commands'])
        # A second complete streamed read of all four copies is the final remote
        # custody barrier. No source has been moved or unlinked before this.
        for row in result['blobs']:
            remote(ps_readback(remote_root,token,row['name'],row['bytes']),'final-readback-'+row['name'],expected_size=row['bytes'],expected_sha=row['sha256'])
        assert {p:sha_file(p) for p in PINS}==PINS
        result['noLiveBeforeRetirement']=no_live_inodes([p for p,_,_ in BLOBS])
        ready={'protocol':'four-frozen-native-remote-custody-ready-v1','allFourVerified':True,'restorationMapSHA256':sha_file(out/'restoration-map.json'),'blobs':[{'name':x['name'],'bytes':x['bytes'],'sha256':x['sha256']} for x in result['blobs']],'originalPathsUnavailableAfterRetirement':True}
        atomic_json(out/'READY-TO-RETIRE.json',ready); data=(out/'READY-TO-RETIRE.json').read_bytes()
        upload_verified('READY-TO-RETIRE.json',data,len(data),hashlib.sha256(data).hexdigest(),MIB);fsync_dir(out)
        assert all(x.get('status')=='PASS' and x.get('groupPositivelyAbsent') and not x['forcedCleanup'] and x['exitCode']==0 for x in result['commands'])
        result['allFourRemoteCustodyBarrierPassedBeforeFirstRetirement']=True;save()
        for row in result['blobs']:
            guard(); source=Path(row['source']); require_canonical_file(source)
            assert metadata(source)==row['metadata'] and sha_file(source)==row['sha256']
            quarantine=source.with_name(source.name+'.custody-'+token)
            entry={'source':str(source),'quarantine':str(quarantine),'sha256':row['sha256'],'stage':'exclusive-capture-intent'};result['retirements'].append(entry);save()
            rename_exclusively(source,quarantine);fsync_dir(source.parent);entry['stage']='captured';save()
            try:
                require_canonical_file(quarantine)
                actual=metadata(quarantine); expected=row['metadata']
                assert {k:v for k,v in actual.items() if k!='ctime_ns'}=={k:v for k,v in expected.items() if k!='ctime_ns'}
                assert sha_file(quarantine)==row['sha256']
                entry['noLiveCaptured']=no_live_inodes([quarantine]);assert metadata(quarantine)==actual
                quarantine.unlink();fsync_dir(source.parent)
                entry.update(stage='retired-verified-duplicate',sourceAbsent=not source.exists() and not source.is_symlink(),allocatedBytesRecovered=expected['allocatedBytes']);save()
                assert entry['sourceAbsent'], 'unexpected new file at frozen original path'
            except BaseException:
                if quarantine.exists():
                    try: rename_exclusively(quarantine,source);fsync_dir(source.parent);entry['rollback']='restored-original-name-exclusively'
                    except OSError as error: entry['rollback']='preserved-quarantine-no-overwrite';entry['rollbackError']=str(error)
                save();raise
        assert len(result['retirements'])==4 and all(x['stage']=='retired-verified-duplicate' for x in result['retirements'])
        result['nativePinsAfter']={p:sha_file(p) for p in PINS};assert result['nativePinsAfter']==PINS
        result['allocatedDevelopmentBytesRecovered']=sum(x['allocatedBytesRecovered'] for x in result['retirements'])
        result['status']='PASS_FOUR_BLOBS_OFFHOST_CUSTODY_AND_DUPLICATE_RETIREMENT_NO_NATIVE_ACCEPTANCE'
    except BaseException as error:
        result['status']='FAIL_OFFHOST_CUSTODY';result['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        try:
            result['originalControlFilesAfter']=capture_original_controls()
            result['originalControlFilesUnchanged']=result['originalControlFilesAfter']==result.get('originalControlFilesBefore')
            assert result['originalControlFilesUnchanged']
            result['nativePinsFinal']={p:sha_file(p) for p in PINS};assert result['nativePinsFinal']==PINS
        except BaseException as final_error:
            result['status']='FAIL_OFFHOST_CUSTODY'
            result['errors'].append({'type':type(final_error).__name__,'message':'final frozen-control/native integrity: '+str(final_error)})
        result['allOwnedSSHGroupsAbsent']=all(x.get('groupPositivelyAbsent') for x in result['commands'])
        if not result['allOwnedSSHGroupsAbsent']: result['status']='FAIL_OFFHOST_CUSTODY'
        result['retiredBlobCount']=sum(x['stage']=='retired-verified-duplicate' for x in result['retirements'])
        result['retirementRequiredAllFourSuccessfulUploadsAndTwoCompleteReadbacks']=True
        result['noSourceRetiredBeforeCompleteRemoteBarrier']=not result['retiredBlobCount'] or result.get('allFourRemoteCustodyBarrierPassedBeforeFirstRetirement') is True
        save()
    print(json.dumps({'status':result['status'],'receipt':str(out/'result.json'),'sha256':sha_file(out/'result.json'),'retired':result['retiredBlobCount'],'seconds':result['seconds']}))
    return 0 if result['status'].startswith('PASS') else 1


if __name__=='__main__': raise SystemExit(main())
