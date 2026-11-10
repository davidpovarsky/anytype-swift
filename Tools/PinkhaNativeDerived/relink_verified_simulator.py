"""Relink only the changed static Heart into verified simulator Swift products.

The exact command comes from accepted Xcode output. No Swift compiler is run.
All app/module/test/config sources and the complete native header ABI must match
the accepted build. Only simulator ad-hoc signatures are renewed.
"""
import json
from pathlib import Path
import platform
import shutil
import subprocess

from build_custom_heart import command, contains, digest, git


def relink(app, derived, evidence, heart):
    if platform.system() != 'Darwin' or platform.machine() != 'x86_64':
        raise RuntimeError('Real Xcode/macOS simulator linker is required')
    authority = app/'docs/pinkha/torah-integration/evidence/universal-properties-r14/relink/accepted-simulator-link.json'
    accepted = json.loads(authority.read_text())
    baseline = accepted['accepted_swift_source_sha']
    changed = git(app, 'diff', '--name-only', baseline, 'HEAD', '--', 'Anytype', 'Modules',
                  'AnyTypeTests', 'Anytype.xcodeproj', 'Configurations', 'Libraryfile').splitlines()
    if changed:
        raise RuntimeError('Compiled Swift/app/test inputs changed: '+', '.join(changed))
    cached = json.loads((derived/'Build/PinkhaSourceInputs.json').read_text())
    if cached['source_sha'] != baseline:
        raise RuntimeError('The exact accepted Swift cache was not restored')
    old = json.loads((app/'docs/pinkha/torah-integration/evidence/universal-properties-r13/xcode-42740484502/custom-heart-build.json').read_text())
    native = app/'Dependencies/Middleware/Lib.xcframework'
    headers = lambda receipt: {v['path']: v['sha256'] for v in receipt['artifacts']
                               if Path(v['path']).suffix in {'.h', '.modulemap'}}
    if not headers(old) or headers(old) != headers(heart):
        raise RuntimeError('Native header ABI changed; verified Swift objects cannot be reused')
    if old['patch_sha256'] == heart['patch_sha256']:
        raise RuntimeError('Relinking requires a genuinely new native runtime')
    products = derived/'Build/Products/Release-Anytype-iphonesimulator'
    built = products/'Anytype.app'
    before_app = {p: digest(built/p) for p in accepted['accepted_app_binaries']}
    if before_app != accepted['accepted_app_binaries']:
        raise RuntimeError('The simulator app is not the exact accepted Swift build')
    command(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(built)], app, evidence)
    toolchain = subprocess.check_output(['xcodebuild', '-version'], text=True)
    if 'Xcode 26.3' not in toolchain or '17C529' not in toolchain:
        raise RuntimeError('The accepted Xcode toolchain is required')
    argv = accepted['link'][:]
    if (argv[argv.index('-target')+1] != 'x86_64-apple-ios17.0-simulator'
            or '-dynamiclib' not in argv or argv[argv.index('-framework')+1] != 'Lib'):
        # The first framework is Lib in the captured runtime command.
        raise RuntimeError('Unexpected accepted runtime link structure')
    output = Path(argv[argv.index('-o')+1])
    expected = products/'PackageFrameworks/ProtobufMessages.framework/ProtobufMessages'
    if output != expected or not output.is_file():
        raise RuntimeError('Unexpected or missing cached runtime framework output')
    # Verify all response files and the original object list, without rebuilding.
    filelist = Path(argv[argv.index('-filelist')+1])
    objects = [Path(v.strip().strip('"')) for v in filelist.read_text().splitlines() if v.strip()]
    if not objects or any(not p.is_file() or not p.resolve().is_relative_to(derived) for p in objects):
        raise RuntimeError('A verified Swift object is missing or outside DerivedData')
    for value in argv:
        if value.startswith('@') and not Path(value[1:]).is_file():
            raise RuntimeError('Missing accepted linker response file: '+value)
    search = [Path(v[2:]) for v in argv if v.startswith('-F') and len(v)>2]
    candidates = [p/'Lib.framework/Lib' for p in search if (p/'Lib.framework/Lib').is_file()]
    if not candidates:
        raise RuntimeError('Cannot resolve the accepted static Heart link input')
    selected = candidates[0]
    if not selected.resolve().is_relative_to(derived):
        raise RuntimeError('The selected link input is outside verified DerivedData')
    source = native/'ios-arm64_x86_64-simulator/Lib.framework/Lib'
    source_sha = next(v['sha256'] for v in heart['artifacts']
                      if v['path']=='ios-arm64_x86_64-simulator/Lib.framework/Lib')
    if digest(source) != source_sha:
        raise RuntimeError('New static runtime differs from its architecture-verified receipt')
    shutil.copy2(source, selected)
    if digest(selected) != source_sha:
        raise RuntimeError('The linker did not receive the exact new native runtime')
    object_hashes = {str(p.relative_to(derived)): digest(p) for p in objects}
    before_runtime = digest(output)
    link_map = evidence/'native-relink-map.txt'
    argv += ['-Xlinker', '-map', '-Xlinker', str(link_map)]
    command(argv, app, evidence)
    after_runtime = digest(output)
    if before_runtime == after_runtime or digest(selected) != source_sha:
        raise RuntimeError('The changed native runtime was not relinked')
    if str(selected) not in link_map.read_text(errors='replace'):
        raise RuntimeError('Actual linker map does not name the exact selected native archive')
    copied = []
    # XCTest embeds its own framework copies too. Replace every existing copy,
    # but preserve all accepted Swift/app resources and extensions.
    for target in built.rglob('ProtobufMessages.framework/ProtobufMessages'):
        if target.is_symlink() or not target.resolve().is_relative_to(built):
            raise RuntimeError('Unexpected framework symlink outside the accepted app')
        shutil.copy2(output, target)
        if digest(target) != after_runtime:
            raise RuntimeError('An embedded runtime copy differs')
        command(['/usr/bin/codesign', '--force', '--sign', '-', '--timestamp=none',
                 '--preserve-metadata=identifier,entitlements,flags', str(target.parent)], app, evidence)
        copied.append(str(target.relative_to(built)))
    if 'Frameworks/ProtobufMessages.framework/ProtobufMessages' not in copied:
        raise RuntimeError('The real app runtime framework was not updated')
    # Cached test bundle and the app seal the changed nested framework copies.
    for bundle in sorted((built/'PlugIns').glob('*.xctest')):
        command(['/usr/bin/codesign', '--force', '--sign', '-', '--timestamp=none',
                 '--preserve-metadata=identifier,entitlements,flags', str(bundle)], app, evidence)
    command(['/usr/bin/codesign', '--force', '--sign', '-', '--timestamp=none',
             '--preserve-metadata=identifier,entitlements,flags', str(built)], app, evidence)
    command(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(built)], app, evidence)
    if object_hashes != {str(p.relative_to(derived)): digest(p) for p in objects}:
        raise RuntimeError('A cached Swift object changed during runtime linking')
    receipt = dict(status='RELINKED_NEW_HEART_WITH_VERIFIED_SWIFT',
        source_run_id=accepted['source_run_id'], compiled_swift_source_sha=baseline,
        current_source_sha=git(app,'rev-parse','HEAD'), swift_compiler_invoked=False,
        native_patch_sha256=heart['patch_sha256'], unchanged_native_headers=headers(heart),
        native_link_input=str(selected), native_link_input_sha256=source_sha,
        before_runtime_sha256=before_runtime, after_runtime_sha256=after_runtime,
        embedded_runtime_sha256={p:digest(built/p) for p in copied},
        actual_runtime_marker_present=contains(output, heart['marker'].encode()),
        unchanged_swift_objects=object_hashes, updated_runtime_copies=copied,
        accepted_command_sha256=digest(authority), linker_map_sha256=digest(link_map),
        signing='EXISTING_SIMULATOR_ADHOC_ONLY', physical_ipad_verified=False)
    (evidence/'relinked-simulator.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(relinked_runtime=True, reused_swift_objects=len(objects))),flush=True)
