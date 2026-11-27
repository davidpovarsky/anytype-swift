'use strict';
// Real production await-boundary helper with an in-memory client; no artifact API.
const assert = require('node:assert/strict');
const {FailureJournal, createArtifactWhenHealthy} = require('./native_stream_action/upload_stream.cjs');
async function main() {
  let createCalls = 0, streamContinuations = 0;
  const prior = new FailureJournal(null), first = new Error('original watchdog before source-qualified continuation');
  prior.record(first, {origin: 'watchdog'});
  await assert.rejects(createArtifactWhenHealthy(prior, {CreateArtifact() { createCalls++; }}, {}), e => e === first);
  assert.equal(createCalls, 0);
  const during = new FailureJournal(null), signal = new Error('original action signal while CreateArtifact awaits');
  let release;
  const pending = createArtifactWhenHealthy(during, {CreateArtifact(request) {
    createCalls++; assert.deepEqual(request, {version: 4, name: 'control-only'});
    return new Promise(resolve => { release = resolve; });
  }}, {version: 4, name: 'control-only'}).then(value => { streamContinuations++; return value; });
  during.record(signal, {origin: 'action-signal', signal: 'SIGTERM'});
  release({ok: true, signedUploadUrl: 'not-used-control-only'});
  await assert.rejects(pending, e => e === signal);
  assert.equal(during.firstError, signal);
  assert.equal(createCalls, 1); assert.equal(streamContinuations, 0);
  const healthy = await createArtifactWhenHealthy(new FailureJournal(null), {
    async CreateArtifact(request) { return {ok: true, originalRequest: request}; },
  }, {version: 4});
  assert.deepEqual(healthy, {ok: true, originalRequest: {version: 4}});
  process.stdout.write(JSON.stringify({status: 'PASS_ORIGINAL_CREATE_AWAIT_BOUNDARY_CONTROLLER_ONLY',
    method: 'latchedFailurePreventsCreateOrPostAwaitStreams', stoppedBeforeCreate: true,
    stoppedDuringCreateAwait: true, streamContinuations, realArtifactCalls: 0, appleTests: 0}) + '\n');
}
main().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
