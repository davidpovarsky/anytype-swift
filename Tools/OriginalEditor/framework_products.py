"""Export real build products and make a separate binary-only consumer project."""
import hashlib
import json
import math
import os
from pathlib import Path
import plistlib
import re
import shutil
import stat
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse

from framework_profile import TARGET, blob, sha256
from clang_product_closure import read_clang_imports
from pbx_source import render, require
from product_inventory import inventory


def copy_product_file(source, target):
    """Materialize a distinct owned product; APFS clones share only immutable extents."""
    if sys.platform != 'darwin':
        return shutil.copy2(source, target)
    import ctypes
    import errno
    clone = getattr(ctypes.CDLL(None, use_errno=True), "clonefile", None)
    if clone is None:
        return shutil.copy2(source, target)
    clone.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    clone.restype = ctypes.c_int
    # copy_product already proves the resolved input stays in the owned producer.
    # Resolve source aliases, matching the existing materializing copy2 behavior.
    if clone(os.fsencode(Path(source).resolve()), os.fsencode(target), 0) == 0:
        shutil.copystat(source, target)
        return str(target)
    error = ctypes.get_errno()
    if error in {errno.EXDEV, errno.ENOTSUP, errno.EOPNOTSUPP}:
        return shutil.copy2(source, target)
    raise OSError(error, os.strerror(error), str(target))


def copy_product(source, target, producer_root):
    source, target, producer_root = Path(source), Path(target), Path(producer_root).resolve()
    require(source.resolve().is_relative_to(producer_root), 'Product source escapes the owned producer')
    require(not target.exists(), 'Refusing to replace an existing exported product')
    for path in [source, *source.rglob('*')] if source.is_dir() else [source]:
        require(path.resolve().is_relative_to(producer_root), 'Product alias escapes its producer')
        require(path.is_file() or path.is_dir(), 'Special product member')
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        # iOS framework/module aliases are materialized from authenticated owned
        # build output, so an exported fallback cannot point back into DerivedData.
        shutil.copytree(source, target, symlinks=False, copy_function=copy_product_file)
    else:
        copy_product_file(source, target)


def framework_extended_attributes(path, follow):
    """Read every accessible attribute; never treat an unsupported API as empty.

    CPython's os xattr functions are Linux-only. Darwin uses the original
    documented listxattr/getxattr ABI, with no writes or added dependency.
    """
    if sys.platform != 'darwin':
        require(hasattr(os, 'listxattr') and hasattr(os, 'getxattr'),
                'No complete extended-attribute reader on this host')
        raw = {name: os.getxattr(path, name, follow_symlinks=follow)
               for name in os.listxattr(path, follow_symlinks=follow)}
    else:
        import ctypes
        library = ctypes.CDLL(None, use_errno=True)
        listing, reading = library.listxattr, library.getxattr
        listing.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
        listing.restype = ctypes.c_ssize_t
        reading.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                           ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
        reading.restype = ctypes.c_ssize_t
        encoded = os.fsencode(path)
        # Original sys/xattr.h: expose compression attributes, and inspect the
        # link itself when requested. No XATTR_NOSECURITY or mutation options.
        options = 0x20 | (0 if follow else 0x1)

        def read_buffer(call):
            size = call(None, 0)
            require(0 <= size <= 16 * 1024 * 1024, 'Unreadable or oversized framework attribute')
            buffer = ctypes.create_string_buffer(max(size, 1))
            actual = call(buffer, size)
            require(actual == size, 'Framework attributes changed or could not be read')
            return buffer.raw[:size]

        names = read_buffer(lambda buffer, size: listing(encoded, buffer, size, options))
        require(not names or names.endswith(b'\0'), 'Malformed Darwin attribute list')
        keys = names[:-1].split(b'\0') if names else []
        require(all(keys) and len(set(keys)) == len(keys),
                'Empty or duplicate Darwin attribute name')
        raw = {os.fsdecode(name): read_buffer(
            lambda buffer, size: reading(encoded, name, buffer, size, 0, options)) for name in keys}
    return {name: {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}
            for name, value in sorted(raw.items())}


def framework_closure(source):
    """Observe every member, including internal aliases, without changing it.

    Only timestamps and filesystem allocation/inode numbers are irrelevant to
    this equivalence check. File bytes, names, kinds, modes, owners, flags,
    extended attributes and literal alias targets must all agree. An alias may
    not borrow a file from another product, even inside this owned producer.
    """
    source = Path(source)
    require(source.is_dir() and not source.is_symlink(), 'Framework root must be a real directory')
    root = source.resolve(strict=True)
    result = {}

    def metadata(path, status, follow):
        return {'mode': stat.S_IMODE(status.st_mode), 'uid': status.st_uid, 'gid': status.st_gid,
                'flags': getattr(status, 'st_flags', 0),
                'extended_attributes': framework_extended_attributes(path, follow)}

    def visit(path, relative, ancestors):
        try:
            resolved = path.resolve(strict=True)
            require(resolved.is_relative_to(root), 'Framework alias escapes its own product: ' + relative)
            status, final = path.lstat(), resolved.stat()
            kind = ('symlink' if stat.S_ISLNK(status.st_mode) else
                    'directory' if stat.S_ISDIR(status.st_mode) else
                    'file' if stat.S_ISREG(status.st_mode) else 'special')
            final_kind = 'directory' if stat.S_ISDIR(final.st_mode) else 'file' if stat.S_ISREG(final.st_mode) else 'special'
            require(kind != 'special' and final_kind != 'special', 'Special framework member: ' + relative)
            row = {'kind': kind, **metadata(path, status, False), 'resolved_kind': final_kind,
                   'resolved_metadata': metadata(resolved, final, True)}
            if kind == 'symlink':
                row['link_target'] = os.readlink(path)
            if final_kind == 'file':
                row.update(bytes=final.st_size, sha256=sha256(resolved))
            result[relative] = row
            if final_kind == 'directory':
                require(resolved not in ancestors, 'Cyclic framework alias: ' + relative)
                for child in sorted(path.iterdir()):
                    visit(child, child.name if relative == '.' else relative + '/' + child.name,
                          ancestors | {resolved})
        except (OSError, RuntimeError) as error:
            raise ValueError('Unreadable or cyclic framework closure: ' + relative) from error

    visit(source, '.', set())
    return result


def select_framework_products(products, frameworks):
    """Admit only the actual Xcode root/PackageFrameworks Lib duplicate pair."""
    groups = {}
    for path in frameworks:
        groups.setdefault(path.name, []).append(path)
    require(TARGET + '.framework' in groups, 'Missing or ambiguous genuine framework products')
    selected, proofs = [], []
    for name, paths in sorted(groups.items()):
        if len(paths) == 1:
            selected.append(paths[0])
            continue
        relative = {path.relative_to(products).as_posix(): path for path in paths}
        expected = {'Lib.framework', 'PackageFrameworks/Lib.framework'}
        require(name == 'Lib.framework' and len(paths) == 2 and set(relative) == expected,
                'Missing or ambiguous genuine framework products')
        closures = {key: framework_closure(relative[key]) for key in sorted(relative)}
        require(closures['Lib.framework'] == closures['PackageFrameworks/Lib.framework'],
                'The two known Lib framework products differ')
        selected.append(relative['Lib.framework'])
        proofs.append({'name': name, 'selected': 'Lib.framework', 'source_closures': closures,
                       'equivalence': 'COMPLETE_CLOSURE_EQUAL'})
    return selected, proofs


def export_products(products, exported, producer_root):
    products, exported = Path(products).resolve(), Path(exported).resolve()
    require(products.is_relative_to(Path(producer_root).resolve()), 'Unowned product directory')
    require(not exported.exists(), 'Refusing stale export')
    require(not any(products.glob('*.app')) and not any(products.glob('*.xctest')),
            'A framework producer may not borrow an app or test binary')
    exported.mkdir(parents=True)
    frameworks = [p for p in products.rglob('*.framework')
                  if not any(parent.suffix in {'.framework', '.bundle', '.app', '.xctest'}
                             for parent in p.relative_to(products).parents)]
    frameworks, duplicate_proofs = select_framework_products(products, frameworks)
    names = [p.name for p in frameworks]
    for source in sorted(frameworks):
        copy_product(source, exported / 'Frameworks' / source.name, producer_root)
    bundles = [p for p in products.rglob('*.bundle')
               if not any(parent.suffix in {'.framework', '.bundle', '.app', '.xctest'}
                          for parent in p.relative_to(products).parents)]
    require(len({p.name for p in bundles}) == len(bundles), 'Ambiguous package resource bundle')
    for source in sorted(bundles):
        copy_product(source, exported / 'Bundles' / source.name, producer_root)
    if (products / 'Modules').is_dir():
        copy_product(products / 'Modules', exported / 'Modules', producer_root)
    else:
        (exported / 'Modules').mkdir()
    for source in sorted(products.glob('*.swiftmodule')):
        copy_product(source, exported / 'Modules' / source.name, producer_root)
    for source in sorted(products.glob('*.a')):
        copy_product(source, exported / 'Libraries' / source.name, producer_root)
    if (products / 'include').is_dir():
        copy_product(products / 'include', exported / 'Include', producer_root)
    # Resources are exported as real compiled bundles, not substituted accessor
    # code. Resolve them independently of whichever bundle the package uses.
    all_bundles = list(exported.rglob('*.bundle'))
    require(any((p / 'Assets.car').is_file() for p in all_bundles),
            'Original compiled asset catalogs were not exported')
    require(any(list(p.rglob('IBMPlexMono-Regular.ttf')) for p in all_bundles),
            'Original font resource bundle was not exported')
    require(any(list(p.rglob('he.lproj/UI.strings')) for p in all_bundles),
            'Original Hebrew localization bundle was not exported')
    result = inventory(exported)
    require(result, 'Empty binary/resource export')
    # Keep the measured input pair and the materialized output bound together.
    # This is not a general duplicate-name or same-hash selection fallback.
    for proof in duplicate_proofs:
        for relative, expected in proof['source_closures'].items():
            require(framework_closure(products / relative) == expected,
                    'A known Lib input changed during export')
        materialized = framework_closure(exported / 'Frameworks/Lib.framework')
        expected = proof['source_closures']['Lib.framework']
        require(set(materialized) == set(expected), 'Exported Lib membership differs')
        for relative, row in materialized.items():
            original = expected[relative]
            require(row['kind'] == original['resolved_kind']
                    and row['resolved_metadata'] == original['resolved_metadata']
                    and row.get('bytes') == original.get('bytes')
                    and row.get('sha256') == original.get('sha256'),
                    'Exported Lib member differs: ' + relative)
        proof['materialized_export_closure'] = materialized
    return {'frameworks': sorted(names), 'verified_known_duplicates': duplicate_proofs,
            'resource_bundles': sorted(p.name for p in bundles),
            'files': result, 'bytes': sum(item['bytes'] for item in result.values())}


def consumer_project(directory, exported, source, dynamic_frameworks, clang_identity):
    directory, exported, source = Path(directory).resolve(), Path(exported).resolve(), Path(source).resolve()
    clang_context = read_clang_imports(exported, clang_identity)
    require(not directory.exists(), 'Refusing existing consumer project')
    require(directory != exported and not directory.is_relative_to(exported), 'Consumer must be a separate project')
    directory.mkdir(parents=True)
    shutil.copyfile(source, directory / 'ConsumerApp.swift')
    relative_export = Path(__import__('os').path.relpath(exported, directory)).as_posix()
    objects = {}

    def add(name, value):
        key = hashlib.sha256(('OriginalEditorExternalConsumer:' + name).encode()).hexdigest()[:24].upper()
        require(key not in objects, 'Consumer object collision')
        objects[key] = value
        return key

    product = add('Product', {'isa': 'PBXFileReference', 'explicitFileType': 'wrapper.application',
                  'includeInIndex': '0', 'path': 'OriginalEditorConsumer.app', 'sourceTree': 'BUILT_PRODUCTS_DIR'})
    source_ref = add('Source', {'isa': 'PBXFileReference', 'lastKnownFileType': 'sourcecode.swift',
                     'path': 'ConsumerApp.swift', 'sourceTree': '<group>'})
    source_build = add('SourceBuild', {'isa': 'PBXBuildFile', 'fileRef': source_ref})
    references, links, embeds, resources = [], [], [], []
    for name in dynamic_frameworks:
        require(re.fullmatch(r'[A-Za-z0-9_.+-]+\.framework', name), 'Unexpected framework product name')
        reference = add('Framework_' + name, {'isa': 'PBXFileReference', 'lastKnownFileType': 'wrapper.framework',
                         'path': relative_export + '/Frameworks/' + name, 'sourceTree': 'SOURCE_ROOT'})
        references.append(reference)
        links.append(add('Link_' + name, {'isa': 'PBXBuildFile', 'fileRef': reference}))
        # No RemoveHeadersOnCopy or resource/module rewriting. The producer has
        # already ad-hoc signed the genuine simulator frameworks.
        embeds.append(add('Embed_' + name, {'isa': 'PBXBuildFile', 'fileRef': reference}))
    for path in sorted((exported / 'Bundles').glob('*.bundle')):
        reference = add('Bundle_' + path.name, {'isa': 'PBXFileReference', 'lastKnownFileType': 'wrapper.plug-in',
                         'path': relative_export + '/Bundles/' + path.name, 'sourceTree': 'SOURCE_ROOT'})
        references.append(reference)
        resources.append(add('Resource_' + path.name, {'isa': 'PBXBuildFile', 'fileRef': reference}))
    phases = []
    for name, kind, files in [('Sources', 'PBXSourcesBuildPhase', [source_build]),
                              ('Frameworks', 'PBXFrameworksBuildPhase', links),
                              ('Resources', 'PBXResourcesBuildPhase', resources)]:
        phases.append(add(name, {'isa': kind, 'buildActionMask': '2147483647', 'files': files,
                                 'runOnlyForDeploymentPostprocessing': '0'}))
    phases.append(add('Embed', {'isa': 'PBXCopyFilesBuildPhase', 'buildActionMask': '2147483647',
                               'dstPath': '', 'dstSubfolderSpec': '10', 'files': embeds,
                               'name': 'Embed genuine dependency frameworks', 'runOnlyForDeploymentPostprocessing': '0'}))
    configurations = []
    for name in ['Debug']:
        settings = {'PRODUCT_NAME': 'OriginalEditorConsumer', 'PRODUCT_BUNDLE_IDENTIFIER': 'org.otzaria.acceptance.original-editor',
            'GENERATE_INFOPLIST_FILE': 'NO', 'INFOPLIST_FILE': 'Info.plist',
            'IPHONEOS_DEPLOYMENT_TARGET': '27.0', 'SDKROOT': 'iphoneos',
            'SUPPORTED_PLATFORMS': 'iphoneos iphonesimulator', 'SWIFT_VERSION': '5.0',
            'SWIFT_STRICT_CONCURRENCY': 'complete', 'TARGETED_DEVICE_FAMILY': '1,2',
            'CODE_SIGN_STYLE': 'Automatic', 'CODE_SIGN_IDENTITY': '-', 'DEVELOPMENT_TEAM': '',
            'CODE_SIGNING_ALLOWED': 'YES', 'CODE_SIGNING_REQUIRED': 'YES', 'PROVISIONING_PROFILE_SPECIFIER': '',
            'ENABLE_USER_SCRIPT_SANDBOXING': 'YES', 'SWIFT_OPTIMIZATION_LEVEL': '-Onone',
            'LD_RUNPATH_SEARCH_PATHS': ['$(inherited)', '@executable_path/Frameworks'],
            'FRAMEWORK_SEARCH_PATHS': ['$(inherited)', '$(PROJECT_DIR)/' + relative_export + '/Frameworks'],
            'SWIFT_INCLUDE_PATHS': ['$(inherited)', '$(PROJECT_DIR)/' + relative_export + '/Modules'],
            'LIBRARY_SEARCH_PATHS': ['$(inherited)', '$(PROJECT_DIR)/' + relative_export + '/Libraries'],
            'HEADER_SEARCH_PATHS': ['$(inherited)', *[
                '$(PROJECT_DIR)/' + relative_export + '/' + path
                for path in clang_context['header_search_paths']]],
            'OTHER_SWIFT_FLAGS': ['$(inherited)', *[
                argument for path in clang_context['module_maps'] for argument in
                ['-Xcc', '-fmodule-map-file=$(PROJECT_DIR)/' + relative_export + '/' + path]]],
            'INFOPLIST_KEY_CFBundleDisplayName': 'Original editor resource acceptance',
            'INFOPLIST_KEY_UILaunchScreen_Generation': 'YES', 'INFOPLIST_KEY_LSRequiresIPhoneOS': 'YES'}
        configurations.append(add('Configuration_' + name, {'isa': 'XCBuildConfiguration', 'buildSettings': settings, 'name': name}))
    config_list = add('Configurations', {'isa': 'XCConfigurationList', 'buildConfigurations': configurations,
                     'defaultConfigurationIsVisible': '0', 'defaultConfigurationName': 'Debug'})
    target = add('Target', {'isa': 'PBXNativeTarget', 'buildConfigurationList': config_list, 'buildPhases': phases,
                 'buildRules': [], 'dependencies': [], 'name': 'OriginalEditorConsumer', 'productName': 'OriginalEditorConsumer',
                 'productReference': product, 'productType': 'com.apple.product-type.application'})
    products = add('Products', {'isa': 'PBXGroup', 'children': [product], 'name': 'Products', 'sourceTree': '<group>'})
    group = add('Main', {'isa': 'PBXGroup', 'children': [source_ref, products, *references], 'sourceTree': '<group>'})
    project_config = add('ProjectConfiguration', {'isa': 'XCBuildConfiguration', 'buildSettings': {}, 'name': 'Debug'})
    project_configs = add('ProjectConfigurations', {'isa': 'XCConfigurationList', 'buildConfigurations': [project_config],
                            'defaultConfigurationIsVisible': '0', 'defaultConfigurationName': 'Debug'})
    project = add('Project', {'isa': 'PBXProject', 'buildConfigurationList': project_configs,
                   'compatibilityVersion': 'Xcode 15.0', 'developmentRegion': 'en', 'knownRegions': ['en', 'he', 'Base'],
                   'mainGroup': group, 'productRefGroup': products, 'projectDirPath': '', 'projectRoot': '', 'targets': [target]})
    path = directory / 'OriginalEditorConsumer.xcodeproj'
    path.mkdir()
    (path / 'project.pbxproj').write_text('// !$*UTF8*$!\n' + render({
        'archiveVersion': '1', 'classes': {}, 'objectVersion': '60', 'objects': objects, 'rootObject': project}) + '\n')
    scheme = ET.Element('Scheme', LastUpgradeVersion='2700', version='1.3')
    action = ET.SubElement(scheme, 'BuildAction', parallelizeBuildables='YES', buildImplicitDependencies='NO')
    entries = ET.SubElement(action, 'BuildActionEntries')
    entry = ET.SubElement(entries, 'BuildActionEntry', buildForTesting='NO', buildForRunning='YES',
                          buildForProfiling='NO', buildForArchiving='NO', buildForAnalyzing='YES')
    ET.SubElement(entry, 'BuildableReference', BuildableIdentifier='primary', BlueprintIdentifier=target,
                  BuildableName='OriginalEditorConsumer.app', BlueprintName='OriginalEditorConsumer',
                  ReferencedContainer='container:OriginalEditorConsumer.xcodeproj')
    ET.indent(scheme, space='   ')
    shared = path / 'xcshareddata/xcschemes'
    shared.mkdir(parents=True)
    (shared / 'OriginalEditorConsumer.xcscheme').write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(scheme) + b'\n')
    with (directory / 'Info.plist').open('wb') as stream:
        plistlib.dump({'CFBundleIdentifier': '$(PRODUCT_BUNDLE_IDENTIFIER)',
            'CFBundleExecutable': '$(EXECUTABLE_NAME)', 'CFBundleName': 'OriginalEditorConsumer',
            'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1', 'CFBundleShortVersionString': '1.0',
            'CFBundleDevelopmentRegion': 'en', 'CFBundleLocalizations': ['en', 'he'],
            'LSRequiresIPhoneOS': True, 'UILaunchScreen': {},
            'UIApplicationSceneManifest': {'UIApplicationSupportsMultipleScenes': False,
                'UISceneConfigurations': {'UIWindowSceneSessionRoleApplication': [{
                    'UISceneConfigurationName': 'ResourceAcceptance',
                    'UISceneDelegateClassName': '$(PRODUCT_MODULE_NAME).OriginalEditorConsumerScene'}]}}}, stream)
    return path


def original_oracles(root, profile):
    root = Path(root)
    oracle = profile['resource_oracles']
    raw = {}
    for name in ['localization', 'font', 'color']:
        value = (root / oracle[name + '_path']).read_bytes()
        require(blob(value) == oracle[name + '_blob'], 'Original resource oracle differs: ' + name)
        raw[name] = value
    localized = json.loads(raw['localization'])['strings'][oracle['localization_key']]['localizations']
    colors = json.loads(raw['color'])['colors']
    expected_colors = {}
    for item in colors:
        name = 'dark' if item.get('appearances') == [{'appearance': 'luminosity', 'value': 'dark'}] else 'light'
        components = item['color']['components']
        require(item['color']['color-space'] == 'srgb' and name not in expected_colors, 'Unexpected original color oracle')
        def number(value):
            return int(value, 16) / 255 if value.startswith('0x') else float(value)
        expected_colors[name] = [number(components[key]) for key in ['red', 'green', 'blue', 'alpha']]
    require(set(expected_colors) == {'light', 'dark'}, 'Missing original color appearances')
    return {'translations': {lang: localized[lang]['stringUnit']['value'] for lang in ['en', 'he']},
            'font_sha256': hashlib.sha256(raw['font']).hexdigest(), 'font_bytes': len(raw['font']),
            'font_name': 'IBMPlexMono', 'colors': expected_colors}


def verify_observation(value, nonce, language, main_bundle, oracle):
    main_bundle = Path(main_bundle).resolve()
    require(value.get('schema') == 1 and value.get('status') == 'ACTUAL_EXTERNAL_CONSUMER_RESOURCE_OBSERVATION'
            and value.get('nonce') == nonce and value.get('mainBundleIdentifier') == 'org.otzaria.acceptance.original-editor'
            and Path(value.get('mainBundleURL', '')).resolve() == main_bundle,
            'Wrong actual consumer observation identity')
    languages = value.get('preferredLanguages', [])
    require(languages and re.split('[-_]', languages[0])[0] == language, 'Consumer language was not actually selected')
    inspection = value.get('inspection', {})
    require(inspection.get('moduleBundleIdentifier') == 'org.otzaria.anytype.original-editor'
            and Path(inspection.get('moduleBundleURL', '')).resolve() == main_bundle / 'Frameworks/AnytypeOriginalEditor.framework',
            'Original framework was not loaded from the external consumer')
    require(inspection.get('originalTypeNames') == [TARGET + '.' + name for name in
            ['EditorPageController', 'EditorPageModuleAssembly', 'PreparedEditorPageSession', 'EditorDocumentWriteOwner']],
            'Actual original compiled editor types differ')
    require(type(inspection.get('imagePNGBytes')) is int and inspection['imagePNGBytes'] > 32
            and re.fullmatch(r'[0-9a-f]{64}', inspection.get('imagePNGSHA256', ''))
            and type(inspection.get('imageWidth')) in {float, int}
            and math.isfinite(inspection['imageWidth']) and 0 < inspection['imageWidth'] <= 8192
            and type(inspection.get('imageHeight')) in {float, int}
            and math.isfinite(inspection['imageHeight']) and 0 < inspection['imageHeight'] <= 8192,
            'Original generated editor image accessor did not resolve')
    require(inspection.get('localizedCancel') == oracle['translations'][language],
            'Original generated localized accessor returned an incorrect value or fallback')
    font = Path(inspection.get('fontResourceURL', '')).resolve()
    require(font.is_relative_to(main_bundle) and font.name == 'IBMPlexMono-Regular.ttf'
            and inspection.get('fontName') == oracle['font_name']
            and inspection.get('fontBytes') == oracle['font_bytes']
            and inspection.get('fontSHA256') == oracle['font_sha256'],
            'Original generated font accessor did not resolve the exact consumer-owned resource')
    for style, key in [('light', 'lightTextRGBA'), ('dark', 'darkTextRGBA')]:
        actual = inspection.get(key, [])
        require(isinstance(actual, list) and len(actual) == 4
                and all(type(number) in {float, int} and abs(number - expected) < 0.0001
                        for number, expected in zip(actual, oracle['colors'][style])),
                'Original generated adaptive color accessor differs: ' + style)
    return {'language': language, 'status': 'ACTUAL_IMPORT_LINK_RESOURCE_RUNTIME_PASS',
            'native_editor_ui_tests': 0, 'editable_mount': 'NOT_EXPOSED'}


def verify_public_surface(graphs, source_root, host_contract=None):
    """Inspect the actual compiler graph for this target, not imported APIs."""
    source_root = Path(source_root).resolve()
    editor = source_root / 'Anytype/Sources/PresentationLayer/TextEditor'
    app_source = source_root / 'Anytype/Sources'
    facade = source_root / 'OriginalEditorFramework/AnytypeOriginalEditorModule.swift'
    reviewed_facades, required = {}, set()
    if host_contract is not None:
        require(host_contract.get('schema') == 2 and len(host_contract.get('facades', {})) == 10,
                'Malformed reviewed Host surface contract')
        for path, contract in host_contract['facades'].items():
            location = (source_root / path).resolve()
            require(location.is_relative_to(source_root / 'OriginalEditorFramework')
                    and isinstance(contract.get('roots'), list) and contract['roots']
                    and isinstance(contract.get('required'), list) and contract['required']
                    and contract.get('scope', 'PUBLIC') in {'PUBLIC', 'DEBUG_SIMULATOR_SPI_ONLY'},
                    'Unreviewed facade source/root requirement')
            reviewed_facades[location] = contract
            required.update((location, tuple(components)) for components in contract['required'])
        require(len(required) == 282, 'Incomplete public Host or qualification SPI surface requirement')
    found_inspection = False
    own_symbols = []
    imported_count = 0
    blocked = []
    unsafe_names = ('EditorPage', 'PreparedEditor', 'EditorDocumentWrite', 'DocumentOwned', 'BaseDocument',
                    'OwnedOriginalEditor', 'OwnedQualificationSpace', 'AnytypeOriginalEditorNativeFixture',
                    'AnytypeOriginalEditorRestoreQualification')
    observed_required = set()
    for graph in graphs:
        if graph.get('module', {}).get('name') != TARGET:
            imported_count += len(graph.get('symbols', []))
            continue
        require(isinstance(graph.get('symbols'), list), 'Malformed actual target symbol graph')
        for symbol in graph['symbols']:
            require(symbol.get('accessLevel') in {'public', 'open'}, 'Compiler graph has unexpected access scope')
            components = symbol.get('pathComponents', [])
            require(isinstance(components, list) and all(isinstance(item, str) for item in components),
                    'Malformed public symbol path')
            uri = symbol.get('location', {}).get('uri')
            location = None
            if uri:
                parsed = urlparse(uri)
                require(parsed.scheme == 'file', 'Unrecognized compiler symbol source URI')
                location = Path(unquote(parsed.path)).resolve()
            precise = symbol.get('identifier', {}).get('precise', '')
            our_identifier = precise.startswith('s:' + str(len(TARGET)) + TARGET)
            own_app_source = location is not None and location.is_relative_to(app_source)
            own_facade = location == facade or location in reviewed_facades
            # Imported/re-exported package symbols are not our target's public
            # constructors and must not be confused with an editing API.
            if not own_app_source and not own_facade and not our_identifier:
                imported_count += 1
                continue
            own_symbols.append({'path': components, 'identifier': precise, 'location': uri,
                                'spi': symbol.get('spi', False)})
            if own_facade and components[:1] == ['AnytypeOriginalEditorModule'] and components[-1:] == ['inspectResources()']:
                found_inspection = True
            if location in reviewed_facades:
                require(components and components[0] in reviewed_facades[location]['roots'],
                        'Unexpected public declaration in a reviewed Host facade: ' + repr(components))
                expected_spi = reviewed_facades[location].get('scope') == 'DEBUG_SIMULATOR_SPI_ONLY'
                require(type(symbol.get('spi', False)) is bool
                        and symbol.get('spi', False) is expected_spi,
                        'Actual compiler public/SPI scope differs from the reviewed facade: ' + repr(components))
                observed_required.add((location, tuple(components)))
                require(not (components[0] in host_contract['nonconstructible_types']
                             and any(item.startswith('init(') for item in components[1:])),
                        'Public constructor grants an unowned original Host/session capability')
            if (host_contract is not None and location is not None
                    and location.is_relative_to(source_root / 'OriginalEditorFramework')
                    and location not in reviewed_facades):
                blocked.append({'path': components, 'identifier': precise, 'location': uri})
            if ((location is not None and location.is_relative_to(editor))
                    or any(item.startswith(unsafe_names) for item in components)):
                blocked.append({'path': components, 'identifier': precise, 'location': uri})
    require(found_inspection, 'Actual compiler graph does not expose the reviewed inspection facade')
    require(not blocked, 'Unqualified original editor/document/writer declaration is public: ' + json.dumps(blocked))
    require(required <= observed_required, 'Missing actual compiled Host or qualification SPI declaration: ' +
            repr(sorted((str(location), components) for location, components in required - observed_required)))
    return {'status': 'ACTUAL_TARGET_PUBLIC_SURFACE_INSPECTED', 'target': TARGET,
            'own_public_symbols': own_symbols, 'imported_dependency_symbols_not_rejected': imported_count,
            'public_original_editor_or_writer_declarations': [],
            'reviewed_host_and_spi_requirements_observed': len(required),
            'qualification_spi_scope_verified': host_contract is not None,
            'public_host_scope_verified': host_contract is not None,
            'editable_mount_api': 'EXPOSED_COMPILED_NATIVE_EDITOR_NOT_RUN' if host_contract is not None else 'NOT_EXPOSED'}
