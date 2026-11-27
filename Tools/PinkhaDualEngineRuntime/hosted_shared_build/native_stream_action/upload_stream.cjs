'use strict';

// Reuse the exact already downloaded GitHub action library in memory. Only its
// bootstrap entry is replaced by explicit exports. No original authentication,
// retry, transport, hashing, retention or protobuf function is edited; the cache
// is never written. A different upstream bundle fails closed before use.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const Module = require('node:module');
const cp = require('node:child_process');
const {setTimeout: delay} = require('node:timers/promises');

const ACTION = 'ea165f8d65b6e75b540449e92b4886f43607fa02';
const BUNDLE_SHA = '0165b8a75330f3228f2c7a234b4ff8a107b9139c2b519147f4c8e9fe99b262d8';
const STARTUP = '/******/ \tvar __webpack_exports__ = __nccwpck_require__(36664);';
const EXPOSE = '/******/ \tvar __webpack_exports__ = {' +
  'core:__nccwpck_require__(42186),' +
  'client:__nccwpck_require__(12312),' +
  'util:__nccwpck_require__(63062),' +
  'blob:__nccwpck_require__(7246),' +
  'retention:__nccwpck_require__(3231),' +
  'zip:__nccwpck_require__(69186),' +
  'archiver:__nccwpck_require__(43084),' +
  'generated:__nccwpck_require__(49960),' +
  'config:__nccwpck_require__(74610)};';
const MiB = 1024 ** 2;
const LIMIT_SECONDS = 1500;
const MAX_RSS = 768 * MiB;

function requireValue(value, why) {
  if (!value) throw new Error(why);
}
function digest(data) { return crypto.createHash('sha256').update(data).digest('hex'); }
function jsonFile(name, value) {
  const data = Buffer.from(JSON.stringify(value, null, 2) + '\n');
  requireValue(data.length <= 8 * MiB, 'Bounded stream evidence required');
  fs.writeFileSync(name, data, {flag: 'wx', mode: 0o600});
  return {path: name, bytes: data.length, sha256: digest(data)};
}
function loadOriginal(bundlePath) {
  const raw = fs.readFileSync(bundlePath);
  requireValue(raw.length === 5051718 && digest(raw) === BUNDLE_SHA, 'Exact original artifact action bundle required');
  const source = raw.toString('utf8');
  requireValue(source.split(STARTUP).length === 2 && !source.includes(EXPOSE), 'Exact original single bootstrap required');
  const exposed = source.replace(STARTUP, EXPOSE);
  requireValue(digest(Buffer.from(exposed.replace(EXPOSE, STARTUP))) === BUNDLE_SHA, 'Full original bundle inverse differs');
  const instance = new Module(bundlePath, module);
  instance.filename = bundlePath;
  instance.paths = [];
  instance._compile(exposed, bundlePath);
  const library = instance.exports;
  requireValue(typeof library.client.internalArtifactTwirpClient === 'function' &&
    typeof library.util.getBackendIdsFromToken === 'function' &&
    typeof library.blob.uploadZipToBlobStorage === 'function' &&
    typeof library.archiver.create === 'function' &&
    typeof library.zip.ZipUploadStream === 'function' &&
    typeof library.retention.getExpiration === 'function' &&
    typeof library.generated.StringValue.create === 'function' &&
    typeof library.generated.ArtifactServiceClientJSON === 'function' &&
    typeof library.config.getConcurrency === 'function' &&
    typeof library.config.getUploadChunkTimeout === 'function' &&
    typeof library.core.setOutput === 'function' && typeof library.core.setSecret === 'function' &&
    typeof library.util.maskSigUrl === 'function' &&
    library.config.getUploadChunkSize() === 8 * MiB, 'Original artifact stream exports differ');
  requireValue(library.generated.StringValue.create({value: 'sha256:offline-control'}).value === 'sha256:offline-control',
    'Original finalization StringValue namespace differs');
  const offlineClient = new library.generated.ArtifactServiceClientJSON({request() { throw new Error('Offline namespace probe must not request network'); }});
  requireValue(typeof offlineClient.CreateArtifact === 'function' && typeof offlineClient.FinalizeArtifact === 'function' &&
    library.retention.getExpiration(30) !== undefined && Number.isFinite(library.config.getUploadChunkTimeout()) &&
    library.config.getConcurrency() >= 1, 'Original finalization/client/retention namespace differs');
  return {library, proof: {originalActionCommit: ACTION, originalBundlePath: bundlePath,
    originalBundleBytes: raw.length, originalBundleSHA256: BUNDLE_SHA,
    inMemoryBootstrapSHA256: digest(Buffer.from(exposed)), substitutions: 1,
    fullByteInverseSHA256: BUNDLE_SHA, originalLibraryFunctionChanges: 0, installedCacheWrites: 0}};
}
function verifyAuthoredFiles(control, commit) {
  const paths = [
    'Tools/PinkhaDualEngineRuntime/hosted_shared_build/native_stream.py',
    'Tools/PinkhaDualEngineRuntime/hosted_shared_build/native_stream_action/action.yml',
    'Tools/PinkhaDualEngineRuntime/hosted_shared_build/native_stream_action/upload_stream.cjs',
  ];
  const result = {};
  for (const relative of paths) {
    const filename = path.join(control, relative);
    requireValue(fs.realpathSync(filename) === filename && fs.lstatSync(filename).isFile(), 'Physical authored stream source required');
    const actual = fs.readFileSync(filename);
    const original = cp.execFileSync('git', ['--no-replace-objects', '-C', control, 'show', `${commit}:${relative}`], {maxBuffer: MiB});
    requireValue(actual.equals(original), 'Authored stream source differs from exact Git commit');
    result[relative] = {bytes: actual.length, sha256: digest(actual)};
  }
  requireValue(fs.realpathSync(__filename) === path.join(control, paths[2]), 'Running local action does not belong to the exact control checkout');
  return result;
}
class OwnedGroup {
  constructor(pid) {
    requireValue(Number.isSafeInteger(pid) && pid > 1, 'Concrete owned process group required');
    this.pid = pid;
    this.absent = false;
    this.observations = [];
    this.signals = [];
  }
  probe() {
    if (this.absent) return false; // Latched: never re-probe a potentially reused ID.
    try {
      process.kill(-this.pid, 0);
      this.observations.push({time: Date.now(), status: 'PRESENT'});
      return true;
    } catch (error) {
      requireValue(error.code === 'ESRCH', 'Owned group absence could not be established');
      this.absent = true;
      this.observations.push({time: Date.now(), status: 'ABSENT_ESRCH_LATCHED'});
      return false;
    }
  }
  signal(name) {
    if (!this.probe()) return;
    try {
      process.kill(-this.pid, name);
      this.signals.push({time: Date.now(), signal: name, status: 'SENT_TO_EXACT_OWNED_GROUP'});
    } catch (error) {
      requireValue(error.code === 'ESRCH', 'Could not signal the exact owned group');
      this.absent = true;
      this.observations.push({time: Date.now(), status: 'ABSENT_ESRCH_LATCHED_DURING_SIGNAL'});
    }
  }
  async waitAbsent(milliseconds) {
    const end = Date.now() + milliseconds;
    while (this.probe()) {
      if (Date.now() >= end) return false;
      await delay(100);
    }
    return true;
  }
  async stopAndDrain() {
    if (!this.probe()) return true;
    this.signal('SIGTERM');
    if (await this.waitAbsent(3000)) return true;
    this.signal('SIGKILL');
    return this.waitAbsent(3000);
  }
  proof() {
    return {ownedGroupID: this.pid, status: this.absent ? 'ABSENT_ESRCH_LATCHED' : 'UNRESOLVED_RETAIN_CUSTODY',
      observations: this.observations, signals: this.signals};
  }
}
function cleanupFIFO(root, owner) {
  requireValue(owner.absent, 'Owned process group must be absent before FIFO cleanup');
  const readyPath = path.join(root, 'source-stream-ready.json');
  if (!fs.existsSync(readyPath)) return;
  const ready = JSON.parse(fs.readFileSync(readyPath));
  const filename = path.join(root, 'original-source-archive.pipe');
  requireValue(fs.existsSync(filename), 'Expected owned FIFO disappeared before recorded cleanup');
  const state = fs.lstatSync(filename);
  requireValue(state.isFIFO() && state.ino === ready.fifo.inode && state.dev === ready.fifo.device &&
    state.uid === process.getuid() && (state.mode & 0o777) === 0o600 && ready.fifo.path === filename,
    'Refuse cleanup of a replaced or foreign FIFO');
  fs.unlinkSync(filename);
  jsonFile(path.join(root, 'fifo-cleanup-node.json'), {status: 'PASS_REMOVED_ONLY_THIS_EXACT_OWNED_FIFO', fifo: ready.fifo});
}

async function main() {
  if (process.argv[2] === '--verify-library-only') {
    const {proof} = loadOriginal(process.argv[3]);
    process.stdout.write(JSON.stringify({...proof, status: 'PASS_OFFLINE_ORIGINAL_LIBRARY_EXPORTS_NOT_NETWORK_OR_ARTIFACT_ACCEPTANCE'}) + '\n');
    return;
  }
  requireValue(process.platform === 'darwin' && process.arch === 'arm64' && process.getuid() !== 0 &&
    process.env.RUNNER_NAME === 'pinkha-scaleway-mac' && process.env.RUNNER_ENVIRONMENT === 'self-hosted' &&
    process.env.GITHUB_REPOSITORY === 'davidpovarsky/anytype-swift', 'Existing owner Mac Actions context required');
  const control = fs.realpathSync(process.env.INPUT_CONTROL);
  const planPath = fs.realpathSync(process.env.INPUT_PLAN);
  const planSHA = process.env.INPUT_PLAN_SHA256;
  const root = path.resolve(process.env.INPUT_OUTPUT);
  const runID = process.env.GITHUB_RUN_ID, attempt = process.env.GITHUB_RUN_ATTEMPT;
  requireValue(/^[0-9]+$/.test(runID) && /^[0-9]+$/.test(attempt) && /^[0-9a-f]{64}$/.test(planSHA), 'Exact run/plan identity required');
  requireValue(root === path.join(fs.realpathSync(process.env.RUNNER_TEMP), `pinkha-native8ac-stream-export-${runID}-${attempt}`) &&
    !fs.existsSync(root), 'Fresh exact source-stream claim required');
  const planBytes = fs.readFileSync(planPath);
  requireValue(digest(planBytes) === planSHA, 'Original root plan bytes differ');
  const plan = JSON.parse(planBytes);
  requireValue(plan.controlCommit === process.env.GITHUB_SHA && plan.readyForExport === true,
    'Exact root-approved source stream plan required');
  const authored = verifyAuthoredFiles(control, plan.controlCommit);
  const bundlePath = path.resolve(process.env.RUNNER_WORKSPACE, '..', '_actions', 'actions', 'upload-artifact', ACTION, 'dist', 'upload', 'index.js');
  requireValue(fs.realpathSync(bundlePath) === bundlePath, 'Physical pinned artifact library required');
  const {library, proof} = loadOriginal(bundlePath);
  const {core} = library;
  // Runtime capability remains inside this one existing Actions process. The
  // Python producer and the Oracle relay receive only nonsecret identity keys.
  core.setSecret(process.env.ACTIONS_RUNTIME_TOKEN || '');
  process.env.ACTIONS_ARTIFACT_UPLOAD_CONCURRENCY = '2';
  const envKeys = ['PATH', 'HOME', 'TMPDIR', 'RUNNER_TEMP', 'RUNNER_NAME', 'RUNNER_ENVIRONMENT',
    'GITHUB_REPOSITORY', 'GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT'];
  const childEnv = {PYTHONDONTWRITEBYTECODE: '1', GIT_OPTIONAL_LOCKS: '0'};
  for (const key of envKeys) if (process.env[key] !== undefined) childEnv[key] = process.env[key];
  const python = cp.spawn('python3', ['-B', path.join(control, 'Tools/PinkhaDualEngineRuntime/hosted_shared_build/native_stream.py'),
    '--control', control, '--plan', planPath, '--plan-sha256', planSHA, '--output', root],
    {env: childEnv, stdio: ['ignore', 'pipe', 'pipe'], detached: true});
  const owner = new OwnedGroup(python.pid);
  let childTerminal = null, stderr = '', stderrTruncated = false, zip = null, uploadStream = null, maximumRSS = 0;
  let primaryFailure = null, fifoCleaned = false;
  const childDone = new Promise(resolve => {
    python.once('error', error => {childTerminal = {code: null, signal: null, errorType: error.name}; resolve(childTerminal);});
    python.once('close', (code, signal) => {childTerminal = {code, signal}; resolve(childTerminal);});
  });
  python.stderr.on('data', data => {
    if (!stderrTruncated) stderr += data.toString('utf8');
    if (Buffer.byteLength(stderr) > MiB) {
      stderr = Buffer.from(stderr).subarray(0, MiB).toString('utf8');
      stderrTruncated = true;
      try { owner.signal('SIGTERM'); } catch (_) {}
    }
  });
  const started = Date.now();
  let watchdogFailure = null;
  const onSignal = () => {
    watchdogFailure = new Error('Owned action received termination');
    if (uploadStream) uploadStream.destroy(watchdogFailure);
    if (zip) zip.abort();
    try { owner.signal('SIGTERM'); } catch (_) {}
  };
  process.on('SIGTERM', onSignal);
  process.on('SIGINT', onSignal);
  const watchdog = setInterval(() => {
    try {
      const measuredPIDs = owner.absent ? String(process.pid) : `${process.pid},${python.pid}`;
      const rssText = cp.execFileSync('/bin/ps', ['-o', 'rss=', '-p', measuredPIDs], {encoding: 'utf8', timeout: 3000});
      const rss = rssText.trim().split(/\s+/).filter(Boolean).reduce((sum, value) => sum + Number(value) * 1024, 0);
      maximumRSS = Math.max(maximumRSS, rss);
      requireValue(Number.isFinite(rss) && rss <= MAX_RSS, 'Owned source uploader exceeded its bounded RSS');
      requireValue(Date.now() - started < LIMIT_SECONDS * 1000, 'Owned source uploader deadline expired');
    } catch (error) {
      watchdogFailure = error;
      if (uploadStream) uploadStream.destroy(error);
      if (zip) zip.abort();
      try { owner.signal('SIGTERM'); } catch (_) {}
    }
  }, 2000);
  try {
    const sourceQualified = path.join(root, 'source-archive-qualified.json');
    while (!fs.existsSync(sourceQualified)) {
      requireValue(!watchdogFailure, 'Owned stream watchdog failed before upload');
      requireValue(childTerminal === null, 'Original native stream producer failed before artifact creation');
      await delay(250);
    }
    const qualified = JSON.parse(fs.readFileSync(sourceQualified));
    requireValue(qualified.status === 'PASS_EXACT_ORIGINAL_SOURCE_ARCHIVE_IN_MEMORY_NOT_APP_ACCEPTANCE' &&
      qualified.sourceArchiveSHA256 === 'c70592e4ae160cbb5cb8eda3cb1caed08f727476a5c9fac7c207593cd9315830' &&
      qualified.sourceFiles === 4868 && qualified.controlCommit === plan.controlCommit && qualified.planSHA256 === planSHA,
      'Original qualified source stream receipt differs');
    jsonFile(path.join(root, 'original-artifact-library.json'), {...proof, authoredFiles: authored});
    const ids = library.util.getBackendIdsFromToken();
    const client = library.client.internalArtifactTwirpClient();
    const name = `Pinkha-Native8ac-Inputs-${runID}-${attempt}`;
    const create = await client.CreateArtifact({...ids, name, version: 4, expiresAt: library.retention.getExpiration(30)});
    requireValue(create.ok, 'Original Actions artifact creation failed');
    library.util.maskSigUrl(create.signedUploadUrl);
    // Same original archiver/ZipUploadStream/8MiB transport implementation;
    // the only ZIP member is a genuine producer Readable, never a fake path.
    zip = library.archiver.create('zip', {highWaterMark: 8 * MiB, zlib: {level: 0}});
    uploadStream = new library.zip.ZipUploadStream(8 * MiB);
    zip.on('error', error => uploadStream.destroy(error));
    zip.on('warning', error => uploadStream.destroy(error));
    python.stdout.on('error', error => uploadStream.destroy(error));
    zip.append(python.stdout, {name: 'native8ac-inputs.tar.gz', store: true});
    zip.pipe(uploadStream);
    const finalizedZip = zip.finalize();
    const uploaded = await library.blob.uploadZipToBlobStorage(create.signedUploadUrl, uploadStream);
    await finalizedZip;
    const terminal = await childDone;
    requireValue(!watchdogFailure && !stderrTruncated && terminal.code === 0 && terminal.signal === null,
      'Original source producer did not complete; artifact is not finalized');
    clearInterval(watchdog);
    requireValue(await owner.waitAbsent(3000), 'Owned process group remains after producer exit; artifact is not finalized');
    const receiptBytes = fs.readFileSync(path.join(root, 'receipt.json'));
    const receipt = JSON.parse(receiptBytes);
    requireValue(receipt.status === 'PASS_ORIGINAL_NATIVE8AC_STREAM_NOT_DOWNLOADED_ARTIFACT_OR_APP_ACCEPTANCE' &&
      receipt.sourceBeforeEqualsAfter === true && receipt.controlCommit === plan.controlCommit &&
      receipt.rootPlan.sha256 === planSHA && receipt.archiveDiskBytes === 0 && receipt.restoredSourceDiskBytes === 0,
      'Actual completed source stream proof differs');
    requireValue(uploaded.uploadSize > 0 && /^[0-9a-f]{64}$/.test(uploaded.sha256Hash), 'Original upload byte/hash result missing');
    cleanupFIFO(root, owner);
    fifoCleaned = true;
    jsonFile(path.join(root, 'owned-group-drain.json'), owner.proof());
    const final = await client.FinalizeArtifact({...ids, name, size: String(uploaded.uploadSize),
      hash: library.generated.StringValue.create({value: `sha256:${uploaded.sha256Hash}`})});
    requireValue(final.ok && /^[0-9]+$/.test(String(final.artifactId)), 'Original artifact finalization failed');
    jsonFile(path.join(root, 'actions-artifact.json'), {
      status: 'PASS_FINALIZED_ORIGINAL_NATIVE8AC_STREAM_ARTIFACT_NOT_DOWNLOADED_OR_APP_ACCEPTANCE',
      artifactID: String(final.artifactId), artifactDigest: uploaded.sha256Hash, artifactBytes: uploaded.uploadSize,
      artifactName: name, runID, runAttempt: attempt, controlCommit: plan.controlCommit,
      nativeStreamReceiptSHA256: digest(receiptBytes), payload: receipt.payload,
      payloadManifestSHA256: receipt.payloadManifestSHA256, maximumObservedCombinedRSSBytes: maximumRSS,
      ownedGroup: owner.proof(), fifoCleanedAfterGroupAbsence: true,
      archiveDiskBytes: 0, restoredSourceDiskBytes: 0, nativeBuildsNow: 0, testsExecuted: 0,
    });
    core.setOutput('artifact-id', String(final.artifactId));
    core.setOutput('artifact-digest', uploaded.sha256Hash);
    core.info(`Finalized exact native8ac input artifact ${final.artifactId}; hosted download qualification remains required.`);
  } catch (error) {
    primaryFailure = new Error('Exact native8ac streaming export failed; no App/native/test acceptance was granted.');
    const sanitizedMessage = String(error.message).replaceAll(process.env.ACTIONS_RUNTIME_TOKEN || 'NO_RUNTIME_CAPABILITY', '<runtime-capability>')
      .replace(/https?:\/\/[^\s"'<>]+/g, '<redacted-url>');
    if (fs.existsSync(root)) try { jsonFile(path.join(root, 'artifact-stream-failure.json'), {
      status: 'FAIL_OR_INCOMPLETE_NATIVE_ARTIFACT_STREAM', errorType: error.name,
      // Never serialize an upstream Error/response carrying a signed URL.
      reason: 'The source-stream or original artifact operation failed; original producer stderr and receipts are retained.',
      sanitizedOriginalMessage: sanitizedMessage,
      childTerminal, maximumObservedCombinedRSSBytes: maximumRSS, finalizedAcceptance: false,
    }); } catch (_) { /* Preserve the primary failure even if evidence storage failed. */ }
    throw primaryFailure;
  } finally {
    clearInterval(watchdog);
    process.removeListener('SIGTERM', onSignal);
    process.removeListener('SIGINT', onSignal);
    const cleanupErrors = [];
    try { if (zip) zip.abort(); } catch (error) { cleanupErrors.push(error.name); }
    try { if (uploadStream) uploadStream.destroy(); } catch (error) { cleanupErrors.push(error.name); }
    try { await owner.stopAndDrain(); } catch (error) { cleanupErrors.push(error.name); }
    await Promise.race([childDone, delay(3000)]);
    if (fs.existsSync(root)) {
      try { fs.writeFileSync(path.join(root, 'producer.original.stderr.log'), stderr, {flag: 'wx', mode: 0o600}); }
      catch (error) { cleanupErrors.push(error.name); }
      if (owner.absent && !fifoCleaned) {
        try { cleanupFIFO(root, owner); fifoCleaned = true; } catch (error) { cleanupErrors.push(error.name); }
      }
      try { jsonFile(path.join(root, 'producer-terminal.json'), {ownedPID: python.pid, terminal: childTerminal,
        ownedGroup: owner.proof(), fifoCleanedAfterGroupAbsence: fifoCleaned,
        cleanupErrors, maximumObservedCombinedRSSBytes: maximumRSS, stderrTruncated,
        runtimeCredentialsPassedToProducer: false}); } catch (error) { cleanupErrors.push(error.name); }
    }
    if (!primaryFailure && (!owner.absent || cleanupErrors.length)) throw new Error('Original export cleanup/custody remains incomplete.');
  }
}

if (require.main === module) main().catch(error => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
module.exports = {loadOriginal, digest, STARTUP, EXPOSE, OwnedGroup};
