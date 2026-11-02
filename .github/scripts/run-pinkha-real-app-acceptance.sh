#!/bin/bash
set -euo pipefail

device_kind="$1"
udid="$2"
direction="$3"
device_language="$4"
device_region="$5"
app_language="$6"
app_region="$7"
result="build/results/release-${device_kind}-${direction}.xcresult"
log="build/evidence/release-${device_kind}-${direction}.log"

xcrun simctl shutdown "$udid" || true
xcrun simctl boot "$udid"
xcrun simctl bootstatus "$udid" -b
xcrun simctl uninstall "$udid" io.anytype.app || true
xcrun simctl uninstall "$udid" io.anytype.app.dev || true
xcrun simctl spawn "$udid" defaults write NSGlobalDomain AppleLanguages -array "$device_language"
xcrun simctl spawn "$udid" defaults write NSGlobalDomain AppleLocale "$device_language"_"$device_region"
{
  printf 'device-language-requested=%s\n' "$device_language"
  printf 'device-region-requested=%s\n' "$device_region"
  printf 'app-language-requested=%s\n' "$app_language"
  printf 'app-region-requested=%s\n' "$app_region"
  xcrun simctl spawn "$udid" defaults read NSGlobalDomain AppleLanguages
  xcrun simctl spawn "$udid" defaults read NSGlobalDomain AppleLocale
} | tee "build/evidence/release-${device_kind}-${direction}-device-language.txt"
# Apply the OS language before launching the app with the opposite language.
xcrun simctl shutdown "$udid"
xcrun simctl boot "$udid"
xcrun simctl bootstatus "$udid" -b

xcrun simctl spawn "$udid" log stream \
  --style compact \
  --level info \
  --predicate 'subsystem == "com.anytype.pinkha"' \
  > "build/evidence/release-${device_kind}-${direction}-pinkha-runtime.log" 2>&1 &
pinkha_log_pid=$!
trap 'kill "$pinkha_log_pid" 2>/dev/null || true; wait "$pinkha_log_pid" 2>/dev/null || true; xcrun simctl shutdown "$udid" || true' EXIT

# Prepare real objects through the original native APIs in this disposable simulator.
# Keep simulator signing/Keychain and the Release bundle/container identical to the UI run.
set +e
xcodebuild test-without-building \
  -project Anytype.xcodeproj \
  -scheme Anytype \
  -configuration Release-Anytype \
  -destination "platform=iOS Simulator,id=$udid" \
  -derivedDataPath build/DerivedData-Release-Acceptance \
  -resultBundlePath "build/results/release-${device_kind}-${direction}-preparation.xcresult" \
  -collect-test-diagnostics never \
  -parallel-testing-enabled NO \
  -test-timeouts-enabled YES \
  -default-test-execution-time-allowance 300 \
  -maximum-test-execution-time-allowance 300 \
  -only-testing:AnytypeTests/PinkhaStage1AcceptancePreparationTests \
  ENABLE_TESTABILITY=YES \
  ONLY_ACTIVE_ARCH=YES \
  2>&1 | tee "build/evidence/release-${device_kind}-${direction}-preparation.log"
preparation_status=${PIPESTATUS[0]}
set -e
printf '%s\n' "$preparation_status" > "build/evidence/release-${device_kind}-${direction}-preparation-status.txt"
if [[ $preparation_status -ne 0 ]]; then exit "$preparation_status"; fi

data_container="$(xcrun simctl get_app_container "$udid" io.anytype.app data)"
fixture_path="$data_container/Library/Application Support/pinkha-stage1-acceptance-state.json"
cp "$fixture_path" "build/evidence/release-${device_kind}-${direction}-fixtures.json"
fixture_env="build/evidence/release-${device_kind}-${direction}-fixtures.sh"
python3 - "$fixture_path" > "$fixture_env" <<'PY'
import json, shlex, sys
state = json.load(open(sys.argv[1]))
keys = {
    'PINKHA_ACCEPTANCE_SPACE_ID': 'spaceId',
    'PINKHA_ACCEPTANCE_PINKHA_ID': 'pinkhaObjectId',
    'PINKHA_ACCEPTANCE_NOTE_ID': 'noteObjectId',
    'PINKHA_ACCEPTANCE_PAGE_ID': 'pageObjectId',
}
for environment_key, state_key in keys.items():
    value = state.get(state_key)
    if not isinstance(value, str) or not value:
        raise SystemExit(f'Missing native fixture ID: {state_key}')
    print(f'export TEST_RUNNER_{environment_key}={shlex.quote(value)}')
PY
source "$fixture_env"

set +e
TEST_RUNNER_PINKHA_ACCEPTANCE_DIRECTION="$direction" \
TEST_RUNNER_PINKHA_ACCEPTANCE_DEVICE_LANGUAGE="$device_language" \
xcodebuild test-without-building \
  -workspace PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcworkspace \
  -scheme PinkhaStage1Acceptance \
  -configuration Release-Anytype \
  -destination "platform=iOS Simulator,id=$udid" \
  -derivedDataPath build/DerivedData-Release-Acceptance \
  -resultBundlePath "$result" \
  -collect-test-diagnostics never \
  -parallel-testing-enabled NO \
  -test-timeouts-enabled YES \
  -default-test-execution-time-allowance 900 \
  -maximum-test-execution-time-allowance 900 \
  -testLanguage "$app_language" \
  -testRegion "$app_region" \
  -only-testing:PinkhaStage1AcceptanceUITests/PinkhaStage1AcceptanceUITests \
  ENABLE_TESTABILITY=YES \
  ONLY_ACTIVE_ARCH=YES \
  2>&1 | tee "$log"
run_status=${PIPESTATUS[0]}
set -e
printf '%s\n' "$run_status" > "build/evidence/release-${device_kind}-${direction}-status.txt"
exit "$run_status"
