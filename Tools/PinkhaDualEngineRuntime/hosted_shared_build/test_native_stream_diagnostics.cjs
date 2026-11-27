'use strict';
// Portable controller regressions only. No artifact, Apple, or network call.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {OwnedGroup, FailureJournal, errorDetails, psOutput} = require('./native_stream_action/upload_stream.cjs');

const outcomes = [];
async function test(name, body) {
  await body(); outcomes.push({name, status: 'PASS'});
}
function syscall(code) { return Object.assign(new Error(`kill ${code}`), {code, errno: code === 'EPERM' ? -1 : -3, syscall: 'kill'}); }
async function withKill(replacement, body) {
  const original = process.kill; process.kill = replacement;
  try { await body(); } finally { process.kill = original; }
}
async function main() {
  await test('firstPSFailureSurvivesLaterSignalAndCleanup', async () => {
    const journal = new FailureJournal(null);
    const first = Object.assign(new Error('spawnSync /bin/ps ETIMEDOUT'), {
      code: 'ETIMEDOUT', errno: -60, syscall: 'spawnSync /bin/ps', status: null, signal: 'SIGTERM',
    });
    const raw = {stdout: psOutput(' 32768\n'), stderr: psOutput('ps: original diagnostic\n')};
    assert(journal.record(first, {origin: 'watchdog', ps: {argv: ['-o', 'rss=', '-p', '101,102'], ...raw}}));
    const frozen = JSON.stringify(journal.first);
    await Promise.resolve().then(() => journal.record(new Error('Owned action received termination'), {origin: 'action-signal', signal: 'SIGTERM'}));
    await Promise.resolve().then(() => journal.record(syscall('EPERM'), {origin: 'cleanup-owned-group'}));
    assert.equal(journal.firstError, first);
    assert.equal(JSON.stringify(journal.first), frozen);
    assert.equal(journal.first.error.code, 'ETIMEDOUT');
    assert.equal(journal.first.error.status, null);
    assert.equal(journal.first.ps.stderr.text, 'ps: original diagnostic\n');
    assert.equal(journal.laterCount, 2);
  });
  await test('receiptFailurePreservesFirstErrorAndExistingFile', async () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pinkha-stream-diagnostic-control-'));
    const target = path.join(root, 'first-stream-failure.json');
    fs.writeFileSync(target, 'original retained partial receipt\n', {flag: 'wx'});
    try {
      const journal = new FailureJournal(root), first = new Error('first unchanged failure');
      journal.record(first, {origin: 'watchdog'});
      assert.equal(journal.firstError, first);
      assert.equal(journal.receiptErrors[0].error.code, 'EEXIST');
      assert.equal(fs.readFileSync(target, 'utf8'), 'original retained partial receipt\n');
    } finally { fs.rmSync(root, {recursive: true}); }
  });
  await test('darwinEPERMWaitsReadOnlyForActualESRCHThenLatches', async () => {
    const owner = new OwnedGroup(424242), signals = []; let count = 0;
    await withKill((pid, signal) => {
      assert.equal(pid, -424242); if (signal !== 0) signals.push(signal);
      if (count++ === 0) throw syscall('EPERM'); throw syscall('ESRCH');
    }, async () => {
      assert.equal(await owner.waitAbsent(3000), true);
      assert.equal(owner.absent, true);
      assert.equal(owner.indeterminate, true);
      assert.equal(owner.proof().observations[0].error.code, 'EPERM');
      assert.equal(owner.proof().observations.at(-1).status, 'ABSENT_ESRCH_LATCHED');
      assert.deepEqual(signals, []);
    });
    await withKill(() => { throw new Error('Latched group must not be reprobed'); }, async () => {
      assert.equal(owner.probe(), false); owner.signal('SIGTERM');
      assert.equal(await owner.stopAndDrain(), true);
    });
  });
  await test('persistentEPERMDoesNotPassOrSignal', async () => {
    const owner = new OwnedGroup(424243), signals = [];
    await withKill((pid, signal) => {
      assert.equal(pid, -424243); if (signal !== 0) signals.push(signal); throw syscall('EPERM');
    }, async () => {
      assert.equal(await owner.waitAbsent(0), false);
      assert.equal(owner.absent, false);
      assert.throws(() => owner.signal('SIGKILL'), {code: 'EPERM'});
      assert.deepEqual(signals, []);
    });
  });
  await test('apparentPresenceAfterEPERMDoesNotRestoreSignalAuthority', async () => {
    const owner = new OwnedGroup(424244), calls = []; let stage = 0;
    await withKill((pid, signal) => {
      calls.push({pid, signal});
      if (stage === 0) throw syscall('EPERM');
      if (stage === 1) return true;
      throw syscall('ESRCH');
    }, async () => {
      assert.throws(() => owner.probe(), {code: 'EPERM'}); stage = 1;
      assert.throws(() => owner.signal('SIGTERM'), /Signals withheld/);
      assert(calls.every(row => row.signal === 0)); stage = 2;
      assert.equal(await owner.waitAbsent(0), true);
    });
  });
  await test('signalEPERMRacePreservesActualErrorAndRequiresESRCH', async () => {
    const owner = new OwnedGroup(424245); let absent = false;
    await withKill((pid, signal) => {
      assert.equal(pid, -424245);
      if (absent) throw syscall('ESRCH');
      if (signal === 0) return true;
      throw syscall('EPERM');
    }, async () => {
      assert.throws(() => owner.signal('SIGTERM'), {code: 'EPERM'});
      assert.equal(owner.absent, false);
      assert.equal(owner.proof().signals[0].status, 'INDETERMINATE_NOT_CONFIRMED_SIGNAL');
      absent = true; assert.equal(await owner.waitAbsent(0), true);
    });
  });
  await test('unrelatedProbeErrorIsNeverConvertedToAbsence', async () => {
    const owner = new OwnedGroup(424246);
    await withKill(() => { throw syscall('EINVAL'); }, async () => {
      await assert.rejects(owner.waitAbsent(0), {code: 'EINVAL'});
      assert.equal(owner.absent, false);
    });
  });
  await test('boundedLaterDiagnosticsAndCapabilityRedaction', async () => {
    const previous = process.env.ACTIONS_RUNTIME_TOKEN; process.env.ACTIONS_RUNTIME_TOKEN = 'control-only-fake-capability';
    try {
      const journal = new FailureJournal(null);
      journal.record(new Error('first control-only-fake-capability https://invalid.example/signed?q=control'), {origin: 'main'});
      for (let i = 0; i < 40; i++) journal.record(new Error(`later${i}`), {origin: 'cleanup'});
      assert(!JSON.stringify(journal.proof()).includes('control-only-fake-capability'));
      assert(!JSON.stringify(journal.proof()).includes('https://'));
      assert.equal(journal.later.length, 32); assert.equal(journal.laterCount, 40);
      assert.equal(journal.proof().laterTruncated, true);
      assert.equal(errorDetails({name: 'Error', message: 'exact', code: 'EPERM', status: null}).status, null);
    } finally { if (previous === undefined) delete process.env.ACTIONS_RUNTIME_TOKEN; else process.env.ACTIONS_RUNTIME_TOKEN = previous; }
  });
  process.stdout.write(JSON.stringify({status: 'PASS_PORTABLE_CONTROLLER_REGRESSIONS_NOT_STREAM_OR_APP_ACCEPTANCE',
    methods: outcomes.length, outcomes, appleTests: 0, uploads: 0}) + '\n');
}
main().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
