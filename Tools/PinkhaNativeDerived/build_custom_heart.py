"""Build the pinned CUSTOM Heart, preserving source and binary provenance.

Run only after exact owner approval of the supplied patch. Merely passing a hash
does not grant approval. No generated protocols or global Go settings are changed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import urllib.request

PIN = 'd98420b1113536afd08cde6de9a5816f6d27ffff'
TAG = 'v0.51.7-nightly.20261014.1'
BRANCH = 'codex/torah-native-derived-properties-20261103'
NATIVE_REGRESSION_PACKAGES = [
 './core/pinkha/...', './pkg/lib/bundle', './pkg/lib/database',
 './pkg/lib/localstore/objectstore/spaceindex', './core/block/object/objectcreator',
 './core/block/editor/basic', './core/block/editor/smartblock', './core/indexer',
 './core/converter/pbc', './core/converter/pbjson', './core/block/export/anyblock',
 './core/block/object/objectlink', './core/block/simple/dataview',
 './core/block/import', './core/block/import/common', './core/block/import/pb',
]

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def command(argv, cwd, logdir, env=None):
    log = logdir / ('command-%02d.log' % len(list(logdir.glob('command-*.log'))))
    print(json.dumps(dict(command=argv, log=str(log))), flush=True)
    with log.open('w', encoding='utf8') as stream:
        with subprocess.Popen(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              text=True,encoding='utf8',errors='replace',bufsize=1) as process:
            for number,line in enumerate(process.stdout):
                stream.write(line)
                if number % 250 == 0 or 'error:' in line.lower(): print(line.rstrip(),flush=True)
            returncode=process.wait()
    if returncode:
        print(log.read_text(encoding='utf8', errors='replace')[-6000:])
        raise subprocess.CalledProcessError(returncode, argv)

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()

def contains(path, value):
    previous=b''
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            if value in previous+chunk: return True
            previous=chunk[-len(value):]
    return False

def fetch_tantivy(heart, arch):
    hashes={Path(p).name:h for h,p in (line.split() for line in (heart/'tantivity_sha256.txt').read_text().splitlines() if line.strip())}
    archive=heart/'deps/libs'/f'{arch}.tar.gz'
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        urllib.request.urlretrieve(f'https://github.com/anyproto/tantivy-go/releases/download/v1.0.6/{archive.name}',archive)
    if digest(archive)!=hashes[archive.name]: raise RuntimeError('Pinned Tantivy checksum mismatch: '+arch)
    destination=archive.parent/arch
    destination.mkdir(exist_ok=True)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            resolved=(destination/member.name).resolve()
            if not resolved.is_relative_to(destination.resolve()) or not (member.isfile() or member.isdir()):
                raise RuntimeError('Unsafe native archive member')
            if member.isdir(): resolved.mkdir(parents=True, exist_ok=True)
            else:
                resolved.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, resolved.open('wb') as output: shutil.copyfileobj(source,output)
    return dict(architecture=arch,archive_sha256=digest(archive))

def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--heart-source',required=True,type=Path)
    parser.add_argument('--patch',required=True,type=Path)
    parser.add_argument('--inventory',required=True,type=Path)
    parser.add_argument('--approved-patch-sha256',required=True)
    parser.add_argument('--apply-approved-patch',action='store_true')
    parser.add_argument('--target',choices=['verify','linux','ios'],default='verify')
    parser.add_argument('--go',default='go')
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--install-app',type=Path)
    args=parser.parse_args()
    heart=args.heart_source.resolve()
    patch=args.patch.resolve()
    inventory=json.loads(args.inventory.read_text(encoding='utf8'))
    actual=digest(patch)
    if actual!=args.approved_patch_sha256 or actual!=inventory['patch_sha256']: raise RuntimeError('Patch differs from exact approved diff')
    if git(heart,'rev-parse','HEAD')!=PIN: raise RuntimeError('Wrong Heart SHA')
    if args.target=='ios' and platform.system()!='Darwin': raise RuntimeError('Actual Xcode/macOS SDK required for iOS; no source was modified')
    if args.target=='linux' and platform.system()!='Linux': raise RuntimeError('Linux native build requires Linux')
    args.evidence.mkdir(parents=True,exist_ok=True)
    if args.apply_approved_patch:
        if git(heart,'diff','--name-only') or git(heart,'diff','--cached','--name-only'): raise RuntimeError('Refusing to patch dirty Heart')
        command(['git','apply','--check',str(patch)],heart,args.evidence)
        command(['git','apply',str(patch)],heart,args.evidence)
    approved_paths={entry['path'] for entry in inventory['files']}
    for entry in inventory['files']:
        path=heart/entry['path']
        # Git may materialize LF source as CRLF on Windows. The approved patch
        # inventory hashes Git's LF text; binary artifact hashes remain exact.
        if not path.is_file() or hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=entry['after_sha256']:
            raise RuntimeError('Heart does not contain the approved source: '+entry['path'])
    if set(git(heart,'diff','--name-only').splitlines())-approved_paths: raise RuntimeError('Unreviewed Heart changes')
    if git(heart,'diff','--cached','--name-only'): raise RuntimeError('Heart index must stay untouched')
    receipt=dict(heart_sha=PIN,heart_tag=TAG,patch_sha256=actual,target=args.target,files=inventory['files'],status='SOURCE_VERIFIED_BUILD_NOT_RUN')
    receipt_path=args.evidence/'custom-heart-build.json'
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    if args.target=='verify': return
    marker='pinkha-native-derived-v1-'+actual
    ldflags=f'-X github.com/anyproto/anytype-heart/util/vcs.GitSummary={TAG}-{marker} -X github.com/anyproto/anytype-heart/util/vcs.GitCommit={PIN}'
    env=dict(os.environ,CGO_ENABLED='1',GOMAXPROCS='2')
    env.pop('GOWORK',None)
    # Downstream tests exercise the actual original Space store transaction and
    # worker lifecycle. The review patch includes this test-only source; Go
    # excludes it from the shipped framework.
    test_source=Path(__file__).resolve().parent/'native_test_templates/pinkha_torah_fulltext_test.go'
    test_destination=heart/'pkg/lib/localstore/objectstore/spaceindex/pinkha_torah_fulltext_test.go'
    normalized_test=test_source.read_bytes().replace(b'\r\n',b'\n')
    if test_destination.read_bytes().replace(b'\r\n',b'\n')!=normalized_test:
        raise RuntimeError('Applied native acceptance fixture differs from the recorded source')
    receipt['native_test_source_sha256']=hashlib.sha256(normalized_test).hexdigest()
    native=[]
    if args.target=='linux':
        arch='linux-amd64-musl' if platform.machine()=='x86_64' else 'linux-arm64-musl'
        native.append(fetch_tantivy(heart,arch))
        env['CGO_LDFLAGS']='-L'+str(heart/'deps/libs'/arch)
        command([args.go,'test','-p','2',*NATIVE_REGRESSION_PACKAGES],heart,args.evidence,env)
        output=args.evidence.resolve()/'libpinkha-heart.so'
        command([args.go,'build','-p','2','-tags','nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg','-ldflags',ldflags,'-buildmode=c-shared','-o',str(output),'./clientlibrary/clib'],heart,args.evidence,env)
        if not contains(output,marker.encode()): raise RuntimeError('Custom identity missing from native Heart binary')
        receipt['artifacts']=[dict(path=str(output),sha256=digest(output))]
    else:
        command(['xcodebuild','-version'],heart,args.evidence)
        command(['xcrun','--sdk','iphoneos','--show-sdk-version'],heart,args.evidence)
        for arch in ['darwin-arm64','darwin-amd64','ios-arm64','ios-arm64-sim','ios-amd64']: native.append(fetch_tantivy(heart,arch))
        hostarch='darwin-arm64' if platform.machine()=='arm64' else 'darwin-amd64'
        testenv=dict(env,CGO_LDFLAGS='-L'+str(heart/'deps/libs'/hostarch))
        command([args.go,'test','-p','2',*NATIVE_REGRESSION_PACKAGES],heart,args.evidence,testenv)
        (heart/'deps').mkdir(exist_ok=True)
        for tool in ['gomobile','gobind']:
            command([args.go,'build','-o',str(heart/'deps'/tool),'golang.org/x/mobile/cmd/'+tool],heart,args.evidence,env)
        env['PATH']=str(heart/'deps')+os.pathsep+env['PATH']
        command([str(heart/'deps/gomobile'),'init'],heart,args.evidence,env)
        framework=heart/'dist/ios/Lib.xcframework'
        if framework.exists(): raise RuntimeError('Refusing stale framework output; use a fresh isolated build clone')
        framework.parent.mkdir(parents=True,exist_ok=True)
        command([str(heart/'deps/gomobile'),'bind','-tags','nogrpcserver gomobile nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg','-ldflags',ldflags,'-target=ios','-o',str(framework),'github.com/anyproto/anytype-heart/clientlibrary/service','github.com/anyproto/anytype-heart/core'],heart,args.evidence,env)
        command([args.go,'run','cmd/iosrepack/main.go'],heart,args.evidence,env)
        binaries=[path for path in framework.rglob('Lib') if path.is_file()]
        if not binaries or not all(contains(path,marker.encode()) for path in binaries): raise RuntimeError('Custom identity missing in one or more XCFramework slices')
        receipt['artifacts']=[dict(path=str(path.relative_to(framework)),sha256=digest(path)) for path in sorted(framework.rglob('*')) if path.is_file()]
        receipt['framework']=str(framework)
        if args.install_app:
            app=args.install_app.resolve()
            if git(app,'branch','--show-current')!=BRANCH: raise RuntimeError('Wrong application branch')
            if TAG not in (app/'Libraryfile').read_text(): raise RuntimeError('Application middleware pin differs')
            destination=app/'Dependencies/Middleware/Lib.xcframework'
            backup=destination.with_name('Lib.pre-native-'+actual[:12]+'.xcframework')
            if destination.exists():
                if backup.exists(): raise RuntimeError('Existing middleware backup must be preserved')
                destination.rename(backup)
            shutil.copytree(framework,destination)
            receipt['app_base_sha']=git(app,'rev-parse','HEAD')
            receipt['installed_at']=str(destination)
    receipt.update(status='PASS',marker=marker,native_dependencies=native)
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    if args.install_app:
        (args.install_app/'Dependencies/Middleware/PinkhaNativeHeartBuild.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(status='PASS',receipt=str(receipt_path),patch_sha256=actual)))

if __name__=='__main__': main()
