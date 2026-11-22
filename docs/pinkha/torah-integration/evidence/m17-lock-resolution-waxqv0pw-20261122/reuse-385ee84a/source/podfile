ENV['RCT_NEW_ARCH_ENABLED'] = '1'

upstream_dir = File.expand_path('Vendor/SefariaMobile/Upstream', __dir__)
ENV['NODE_PATH'] = [File.join(upstream_dir, 'node_modules'), ENV['NODE_PATH']].compact.reject(&:empty?).join(':')

require File.join(File.dirname(`node --print "require.resolve('expo/package.json', {paths: ['#{upstream_dir}']})"`), "scripts/autolinking")
require Pod::Executable.execute_command('node', ['-p',
  'require.resolve(
    "react-native/scripts/react_native_pods.rb",
    {paths: [process.argv[1]]},
  )', upstream_dir]).strip

min_ios_version_supported = '18.0'
platform :ios, min_ios_version_supported
prepare_react_native_project!

$RNFirebaseAnalyticsWithoutAdIdSupport = true
production = ENV["PRODUCTION"] == "1"

target 'Maktabah-iOS' do
  project 'Maktabah.xcodeproj'

  pod 'Firebase', :modular_headers => true
  pod 'FirebaseCoreInternal', :modular_headers => true
  pod 'GoogleUtilities', :modular_headers => true
  pod 'FirebaseCrashlytics', :modular_headers => true
  pod 'FirebaseCore', :modular_headers => true
  pod 'FirebaseInstallations', :modular_headers => true
  pod 'GoogleDataTransport', :modular_headers => true
  pod 'nanopb', :modular_headers => true
  pod 'FirebaseRemoteConfig', :modular_headers => true
  pod 'FirebaseABTesting', :modular_headers => true
  pod 'FirebaseSessions', :modular_headers => true
  pod 'FirebaseCoreExtension', :modular_headers => true
  pod 'RecaptchaInterop', :modular_headers => true
  pod 'AppCheckCore', :modular_headers => true

  use_expo_modules!(
    :projectRoot => upstream_dir,
    :project_root => upstream_dir,
    :searchPaths => [upstream_dir],
    :search_paths => [upstream_dir]
  )

  post_integrate do |installer|
    begin
      expo_patch_react_imports!(installer)
    rescue => e
      Pod::UI.warn e
    end
  end

  cli_config_command = [
    'node',
    '--no-warnings',
    '-e',
    "process.chdir('#{upstream_dir}');process.argv=['', '', 'config'];require('@react-native-community/cli').run()"
  ]
  $config = use_native_modules!(cli_config_command)

  rn_rel_path = 'Vendor/SefariaMobile/Upstream/node_modules/react-native'
  use_react_native!(
    :path => rn_rel_path,
    :production => production,
    :app_path => upstream_dir
  )
end

post_install do |installer|
  rn_rel_path = 'Vendor/SefariaMobile/Upstream/node_modules/react-native'

  # Gracefully override set_RCTNewArchEnabled_in_info_plist because RCTNewArchEnabled
  # is already statically configured in Source/iOS-Info.plist and scanning non-UTF8 targets crashes.
  if defined?(NewArchitectureHelper)
    class << NewArchitectureHelper
      def set_RCTNewArchEnabled_in_info_plist(installer, new_arch_enabled)
        Pod::UI.message "RCTNewArchEnabled is statically configured in Source/iOS-Info.plist"
      end
    end
  end

  react_native_post_install(
    installer,
    rn_rel_path,
    :mac_catalyst_enabled => false
  )

  installer.aggregate_targets.each do |aggregate_target|
    aggregate_target.user_project.targets.each do |target|
      target.build_phases.each do |phase|
        if phase.respond_to?(:name) && phase.name.to_s =~ /Crashlytics/i
          if phase.respond_to?(:shell_script) && phase.shell_script && !phase.shell_script.include?("Skipping Crashlytics")
            phase.shell_script = "if [ \"${CONFIGURATION}\" = \"Debug\" ] || [ \"${EFFECTIVE_PLATFORM_NAME}\" = \"-iphonesimulator\" ]; then\n  echo \"Skipping Crashlytics dSYM upload for simulator/debug build\"\n  exit 0\nfi\n" + phase.shell_script
          end
        end
      end
    end
    aggregate_target.user_project.save
  end

  installer.pods_project.targets.each do |target|
    target.build_configurations.each do |config|
      config.build_settings['ENABLE_USER_SCRIPT_SANDBOXING'] = 'NO'
      current_dep = config.build_settings['IPHONEOS_DEPLOYMENT_TARGET']
      if current_dep.nil? || current_dep.to_f < 15.0
        config.build_settings['IPHONEOS_DEPLOYMENT_TARGET'] = '18.0'
      end
    end
  end
  installer.pods_project.save
end
