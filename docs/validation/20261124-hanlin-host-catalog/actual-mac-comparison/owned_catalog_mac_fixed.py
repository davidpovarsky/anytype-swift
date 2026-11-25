#!/usr/bin/env python3
"""Apply the exact reviewed candidate after the preserved actual baseline."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, signal, subprocess, time
import xml.etree.ElementTree as ET

ROOT = Path("/Users/m1/builds/hanlin-f48bfc6596ee-anytype-catalog")
SOURCE = ROOT / "source"
HARNESS = ROOT / "host-harness"
EVIDENCE = ROOT / "host-fixed-evidence"
BASE = ROOT / "host-baseline-evidence"
ENGINE = "Packages/HanlinPlatform/Sources/HanlinChatCore/HanlinAISDKAgentEngine.swift"
TEST = "Packages/HanlinPlatform/Tests/HanlinChatCoreTests/HanlinCatalogReloadCancellationTests.swift"
ORIGINAL = "Packages/HanlinPlatform/Tests/HanlinChatCoreTests/HanlinTransientToolCatalogTests.swift"
EXPECTED = {
 ("HanlinChatCoreTests.HanlinTransientToolCatalogTests", "restoredCatalogContinuesTheOriginalEmptyToolResult()"),
 ("HanlinChatCoreTests.HanlinCatalogReloadCancellationTests", "cancellationDuringFinalCatalogLookupStopsBeforeAnotherProviderStep()"),
}
AUXILIARY = {
 "Packages/HanlinPlatform/.build/.buildSystem_debug": "cd1ba1c9604b794d71cd3cb482cc02e4c16bdea56c361333fabe801a74db2b90",
 "Packages/HanlinPlatform/.build/.lock": "39525c7dc9ec716b58cffac93b2bc246e651e055c3f820a12e161755ea0b6988",
 "Packages/HanlinPlatform/.build/CACHEDIR.TAG": "61833598201b8d9bb6a18003b6be9fd00ae014cfbd583253c1f23b746bf035d1",
 "Packages/HanlinPlatform/.swiftpm/configuration/mirrors.json": "9086d4db30679663869b11e82b8a9996cdba06a9026eeaa33e059fc9b379689c",
}
ENV = dict(os.environ)
ENV["DEVELOPER_DIR"] = "/Applications/Xcode.app/Contents/Developer"
assert not any(k.startswith("GITHUB_") for k in ENV)
assert os.uname().sysname == "Darwin" and os.uname().machine == "arm64"

def digest(p):
 with p.open("rb") as f:
  return hashlib.file_digest(f, "sha256").hexdigest()

def utc():
 return datetime.datetime.now(datetime.timezone.utc).isoformat()

def write(p, obj):
 p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")

def capacity():
 raw = subprocess.check_output(["vm_stat"], text=True)
 page = int(raw.split("page size of ")[1].split(" bytes")[0])
 values = {line.split(":", 1)[0].strip(): int(line.split(":", 1)[1].strip().rstrip("."))
           for line in raw.splitlines()[1:] if ":" in line}
 return {"availableAndReclaimableBytes": sum(values.get(k, 0) for k in
         ["Pages free", "Pages inactive", "Pages speculative"]) * page,
         "pageBytes": page, "compressedBytes": values["Pages occupied by compressor"] * page}

def apple_activity():
 rows = []
 for line in subprocess.check_output(["ps", "-axo", "pid=,pgid=,%cpu=,rss=,comm="], text=True).splitlines():
  a = line.split(None, 4)
  if len(a) == 5 and Path(a[4]).name in {"swift-frontend", "clang", "clang++", "ld", "ld64.lld", "swiftc", "xcodebuild", "Runner.Worker"}:
   rows.append({"pid": int(a[0]), "pgid": int(a[1]), "cpu": float(a[2]), "rssKB": int(a[3]), "exe": a[4]})
 return rows

assert digest(ROOT / "source-manifest.json") == "dea308bed9cedcedbccee8ed6085d873626c88e1d490de200b9b096840fbd82a"
assert digest(ROOT / "candidate-v2/candidate-v2-manifest.json") == "4868cb52df82b755aa1c68754a1a29bde9f508ffde1ee47ad4cbe27ea06e0e3b"
assert digest(ROOT / "host-harness-manifest.json") == "6168908358d68ee82b0630f9bf84ff3b6e25b9ab9e2a4ddd30d0afacb1bf03a9"
origin = json.loads((ROOT / "source-manifest.json").read_text())
candidate = json.loads((ROOT / "candidate-v2/candidate-v2-manifest.json").read_text())
harness = json.loads((ROOT / "host-harness-manifest.json").read_text())
assert origin["baselineCommit"] == "f48bfc6596eebe491c982bbecbd01939bbce1ed1"
assert candidate["candidateCommit"] == "6bd6036dbca16c969689a5722550a54bebc1e851"
assert set(candidate["files"]) == {ENGINE, TEST}
assert candidate["unchangedOriginalRegressionSHA256"] == "1f5f18df56420a7b9b41acfb67f9995d8c4596cc42609c75337f542fcf1de65a"

def verify_source(fixed):
 rows = dict(origin["baselineFiles"])
 if fixed:
  rows.update(candidate["files"])
 for path, row in rows.items():
  actual = SOURCE / path
  assert digest(actual) == row["sha256"] and actual.stat().st_size == row["bytes"], path
 actual_files = {str(p.relative_to(SOURCE)) for p in SOURCE.rglob("*") if p.is_file()}
 assert actual_files == set(rows) | set(AUXILIARY), "Unexpected original package/source auxiliary files"
 for path, sha in AUXILIARY.items():
  assert digest(SOURCE / path) == sha, "Frozen setup artifact changed: " + path
 for path, sha in harness["files"].items():
  assert digest(HARNESS / path) == sha, path
 if fixed:
  assert digest(HARNESS / "Tests/HanlinChatCoreTests" / Path(TEST).name) == candidate["files"][TEST]["sha256"]
  assert {p.name for p in (HARNESS / "Tests/HanlinChatCoreTests").iterdir()} == {Path(TEST).name, Path(ORIGINAL).name}
 return {"sourceFiles": len(rows), "originalRegressionSHA256": digest(SOURCE / ORIGINAL),
         "originalPackageSHA256": digest(SOURCE / "Packages/HanlinPlatform/Package.swift")}

def verify_deps():
 pins = {p["identity"]: p["state"]["revision"] for p in json.loads((HARNESS / "Package.resolved").read_text())["pins"]}
 assert pins == harness["dependencyPins"]
 for name, sha in pins.items():
  checkout = ROOT / "host-build/checkouts" / name
  assert subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip() == sha
  assert not subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain"], text=True).strip()
 return pins

baseline = json.loads((BASE / "baseline-result.json").read_text())
assert digest(BASE / "baseline-result.json") == "42847b6171c9dcda90cba847dc95f23c8c37dda99d0111426f7ad78e34bf54d0"
assert baseline["status"] == "ACTUAL_BASELINE_FAILED_AS_EXPECTED"
assert baseline["sourceUnchanged"] and baseline["ownedCommandExited"] and baseline["testability"]["compilerFlagObserved"]
source_before = verify_source(False)
pins = verify_deps()
cap = capacity()
activity = apple_activity()
assert cap["availableAndReclaimableBytes"] >= 6 * 1024**3, cap
assert shutil.disk_usage(ROOT).free >= 8 * 1024**3
assert sum(r["cpu"] for r in activity) < 600
help_text = subprocess.check_output(["xcrun", "swift", "test", "--help"], env=ENV, text=True)
for flag in ["--force-resolved-versions", "--verbose", "--no-parallel", "--xunit-output", "--filter"]:
 assert flag in help_text, flag
toolchain = subprocess.check_output(["xcrun", "swift", "--version"], env=ENV, text=True).strip()
assert toolchain == baseline["toolchain"]
xcode = subprocess.check_output(["xcodebuild", "-version"], env=ENV, text=True).strip()
assert xcode == baseline["xcode"]
preserved = {p.name: digest(p) for p in BASE.iterdir() if p.is_file()}
EVIDENCE.mkdir(mode=0o700, exist_ok=False)
receipt = {"mode": "LOCAL_MACOS_ENGINE_REGRESSION", "phase": "fixed",
 "sourceCommit": candidate["candidateCommit"], "baselineCommit": origin["baselineCommit"],
 "originalProductionCommit": baseline["originalProductionCommit"],
 "sourceManifestSHA256": digest(ROOT / "source-manifest.json"),
 "candidateManifestSHA256": digest(ROOT / "candidate-v2/candidate-v2-manifest.json"),
 "harnessManifestSHA256": digest(ROOT / "host-harness-manifest.json"),
 "baselineResultSHA256": digest(BASE / "baseline-result.json"),
 "baselineEvidenceFiles": preserved, "expectedCases": sorted(EXPECTED),
 "sourceBeforeCandidateApplication": source_before, "frozenAuxiliaryInputs": AUXILIARY, "dependencyPins": pins,
 "appBuilds": 0, "simulatorCreations": 0, "nativeWrites": 0, "providerIsMockFetch": True,
 "startedAt": utc(), "capacity": cap, "externalAppleActivity": activity,
 "overlapDeclared": bool(activity), "throughputComparison": False,
 "toolchain": toolchain, "xcode": xcode, "controllerSHA256": digest(Path(__file__)),
 "capacityObservations": []}
proc = None
applied = False
try:
 with (EVIDENCE / "original-HanlinAISDKAgentEngine.swift").open("xb") as out:
  out.write((SOURCE / ENGINE).read_bytes())
 for path, row in candidate["files"].items():
  donor = ROOT / "candidate-v2" / path
  content = donor.read_bytes()
  assert hashlib.sha256(content).hexdigest() == row["sha256"] and len(content) == row["bytes"]
  assert hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest() == row["gitBlobSHA1"]
  target = SOURCE / path
  if target.exists():
   target.chmod(0o600)
  target.write_bytes(content)
  if "/Tests/" in path:
   (HARNESS / "Tests/HanlinChatCoreTests" / Path(path).name).write_bytes(content)
 applied = True
 receipt["sourceBeforeExecution"] = verify_source(True)
 result = EVIDENCE / "fixed.xml"
 command = ["xcrun", "swift", "test", "--package-path", str(HARNESS),
  "--scratch-path", str(ROOT / "host-build"), "--cache-path", str(ROOT / "host-cache"),
  "--force-resolved-versions", "--skip-update", "--verbose", "-j", "1",
  "--disable-xctest", "--enable-swift-testing", "--no-parallel",
  "--filter", "(HanlinTransientToolCatalogTests|HanlinCatalogReloadCancellationTests)",
  "--xunit-output", str(result)]
 receipt["command"] = command
 write(EVIDENCE / "fixed-launch.json", receipt)
 with (EVIDENCE / "fixed.log").open("xb") as output:
  proc = subprocess.Popen(command, cwd=HARNESS, env=ENV, stdout=output, stderr=subprocess.STDOUT,
                          stdin=subprocess.DEVNULL, start_new_session=True)
  receipt["pid"] = proc.pid
  receipt["pgid"] = os.getpgid(proc.pid)
  write(EVIDENCE / "fixed-active.json", receipt)
  deadline = time.monotonic() + 900
  next_check = time.monotonic() + 20
  low = 0
  while proc.poll() is None:
   if time.monotonic() > deadline:
    raise TimeoutError("Owned fixed comparison budget 900 seconds")
   if time.monotonic() >= next_check:
    sample = capacity()
    receipt["capacityObservations"].append({"at": utc(), **sample})
    low = low + 1 if sample["availableAndReclaimableBytes"] < 1024**3 else 0
    if low >= 2:
     raise RuntimeError("Owned job stopped after two low-memory observations")
    next_check = time.monotonic() + 20
   time.sleep(2)
  receipt["commandExit"] = proc.returncode
 assert result.is_file(), "No actual Swift Testing result; bootstrap is not test success"
 cases = list(ET.fromstring(result.read_bytes()).iter("testcase"))
 receipt["cases"] = [{"attributes": c.attrib, "failures": [(x.text or "") for x in c.findall("failure")]} for c in cases]
 actual = {(c.attrib.get("classname"), c.attrib.get("name")) for c in cases}
 receipt["counts"] = {"totalTestCount": len(cases),
  "failedTests": sum(c.find("failure") is not None or c.find("error") is not None for c in cases),
  "skippedTests": sum(c.find("skipped") is not None for c in cases)}
 assert len(cases) == 2 and actual == EXPECTED, "Wrong actual selected test identities"
 assert receipt["commandExit"] == 0 and receipt["counts"] == {"totalTestCount": 2, "failedTests": 0, "skippedTests": 0}
 log = (EVIDENCE / "fixed.log").read_text(errors="replace")
 receipt["testability"] = {"unchangedTestableImport": "@testable import HanlinChatCore" in
  (HARNESS / "Tests/HanlinChatCoreTests" / Path(ORIGINAL).name).read_text(),
  "compilerFlagObserved": any("-module-name HanlinChatCore" in line and "-enable-testing" in line for line in log.splitlines()),
  "actualTwoMethodsExecuted": True}
 assert receipt["testability"]["unchangedTestableImport"]
 receipt["status"] = "ACTUAL_FIXED_TWO_METHODS_PASS"
except BaseException as error:
 receipt["status"] = "FIXED_COMPARISON_REQUIRES_REVIEW"
 receipt["error"] = {"type": type(error).__name__, "message": str(error)}
finally:
 if proc is not None and proc.poll() is None:
  assert os.getpgid(proc.pid) == proc.pid
  os.killpg(proc.pid, signal.SIGTERM)
  try:
   proc.wait(timeout=10)
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid, signal.SIGKILL)
   proc.wait(timeout=10)
 receipt["ownedCommandExited"] = proc is None or proc.poll() is not None
 try:
  receipt["sourceAfter"] = verify_source(applied)
  receipt["sourceUnchangedDuringExecution"] = True
  receipt["dependencyPinsAfter"] = verify_deps()
  assert all(digest(BASE / name) == sha for name, sha in preserved.items())
  receipt["originalBaselineEvidenceUnchanged"] = True
 except BaseException as error:
  receipt["status"] = "FIXED_COMPARISON_REQUIRES_REVIEW"
  receipt["readbackError"] = str(error)
 receipt["finishedAt"] = utc()
 write(EVIDENCE / "fixed-result.json", receipt)
 print(json.dumps({k: receipt.get(k) for k in ["status", "commandExit", "counts", "sourceUnchangedDuringExecution",
        "originalBaselineEvidenceUnchanged", "ownedCommandExited", "error", "readbackError", "finishedAt"]}))
raise SystemExit(0 if receipt["status"] == "ACTUAL_FIXED_TWO_METHODS_PASS" else 1)
