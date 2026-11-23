"""Repair the diagnostic consumer's observed iOS 27 UIScene launch failure.

The already built Firebase provider and every original resource remain exact.
Only this tiny consumer executable, its scene Info.plist and outer signature are
rebuilt. This is not a source rebuild or qualification of the original editor.
"""
import hashlib
import json
from pathlib import Path
import plistlib
import shutil

from run_probe import BUNDLE, CLASSES, NAME, RUNTIME, digest, require


def build_scene_consumer(root, work, evidence, original_app, retained, receipt, command, inventory):
    app = work / 'scene-consumer' / (NAME + '.app')
    require(not app.exists(), 'Refusing a stale scene consumer')
    shutil.copytree(original_app, app, copy_function=shutil.copy2)
    require(inventory(app) == retained['app_inventory'], 'Copied retained inputs differ')
    source = root / 'Tools/OriginalEditor/SharedRuntime/SceneProbeApp.swift'
    source_hash = digest(source)
    info_path = app / 'Info.plist'
    info = plistlib.loads(info_path.read_bytes())
    require(info['CFBundleIdentifier'] == BUNDLE and info['CFBundleExecutable'] == NAME
            and 'UIApplicationSceneManifest' not in info, 'Unreviewed original diagnostic app identity')
    info['UIApplicationSceneManifest'] = {
        'UIApplicationSupportsMultipleScenes': False,
        'UISceneConfigurations': {'UIWindowSceneSessionRoleApplication': [{
            'UISceneConfigurationName': 'Shared provider',
            'UISceneClassName': 'UIWindowScene',
            'UISceneDelegateClassName': NAME + '.SharedRuntimeProbeScene',
        }]},
    }
    info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_BINARY, sort_keys=True))
    sdk = command('consumer-sdk-path', ['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path']).strip()
    version = command('consumer-sdk-version', ['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-version']).strip()
    require(version == info['DTPlatformVersion'] and version.split('.')[0] == '27',
            'The repaired consumer must use the retained producer SDK version')
    command('consumer-swift-version', ['xcrun', 'swiftc', '--version'])
    receipt.update(builds_executed=1, provider_builds_executed=0, consumer_builds_executed=1,
                   phase='BUILD_ONLY_SCENE_CONSUMER_AGAINST_RETAINED_PROVIDER')
    binary = work / 'scene-build' / NAME
    binary.parent.mkdir()
    command('scene-consumer-compile', [
        'xcrun', 'swiftc', '-parse-as-library', '-sdk', sdk, '-target',
        'arm64-apple-ios' + version + '-simulator', '-swift-version', '5', '-Onone', '-g',
        '-module-name', NAME, '-F', str(app / 'Frameworks'), '-framework', 'UIKit',
        '-Xlinker', '-needed_framework', '-Xlinker', RUNTIME,
        '-Xlinker', '-rpath', '-Xlinker', '@executable_path/Frameworks',
        str(source), '-o', str(binary),
    ], 180)
    require(digest(source) == source_hash, 'Scene consumer source changed during compile')
    shutil.copy2(binary, app / NAME)
    original_provider = original_app / 'Frameworks' / (RUNTIME + '.framework')
    provider = app / 'Frameworks' / (RUNTIME + '.framework')
    require(inventory(provider) == inventory(original_provider), 'Retained provider changed during consumer compile')
    command('scene-consumer-sign', ['codesign', '--force', '--sign', '-', app])
    command('scene-consumer-signature', ['codesign', '--verify', '--deep', '--strict', app])
    require(inventory(provider) == inventory(original_provider), 'Outer app signing changed the retained provider')
    loads = command('scene-consumer-loads', ['xcrun', 'otool', '-L', app / NAME])
    require('@rpath/' + RUNTIME + '.framework/' + RUNTIME in loads, 'Consumer is not linked to retained provider')
    symbols = set(command('scene-consumer-symbols', ['xcrun', 'nm', '-gjU', app / NAME]).splitlines())
    require(not symbols & {'_OBJC_CLASS_$_' + name for name in CLASSES},
            'Scene consumer duplicated provider implementations')
    current = inventory(app)
    original = retained['app_inventory']
    require(current.keys() == original.keys()
            and {p for p in current if current[p] != original[p]}
            == {NAME, 'Info.plist', '_CodeSignature/CodeResources'},
            'Consumer repair changed a resource or retained framework')
    archive = evidence / 'scene-consumer-app.zip'
    command('retain-scene-consumer', ['ditto', '-c', '-k', '--keepParent', app, archive], 120)
    retained_scene = {
        'schema': 1, 'status': 'SCENE_CONSUMER_BUILT_RUNTIME_NOT_QUALIFIED',
        'controller_source': receipt['controller_source'],
        'controller_run_id': receipt['controller_run_id'],
        'controller_run_attempt': receipt['controller_run_attempt'],
        'original_provider_source': retained['source_sha'],
        'original_provider_run_id': retained['run_id'],
        'original_provider_run_attempt': retained['run_attempt'],
        'consumer_source_sha256': source_hash, 'app_inventory': current,
        'archive_bytes': archive.stat().st_size, 'archive_sha256': digest(archive),
        'provider_binary_sha256': digest(provider / RUNTIME),
        'consumer_binary_sha256': digest(app / NAME), 'provider_builds_executed': 0,
        'stageb_qualified': False,
    }
    (evidence / 'retained-scene-consumer.json').write_text(json.dumps(retained_scene, indent=2, sort_keys=True) + '\n')
    receipt.update(
        original_provider_build_reused=True, original_consumer_reused=False,
        consumer_lifecycle_repair='ACTUAL_UIWINDOWSCENE_DELEGATE_AND_WINDOW',
        consumer_source_sha256=source_hash,
        binary_identity={RUNTIME: digest(provider / RUNTIME), NAME: digest(app / NAME)},
    )
    return app, current
