'use strict';
// Bounded same-runner controller probe. Exact successor source arrives on stdin;
// no action main, Git checkout, artifact, FIFO, or filesystem mutation is used.
const fs = require('node:fs');
const crypto = require('node:crypto');
const Module = require('node:module');
const cp = require('node:child_process');
const assert = require('node:assert/strict');
const source = fs.readFileSync(0);
const expected = '3d8b949047ce66303f2b0bf519d5209c11a76a4a9321e899f54fcbb0dfd7ad04';
assert.equal(crypto.createHash('sha256').update(source).digest('hex'), expected);
assert.equal(process.execPath, '/Users/m1/actions-runner-anytype/externals/node24/bin/node');
assert.equal(process.version, 'v24.22.1');
assert.equal(process.platform, 'darwin');
const instance = new Module('pinkha-stream-custody-successor-probe', module);
instance.filename = 'pinkha-stream-custody-successor-probe.cjs';
instance.paths = [];
instance._compile(source.toString('utf8'), instance.filename);
const {OwnedGroup} = instance.exports;
async function main() {
  const child = cp.spawn('/bin/sleep', ['5'], {env: {PATH: '/usr/bin:/bin'}, stdio: 'ignore', detached: true});
  const done = new Promise(resolve => {
    child.once('error', e => resolve({error: {name: e.name, code: e.code}}));
    child.once('close', (code, signal) => resolve({code, signal}));
  });
  await new Promise((resolve, reject) => { child.once('spawn', resolve); child.once('error', reject); });
  const owner = new OwnedGroup(child.pid);
  const receipt = {sourceSHA256: expected, node: process.execPath, nodeVersion: process.version,
    ownedPID: child.pid, startedAt: new Date().toISOString(), appleTests: 0, artifactCalls: 0,
    historicalGroupsProbed: false, sourceOrCacheWrites: 0};
  try {
    assert.equal(owner.probe(), true);
    receipt.drained = await owner.stopAndDrain();
    receipt.terminal = await done;
    assert.equal(receipt.drained, true);
    assert.equal(owner.absent, true);
    const originalKill = process.kill;
    process.kill = () => { throw new Error('No system call allowed after ESRCH latch'); };
    try { assert.equal(owner.probe(), false); owner.signal('SIGTERM'); assert.equal(await owner.stopAndDrain(), true); }
    finally { process.kill = originalKill; }
    receipt.status = 'PASS_ACTUAL_NODE24_SUCCESSOR_OWNED_DRAIN_ONLY';
  } catch (e) {
    receipt.status = 'FAIL_OR_INCOMPLETE_NODE24_SUCCESSOR_OWNED_DRAIN';
    receipt.error = {name: e.name, message: e.message, code: e.code};
  } finally {
    if (!owner.absent) {
      try { receipt.finalDrain = await owner.stopAndDrain(); }
      catch (e) { receipt.finalDrainError = {name: e.name, message: e.message, code: e.code}; }
      receipt.terminal = await done;
    }
    receipt.group = owner.proof();
    receipt.finishedAt = new Date().toISOString();
    process.stdout.write(JSON.stringify(receipt) + '\n');
  }
}
main().catch(e => { process.stderr.write(JSON.stringify({name: e.name, message: e.message, code: e.code}) + '\n'); process.exitCode = 1; });
