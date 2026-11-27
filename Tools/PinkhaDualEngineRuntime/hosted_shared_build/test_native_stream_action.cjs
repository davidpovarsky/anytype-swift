'use strict';
// One actual owned local child plus the ESRCH latch. No network/Apple operation.
const assert = require('node:assert/strict');
const cp = require('node:child_process');
const {once} = require('node:events');
const {OwnedGroup} = require('./native_stream_action/upload_stream.cjs');

async function main() {
  const child = cp.spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], {
    stdio: 'ignore', detached: true,
  });
  const closed = once(child, 'close');
  const owner = new OwnedGroup(child.pid);
  try {
    assert.equal(owner.probe(), true);
    assert.equal(await owner.stopAndDrain(), true);
    await closed;
    assert.equal(owner.absent, true);
    assert.match(owner.proof().observations.at(-1).status, /ABSENT_ESRCH_LATCHED/);
    assert(owner.proof().signals.every(item => item.status === 'SENT_TO_EXACT_OWNED_GROUP'));
    const originalKill = process.kill;
    process.kill = () => { throw new Error('Latched group must never be probed/signalled again'); };
    try {
      assert.equal(owner.probe(), false);
      owner.signal('SIGTERM');
      assert.equal(await owner.stopAndDrain(), true);
    } finally { process.kill = originalKill; }
    process.stdout.write(JSON.stringify({status: 'PASS_ACTUAL_OWNED_GROUP_DRAIN_AND_NO_REPROBE_LATCH_CONTROL_ONLY',
      group: owner.proof(), appleTests: 0, artifactUploadCalls: 0}) + '\n');
  } finally {
    if (!owner.absent) await owner.stopAndDrain();
  }
}
main().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1; });
