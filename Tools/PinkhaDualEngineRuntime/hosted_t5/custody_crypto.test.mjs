/** AUTHORED_NOT_RUN. Local disposable bytes only; no account/runtime fixtures. */
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {canonical, runtimeIdentity, fileHash, seal, restore} from './custody_crypto.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const spki = 'f101e91b46c3389438f69ca00aaf3608f829a34219d84453ff3b36c518361c6a';
const recipient = path.join(here, 'recipient-public.pem');
function fixture() {
  const output = fs.mkdtempSync(path.join(os.tmpdir(), 'pinkha-t5-crypto-control-')); fs.chmodSync(output, 0o700);
  fs.mkdirSync(path.join(output, 'evidence'), {mode: 0o700}); fs.mkdirSync(path.join(output, 'ciphertext'), {mode: 0o700});
  fs.writeFileSync(path.join(output, 'evidence/original.txt'), 'disposable exact original control bytes\n', {mode: 0o600});
  const binding = {sourceCommit: 'a'.repeat(40), controlFixture: 'not-native-evidence'};
  return {output, binding, plan: {schema: 'pinkha-t5-private-seal-plan-v1', output, processClosure: 'ALL_ORIGINAL_OWNED_GROUPS_ABSENT',
    noFurtherNativeEffects: true, nodeIdentity: runtimeIdentity(), publicKey: recipient, recipientSPKISHA256: spki, binding,
    ciphertext: path.join(output, 'ciphertext/original-private-custody.bin'),
    scopes: [{id: 'original-evidence', kind: 'evidence', root: path.join(output, 'evidence')}]}};
}

test('ciphertext seal preserves original evidence and refuses replacement', () => {
  const item = fixture(); const before = fileHash(path.join(item.output, 'evidence/original.txt'));
  const result = seal(item.plan); const originalCipher = fileHash(item.plan.ciphertext);
  assert.equal(result.status, 'PASS_AUTHENTICATED_PRIVATE_CIPHERTEXT_NOT_RESTORED');
  assert.equal(result.originalDataDeleted, false); assert.equal(result.restoredBytesVerified, false);
  assert.throws(() => seal(item.plan));
  assert.equal(fileHash(item.plan.ciphertext), originalCipher);
  assert.equal(fileHash(path.join(item.output, 'evidence/original.txt')), before);
});

test('unowned scope and mismatched Node are rejected before a ciphertext is created', () => {
  const item = fixture();
  assert.throws(() => seal({...item.plan, scopes: [{id: 'original-evidence', kind: 'evidence', root: os.tmpdir()}]}));
  assert.throws(() => seal({...item.plan, nodeIdentity: {...item.plan.nodeIdentity, executableSHA256: '0'.repeat(64)}}));
  assert.equal(fs.existsSync(item.plan.ciphertext), false);
});

test('a private scope symlink never expands the finite owned input', () => {
  const item = fixture(); fs.symlinkSync(os.tmpdir(), path.join(item.output, 'evidence/foreign'));
  assert.throws(() => seal(item.plan)); assert.equal(fs.existsSync(item.plan.ciphertext), false);
});

// Receiver cases require the root's explicit LOCAL Mac plan. The key is never
// embedded, read on hosted CI, transferred or replaced by a synthetic pass.
const receiverPlan = process.env.PINKHA_T5_LOCAL_RECEIVER_CONTROL_PLAN;
function receiver(item, result, suffix) {
  const selected = JSON.parse(fs.readFileSync(receiverPlan));
  assert.deepEqual(selected.nodeIdentity, runtimeIdentity());
  return {schema: 'pinkha-t5-private-restore-plan-v1', privateKey: selected.privateKey,
    parent: selected.parent, destination: path.join(selected.parent, 'control-' + suffix + '-' + crypto.randomBytes(8).toString('hex')),
    nodeIdentity: selected.nodeIdentity, ciphertext: item.plan.ciphertext, ciphertextSHA256: result.ciphertextSHA256,
    binding: item.binding, inventorySHA256: result.inventorySHA256};
}

test('authenticated receiver restores exact file bytes and refuses an existing destination', {skip: !receiverPlan}, () => {
  const item = fixture(); const result = seal(item.plan); const plan = receiver(item, result, 'exact');
  const actual = restore(plan);
  assert.equal(actual.status, 'PASS_AUTHENTICATED_PRIVATE_RESTORE_EXACT_BYTES_NOT_RETIREMENT');
  assert.deepEqual(fs.readFileSync(path.join(plan.destination, 'original-evidence/original.txt')),
                   fs.readFileSync(path.join(item.output, 'evidence/original.txt')));
  assert.equal(actual.retirementAuthorized, false); assert.throws(() => restore(plan));
});

test('tampered GCM ciphertext creates no plaintext file or destination', {skip: !receiverPlan}, () => {
  const item = fixture(); const result = seal(item.plan); const plan = receiver(item, result, 'tampered');
  const raw = fs.readFileSync(plan.ciphertext); raw[raw.length - 17] ^= 1;
  const corrupt = plan.ciphertext + '.corrupt'; fs.writeFileSync(corrupt, raw, {mode: 0o600});
  const before = fs.readdirSync(plan.parent).sort();
  assert.throws(() => restore({...plan, ciphertext: corrupt, ciphertextSHA256: fileHash(corrupt)}));
  assert.equal(fs.existsSync(plan.destination), false); assert.deepEqual(fs.readdirSync(plan.parent).sort(), before);
});
