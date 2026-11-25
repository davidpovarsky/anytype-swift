"""Independent optimized production-API-only consumer of exported binaries."""
from pathlib import Path
import hashlib
import plistlib
import re
import shutil
import xml.etree.ElementTree as ET
from pbx_source import require, render
from clang_product_closure import read_clang_imports

def consumer_project(directory, exported, source, dynamic_frameworks, clang_identity, platform_name):
    require(platform_name in {'iphoneos', 'iphonesimulator'}, 'Unexpected Release consumer platform')
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
        # already ad-hoc signed these owned genuine Release exports.
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
    for name in ['Release']:
        settings = {'PRODUCT_NAME': 'OriginalEditorConsumer', 'PRODUCT_BUNDLE_IDENTIFIER': 'org.otzaria.acceptance.original-editor',
            'GENERATE_INFOPLIST_FILE': 'NO', 'INFOPLIST_FILE': 'Info.plist',
            'IPHONEOS_DEPLOYMENT_TARGET': '27.0', 'SDKROOT': 'iphoneos',
            'SUPPORTED_PLATFORMS': platform_name, 'SWIFT_VERSION': '5.0',
            'SWIFT_STRICT_CONCURRENCY': 'complete', 'TARGETED_DEVICE_FAMILY': '1,2',
            'CODE_SIGN_STYLE': 'Automatic', 'CODE_SIGN_IDENTITY': '-', 'DEVELOPMENT_TEAM': '',
            'CODE_SIGNING_ALLOWED': 'YES' if platform_name == 'iphonesimulator' else 'NO',
            'CODE_SIGNING_REQUIRED': 'YES' if platform_name == 'iphonesimulator' else 'NO', 'PROVISIONING_PROFILE_SPECIFIER': '',
            'ENABLE_USER_SCRIPT_SANDBOXING': 'YES', 'SWIFT_OPTIMIZATION_LEVEL': '-O', 'DEAD_CODE_STRIPPING': 'NO',
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
                     'defaultConfigurationIsVisible': '0', 'defaultConfigurationName': 'Release'})
    target = add('Target', {'isa': 'PBXNativeTarget', 'buildConfigurationList': config_list, 'buildPhases': phases,
                 'buildRules': [], 'dependencies': [], 'name': 'OriginalEditorConsumer', 'productName': 'OriginalEditorConsumer',
                 'productReference': product, 'productType': 'com.apple.product-type.application'})
    products = add('Products', {'isa': 'PBXGroup', 'children': [product], 'name': 'Products', 'sourceTree': '<group>'})
    group = add('Main', {'isa': 'PBXGroup', 'children': [source_ref, products, *references], 'sourceTree': '<group>'})
    project_config = add('ProjectConfiguration', {'isa': 'XCBuildConfiguration', 'buildSettings': {}, 'name': 'Release'})
    project_configs = add('ProjectConfigurations', {'isa': 'XCConfigurationList', 'buildConfigurations': [project_config],
                            'defaultConfigurationIsVisible': '0', 'defaultConfigurationName': 'Release'})
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
