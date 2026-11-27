/** Bounded private custody. Node built-in crypto only; no private key on hosted CI. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const MAGIC = Buffer.from('PINKHA-T5-CUSTODY-1\n');
const PAYLOAD_MAGIC = Buffer.from('PINKHA-T5-PRIVATE-1\n');
const CHUNK = 1024 * 1024;
const MAX_BYTES = 8 * 1024 ** 3;
const MAX_FILE = 4 * 1024 ** 3;
const MAX_FILES = 65536;
const MAX_MANIFEST = 16 * 1024 ** 2;
const FLOOR = 2 * 1024 ** 3;
const CONCURRENT = 512 * 1024 ** 2;
const SPKI = 'f101e91b46c3389438f69ca00aaf3608f829a34219d84453ff3b36c518361c6a';
const PEM_SHA = '47a137c28c8564ba8c913b00db9a9e47e5669092b7112e10adfec59949cf6853';
const LABEL = Buffer.from('pinkha-hosted-t5-private-custody-v1');
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
function check(condition, code) { if (!condition) { const error = new Error(code); error.code = code; throw error; } }
function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  check(value === null || ['string', 'boolean'].includes(typeof value) || (typeof value === 'number' && Number.isSafeInteger(value)), 'UNSUPPORTED_CANONICAL_VALUE');
  return JSON.stringify(value);
}
function bytes(value) { return Buffer.from(canonical(value)); }
function readJSON(file, maximum = MAX_MANIFEST) {
  const raw = readBounded(file, maximum); const value = JSON.parse(raw.toString());
  check(Buffer.compare(bytes(value), raw) === 0, 'NONCANONICAL_OR_DUPLICATE_JSON');
  return value;
}
function physical(file, directory = false) {
  check(path.isAbsolute(file) && path.normalize(file) === file && fs.realpathSync(file) === file, 'NONPHYSICAL_PATH');
  const stat = fs.lstatSync(file);
  check(!stat.isSymbolicLink() && (directory ? stat.isDirectory() : stat.isFile()), 'WRONG_FILE_KIND');
  return stat;
}
function openRead(file) {
  const before = physical(file); check(before.nlink === 1, 'HARDLINK_NOT_OWNED');
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
  const after = fs.fstatSync(fd);
  check(before.dev === after.dev && before.ino === after.ino, 'READ_IDENTITY_RACE');
  return fd;
}
function readBounded(file, maximum) {
  const fd = openRead(file);
  try { const stat = fs.fstatSync(fd); check(stat.size > 0 && stat.size <= maximum, 'BOUNDED_FILE_REQUIRED'); return fs.readFileSync(fd); }
  finally { fs.closeSync(fd); }
}
function fileHash(file) {
  const fd = openRead(file); const hash = crypto.createHash('sha256'); const buffer = Buffer.alloc(CHUNK);
  try { for (;;) { const count = fs.readSync(fd, buffer, 0, buffer.length, null); if (!count) break; hash.update(buffer.subarray(0, count)); } }
  finally { fs.closeSync(fd); }
  return hash.digest('hex');
}
function runtimeIdentity() {
  const executable = fs.realpathSync(process.execPath);
  check(process.platform === 'darwin' && process.arch === 'arm64', 'ORIGINAL_APPLE_SILICON_CRYPTO_RUNTIME');
  const loaded = process.report.getReport().sharedObjects;
  check(Array.isArray(loaded) && loaded.every(value => typeof value === 'string' && path.isAbsolute(value)), 'ACTUAL_LOADED_IMAGE_LIST');
  // System shared-cache images are OS-bound. Every other loaded image is
  // explicitly hashed, including libnode/libcrypto; the small launcher alone
  // is not a cryptographic runtime identity.
  const physicalImages = [...new Set([executable, ...loaded.filter(value => !value.startsWith('/System/Library/') && !value.startsWith('/usr/lib/'))]
    .map(value => fs.realpathSync(value)))].sort();
  check(physicalImages.length > 0 && physicalImages.length <= 128, 'BOUNDED_NON_SYSTEM_IMAGE_CLOSURE');
  const images = physicalImages.map(value => ({path: value, resolvedPath: value, bytes: physical(value).size, sha256: fileHash(value)}));
  const versionXML = readBounded('/System/Library/CoreServices/SystemVersion.plist', 65536).toString();
  const versions = [...versionXML.matchAll(/<key>ProductVersion<\/key>\s*<string>([0-9]+(?:\.[0-9]+){1,2})<\/string>/g)];
  check(versions.length === 1, 'ACTUAL_MACOS_PRODUCT_VERSION');
  const value = {executable, executableSHA256: images.find(row => row.path === executable).sha256,
    nodeVersion: process.version, opensslVersion: process.versions.openssl, platform: process.platform,
    machine: process.arch, macOS: versions[0][1], images};
  check(bytes(value).length <= 10 * 1024, 'PUBLIC_RUNTIME_IDENTITY_HEADER_BUDGET');
  return value;
}
function publicKey(file) {
  const pem = readBounded(file, 16384); check(sha(pem) === PEM_SHA, 'PUBLIC_PEM_IDENTITY');
  check(pem.toString().startsWith('-----BEGIN PUBLIC KEY-----\n') && !pem.includes(Buffer.from('PRIVATE')), 'PUBLIC_RECIPIENT_ONLY');
  const key = crypto.createPublicKey(pem);
  check(key.asymmetricKeyType === 'rsa' && key.asymmetricKeyDetails.modulusLength === 3072
        && key.asymmetricKeyDetails.publicExponent === 65537n, 'RECIPIENT_RSA3072_REQUIRED');
  const der = key.export({type: 'spki', format: 'der'}); check(sha(der) === SPKI, 'RECIPIENT_FINGERPRINT');
  return key;
}
function hasSpace(directory, additional = 0) {
  const stat = fs.statfsSync(directory, {bigint: true});
  check(stat.bavail * stat.bsize >= BigInt(FLOOR + CONCURRENT + additional), 'PRIVATE_CUSTODY_CAPACITY');
}
function inside(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative !== '' && relative !== '..' && !relative.startsWith('../') && !path.isAbsolute(relative);
}
function safeRelative(value) {
  check(typeof value === 'string' && value.length > 0 && Buffer.byteLength(value) <= 4096
        && !path.isAbsolute(value) && !value.includes('\\') && value.split('/').every(x => x && x !== '.' && x !== '..')
        && !/[\x00-\x1f\x7f]/.test(value), 'UNSAFE_RELATIVE_PATH');
}
function inventory(scopes) {
  const entries = []; let total = 0;
  for (const scope of scopes) {
    physical(scope.root, true); safeRelative(scope.id);
    const visit = (directory, relative) => {
      const st = physical(directory, true);
      check((st.mode & 0o7000) === 0, 'UNSUPPORTED_PRIVATE_DIRECTORY_MODE');
      entries.push({scope: scope.id, path: relative, kind: 'directory', mode: st.mode & 0o777});
      for (const name of fs.readdirSync(directory).sort()) {
        const child = path.join(directory, name); const rel = relative ? relative + '/' + name : name;
        safeRelative(rel); const item = fs.lstatSync(child);
        check(!item.isSymbolicLink(), 'PRIVATE_SYMLINK_REFUSED');
        if (item.isDirectory()) visit(child, rel);
        else {
          check(item.isFile() && item.nlink === 1 && item.size <= MAX_FILE && inside(scope.root, child), 'PRIVATE_SPECIAL_OR_OVERSIZED_FILE');
          check((item.mode & 0o7000) === 0, 'UNSUPPORTED_PRIVATE_FILE_MODE');
          total += item.size; check(total <= MAX_BYTES, 'PRIVATE_TOTAL_LIMIT');
          entries.push({scope: scope.id, path: rel, kind: 'file', mode: item.mode & 0o777, bytes: item.size, sha256: fileHash(child)});
        }
        check(entries.length <= MAX_FILES, 'PRIVATE_FILE_COUNT_LIMIT');
      }
    };
    visit(scope.root, '');
  }
  return {schema: 'pinkha-t5-private-owned-inventory-v1', scopes, entries, totalBytes: total};
}
function validatePlan(plan) {
  check(plan.schema === 'pinkha-t5-private-seal-plan-v1' && plan.processClosure === 'ALL_ORIGINAL_OWNED_GROUPS_ABSENT'
        && plan.noFurtherNativeEffects === true && canonical(plan.nodeIdentity) === canonical(runtimeIdentity()), 'CLOSED_PINNED_NODE_REQUIRED');
  physical(plan.output, true); check((fs.statSync(plan.output).mode & 0o777) === 0o700, 'PRIVATE_OUTPUT_PERMISSIONS');
  check(Array.isArray(plan.scopes) && plan.scopes.length > 0 && plan.scopes.length <= 256, 'FINITE_PRIVATE_SCOPE_REQUIRED');
  const seen = new Set();
  for (const scope of plan.scopes) {
    check(!seen.has(scope.id), 'DUPLICATE_PRIVATE_SCOPE'); seen.add(scope.id);
    if (scope.kind === 'evidence') check(scope.id === 'original-evidence' && scope.root === path.join(plan.output, 'evidence'), 'EVIDENCE_SCOPE_ESCAPED');
    else if (scope.kind === 'command') {
      check(/^command-[0-9]+$/.test(scope.id) && path.dirname(scope.root) === path.join(plan.output, 'commands')
            && path.basename(scope.root) !== 'encrypt-private-custody', 'COMMAND_SCOPE_ESCAPED');
    } else if (scope.kind === 'account') {
      check(['t5-native-ui', 't5-remaining-freshness'].includes(scope.lane) && scope.id === 'account-' + scope.lane, 'FOREIGN_ACCOUNT_SCOPE');
      const observation = readJSON(scope.observation, 65536);
      check(inside(path.join(plan.output, 'evidence/lanes', scope.lane), scope.observation)
            && observation.status === 'ORIGINAL_OWNED_ACCOUNT_SHUTDOWN_OBSERVED'
            && observation.lane === scope.lane && /^[a-fA-F0-9-]{36}$/.test(observation.udid)
            && observation.nativeRoot === scope.root && observation.container === scope.container
            && scope.root === path.join(scope.container, 'Library/Application Support/Anytype/middleware-go'), 'ACCOUNT_CUSTODY_OBSERVATION');
      physical(scope.container, true); check(inside(scope.container, scope.root), 'FOREIGN_ACCOUNT_ROOT');
    } else check(false, 'UNKNOWN_PRIVATE_SCOPE');
    physical(scope.root, true);
  }
  const roots = plan.scopes.map(row => row.root);
  check(roots.every((root, i) => roots.every((other, j) => i === j || (root !== other && !inside(root, other) && !inside(other, root)))), 'OVERLAPPING_PRIVATE_SCOPES');
  check(path.dirname(plan.ciphertext) === path.join(plan.output, 'ciphertext')
        && path.basename(plan.ciphertext) === 'original-private-custody.bin', 'CIPHERTEXT_DESTINATION');
  check(plan.recipientSPKISHA256 === SPKI, 'RECIPIENT_PLAN_FINGERPRINT');
  return publicKey(plan.publicKey);
}
function syncDirectory(directory) { const fd = fs.openSync(directory, 'r'); try { fs.fsyncSync(fd); } finally { fs.closeSync(fd); } }
function writeAll(fd, value) { let at = 0; while (at < value.length) at += fs.writeSync(fd, value, at, value.length - at); }
function seal(plan) {
  const key = validatePlan(plan);
  const inv = inventory(plan.scopes); const inventoryBytes = bytes(inv);
  check(inventoryBytes.length <= MAX_MANIFEST, 'PRIVATE_MANIFEST_LIMIT');
  const length = Buffer.alloc(8); length.writeBigUInt64BE(BigInt(inventoryBytes.length));
  const plaintextBytes = PAYLOAD_MAGIC.length + length.length + inventoryBytes.length + inv.totalBytes;
  hasSpace(plan.output, plaintextBytes + 65536);
  const aesKey = crypto.randomBytes(32), nonce = crypto.randomBytes(12);
  const wrappedKey = crypto.publicEncrypt({key, padding: crypto.constants.RSA_PKCS1_OAEP_PADDING, oaepHash: 'sha256', oaepLabel: LABEL}, aesKey);
  const header = {schema: 'pinkha-t5-rsa3072-oaep-sha256-aes256-gcm-v1', recipientSPKISHA256: SPKI,
    wrappedKey: wrappedKey.toString('base64'), nonce: nonce.toString('base64'), inventorySHA256: sha(inventoryBytes),
    plaintextBytes, binding: plan.binding, nodeIdentity: plan.nodeIdentity};
  const headerBytes = bytes(header), headerSize = Buffer.alloc(4); headerSize.writeUInt32BE(headerBytes.length);
  check(headerBytes.length <= 16384, 'PUBLIC_HEADER_LIMIT');
  const aad = Buffer.concat([MAGIC, headerSize, headerBytes]);
  const cipher = crypto.createCipheriv('aes-256-gcm', aesKey, nonce, {authTagLength: 16}); cipher.setAAD(aad);
  const partial = plan.ciphertext + '.partial-' + crypto.randomBytes(8).toString('hex');
  const fd = fs.openSync(partial, fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_WRONLY, 0o600);
  try {
    writeAll(fd, aad);
    for (const value of [PAYLOAD_MAGIC, length, inventoryBytes]) writeAll(fd, cipher.update(value));
    const scopes = new Map(plan.scopes.map(row => [row.id, row.root])); const buffer = Buffer.alloc(CHUNK);
    for (const row of inv.entries.filter(row => row.kind === 'file')) {
      const input = openRead(path.join(scopes.get(row.scope), row.path)); const before = fs.fstatSync(input);
      const hash = crypto.createHash('sha256'); let actual = 0;
      try {
        for (;;) {
          const count = fs.readSync(input, buffer, 0, buffer.length, null); if (!count) break;
          actual += count; check(actual <= row.bytes, 'SOURCE_GREW_DURING_CUSTODY'); hash.update(buffer.subarray(0, count));
          hasSpace(plan.output); writeAll(fd, cipher.update(buffer.subarray(0, count)));
        }
        const after = fs.fstatSync(input);
        check(before.dev === after.dev && before.ino === after.ino && before.mtimeMs === after.mtimeMs
              && before.ctimeMs === after.ctimeMs && actual === row.bytes && hash.digest('hex') === row.sha256, 'SOURCE_CHANGED_DURING_CUSTODY');
      } finally { fs.closeSync(input); }
    }
    check(canonical(inventory(plan.scopes)) === canonical(inv), 'ORIGINAL_PRIVATE_INVENTORY_CHANGED');
    writeAll(fd, cipher.final()); writeAll(fd, cipher.getAuthTag()); fs.fsyncSync(fd);
  } finally { aesKey.fill(0); fs.closeSync(fd); }
  // Exclusive install, never check-then-replace a prior ciphertext.
  fs.linkSync(partial, plan.ciphertext); fs.unlinkSync(partial); syncDirectory(path.dirname(plan.ciphertext));
  return {status: 'PASS_AUTHENTICATED_PRIVATE_CIPHERTEXT_NOT_RESTORED', schema: header.schema,
    recipientSPKISHA256: SPKI, ciphertextSHA256: fileHash(plan.ciphertext), ciphertextBytes: fs.statSync(plan.ciphertext).size,
    inventorySHA256: header.inventorySHA256, sourceBytes: inv.totalBytes, entryCount: inv.entries.length,
    plaintextUploaded: false, originalDataDeleted: false, restoredBytesVerified: false};
}
function readExact(fd, count, position = null) {
  const value = Buffer.alloc(count); let at = 0;
  while (at < count) { const n = fs.readSync(fd, value, at, count - at, position === null ? null : position + at); check(n > 0, 'TRUNCATED_CUSTODY'); at += n; }
  return value;
}
function qualifyPrivateInventory(invRaw, header) {
  check(sha(invRaw) === header.inventorySHA256, 'AUTHENTICATED_INVENTORY_DIGEST');
  const inv = JSON.parse(invRaw.toString());
  check(bytes(inv).equals(invRaw) && inv.schema === 'pinkha-t5-private-owned-inventory-v1'
        && Array.isArray(inv.scopes) && inv.scopes.length > 0 && inv.scopes.length <= 256 && Array.isArray(inv.entries)
        && inv.entries.length <= MAX_FILES && Number.isSafeInteger(inv.totalBytes) && inv.totalBytes >= 0 && inv.totalBytes <= MAX_BYTES,
        'PRIVATE_INVENTORY_SCHEMA');
  const scopeIDs = new Set(inv.scopes.map(row => row.id));
  check(scopeIDs.size === inv.scopes.length, 'DUPLICATE_RESTORE_SCOPE');
  const seen = new Set(), directories = new Set(); let expectedBytes = 0;
  for (const row of inv.entries) {
    check(scopeIDs.has(row.scope), 'FOREIGN_RESTORE_SCOPE'); safeRelative(row.scope);
    if (row.path) safeRelative(row.path);
    const key = row.scope + '/' + row.path; check(!seen.has(key), 'DUPLICATE_RESTORE_ENTRY'); seen.add(key);
    check(Number.isSafeInteger(row.mode) && row.mode >= 0 && row.mode <= 0o777, 'RESTORE_MODE');
    if (row.path) {
      const parent = path.posix.dirname(row.path);
      check(directories.has(row.scope + '/' + (parent === '.' ? '' : parent)), 'RESTORE_PARENT_NOT_QUALIFIED');
    }
    if (row.kind === 'file') {
      check(row.path && Number.isSafeInteger(row.bytes) && row.bytes >= 0 && row.bytes <= MAX_FILE && /^[a-f0-9]{64}$/.test(row.sha256), 'RESTORE_FILE_BOUNDS');
      expectedBytes += row.bytes;
    } else { check(row.kind === 'directory', 'RESTORE_SPECIAL_FILE_REFUSED'); directories.add(key); }
  }
  check([...scopeIDs].every(id => directories.has(id + '/')), 'RESTORE_SCOPE_ROOT_MISSING');
  check(expectedBytes === inv.totalBytes && PAYLOAD_MAGIC.length + 8 + invRaw.length + expectedBytes === header.plaintextBytes,
        'RESTORE_COMPLETE_PAYLOAD_LENGTH');
  return inv;
}
function restore(plan) {
  check(plan.schema === 'pinkha-t5-private-restore-plan-v1' && canonical(plan.nodeIdentity) === canonical(runtimeIdentity()), 'PINNED_RECEIVER_NODE_REQUIRED');
  check(fileHash(plan.ciphertext) === plan.ciphertextSHA256, 'ORIGINAL_CIPHERTEXT_READBACK');
  const keyStat = physical(plan.privateKey), dirStat = physical(path.dirname(plan.privateKey), true);
  check((keyStat.mode & 0o777) === 0o600 && (dirStat.mode & 0o777) === 0o700 && keyStat.uid === process.getuid()
        && dirStat.uid === process.getuid(), 'PRIVATE_RECIPIENT_PERMISSIONS');
  const key = crypto.createPrivateKey(readBounded(plan.privateKey, 16384));
  check(key.asymmetricKeyType === 'rsa' && key.asymmetricKeyDetails.modulusLength === 3072
        && sha(crypto.createPublicKey(key).export({type: 'spki', format: 'der'})) === SPKI, 'WRONG_PRIVATE_RECIPIENT');
  const source = openRead(plan.ciphertext), originalSourceStat = fs.fstatSync(source), size = originalSourceStat.size;
  let pending, payload, aesKey;
  try {
    check(readExact(source, MAGIC.length).equals(MAGIC), 'UNKNOWN_CIPHERTEXT_FORMAT');
    const headerSizeBytes = readExact(source, 4), headerSize = headerSizeBytes.readUInt32BE();
    check(headerSize > 0 && headerSize <= 16384, 'HEADER_SIZE');
    const rawHeader = readExact(source, headerSize), header = JSON.parse(rawHeader.toString());
    check(bytes(header).equals(rawHeader) && header.schema === 'pinkha-t5-rsa3072-oaep-sha256-aes256-gcm-v1'
          && header.recipientSPKISHA256 === SPKI && canonical(header.binding) === canonical(plan.binding)
          && header.inventorySHA256 === plan.inventorySHA256 && Number.isSafeInteger(header.plaintextBytes)
          && header.plaintextBytes > 0 && header.plaintextBytes <= MAX_BYTES + MAX_MANIFEST + 64, 'AUTHENTICATED_HEADER_BINDING');
    const start = MAGIC.length + 4 + headerSize;
    check(size - start - 16 === header.plaintextBytes, 'CIPHERTEXT_LENGTH');
    const nonce = Buffer.from(header.nonce, 'base64'), wrapped = Buffer.from(header.wrappedKey, 'base64');
    check(nonce.length === 12 && wrapped.length === 384, 'WRAPPED_KEY_OR_NONCE');
    aesKey = crypto.privateDecrypt({key, padding: crypto.constants.RSA_PKCS1_OAEP_PADDING, oaepHash: 'sha256', oaepLabel: LABEL}, wrapped);
    check(aesKey.length === 32, 'WRAPPED_KEY_SIZE');
    const aad = Buffer.concat([MAGIC, headerSizeBytes, rawHeader]);
    const tag = readExact(source, 16, size - 16);
    // First pass authenticates the entire ciphertext and keeps only the bounded
    // private inventory prefix in memory. No plaintext file or destination is
    // created until final GCM authentication AND full inventory qualification.
    const auth = crypto.createDecipheriv('aes-256-gcm', aesKey, nonce, {authTagLength: 16});
    auth.setAAD(aad); auth.setAuthTag(tag);
    const authBuffer = Buffer.alloc(CHUNK), prefix = []; let prefixBytes = 0, authenticatedBytes = 0, at = start;
    function observePlain(value) {
      authenticatedBytes += value.length;
      const keep = Math.min(value.length, MAX_MANIFEST + PAYLOAD_MAGIC.length + 8 - prefixBytes);
      if (keep > 0) { prefix.push(Buffer.from(value.subarray(0, keep))); prefixBytes += keep; }
    }
    while (at < size - 16) {
      const count = fs.readSync(source, authBuffer, 0, Math.min(CHUNK, size - 16 - at), at);
      check(count > 0, 'TRUNCATED_CIPHERTEXT'); at += count; observePlain(auth.update(authBuffer.subarray(0, count)));
    }
    observePlain(auth.final());
    check(authenticatedBytes === header.plaintextBytes, 'AUTHENTICATED_PAYLOAD_LENGTH');
    const authenticatedPrefix = Buffer.concat(prefix);
    check(authenticatedPrefix.subarray(0, PAYLOAD_MAGIC.length).equals(PAYLOAD_MAGIC), 'PRIVATE_PAYLOAD_FORMAT');
    const authenticatedInvSize = Number(authenticatedPrefix.readBigUInt64BE(PAYLOAD_MAGIC.length));
    check(Number.isSafeInteger(authenticatedInvSize) && authenticatedInvSize > 0 && authenticatedInvSize <= MAX_MANIFEST
          && PAYLOAD_MAGIC.length + 8 + authenticatedInvSize <= authenticatedPrefix.length, 'PRIVATE_INVENTORY_SIZE');
    const authenticatedInv = authenticatedPrefix.subarray(PAYLOAD_MAGIC.length + 8, PAYLOAD_MAGIC.length + 8 + authenticatedInvSize);
    qualifyPrivateInventory(authenticatedInv, header);
    check(fileHash(plan.ciphertext) === plan.ciphertextSHA256, 'CIPHERTEXT_CHANGED_BEFORE_EXTRACTION');
    const cipher = crypto.createDecipheriv('aes-256-gcm', aesKey, nonce, {authTagLength: 16});
    cipher.setAAD(aad); cipher.setAuthTag(tag);
    physical(plan.parent, true); check((fs.statSync(plan.parent).mode & 0o777) === 0o700, 'RESTORE_PARENT_PERMISSIONS');
    check(path.dirname(plan.destination) === plan.parent && !fs.existsSync(plan.destination), 'EXCLUSIVE_RESTORE_DESTINATION');
    hasSpace(plan.parent, header.plaintextBytes * 2 + 65536);
    pending = path.join(plan.parent, '.authenticated-payload-pending-' + crypto.randomBytes(16).toString('hex'));
    payload = fs.openSync(pending, fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_RDWR, 0o600);
    const buffer = Buffer.alloc(CHUNK); let cipherPosition = start;
    try {
      while (cipherPosition < size - 16) {
        const count = fs.readSync(source, buffer, 0, Math.min(CHUNK, size - 16 - cipherPosition), cipherPosition);
        check(count > 0, 'TRUNCATED_CIPHERTEXT'); cipherPosition += count; hasSpace(plan.parent);
        writeAll(payload, cipher.update(buffer.subarray(0, count)));
      }
      writeAll(payload, cipher.final()); fs.fsyncSync(payload);
    } finally { aesKey.fill(0); }
    // Recheck the second authenticated pass before creating individual files.
    check(readExact(payload, PAYLOAD_MAGIC.length, 0).equals(PAYLOAD_MAGIC), 'PRIVATE_PAYLOAD_FORMAT');
    const invSize = Number(readExact(payload, 8, PAYLOAD_MAGIC.length).readBigUInt64BE());
    check(Number.isSafeInteger(invSize) && invSize > 0 && invSize <= MAX_MANIFEST, 'PRIVATE_INVENTORY_SIZE');
    const invRaw = readExact(payload, invSize, PAYLOAD_MAGIC.length + 8);
    check(invRaw.equals(authenticatedInv), 'AUTHENTICATED_MANIFEST_CHANGED');
    const inv = qualifyPrivateInventory(invRaw, header);
    // Reserve the final directory exclusively. Partial failures remain protected;
    // a later call never replaces, reuses or labels them a successful restore.
    fs.mkdirSync(plan.destination, {mode: 0o700}); let position = PAYLOAD_MAGIC.length + 8 + invSize;
    for (const row of inv.entries) {
      const target = path.join(plan.destination, row.scope, row.path);
      check(inside(plan.destination, target), 'RESTORE_PATH_ESCAPE');
      if (row.kind === 'directory') { fs.mkdirSync(target, {mode: 0o700}); continue; }
      const fd = fs.openSync(target, fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_WRONLY | fs.constants.O_NOFOLLOW, 0o600);
      const hash = crypto.createHash('sha256'); let remaining = row.bytes;
      try {
        while (remaining) { const amount = Math.min(CHUNK, remaining), value = readExact(payload, amount, position); position += amount; remaining -= amount; hash.update(value); writeAll(fd, value); }
        check(hash.digest('hex') === row.sha256, 'RESTORED_FILE_DIGEST'); fs.fchmodSync(fd, row.mode); fs.fsyncSync(fd);
      } finally { fs.closeSync(fd); }
    }
    for (const row of [...inv.entries].reverse().filter(row => row.kind === 'directory')) fs.chmodSync(path.join(plan.destination, row.scope, row.path), row.mode);
    const restoredScopes = inv.scopes.map(scope => ({...scope, root: path.join(plan.destination, scope.id)}));
    const actual = inventory(restoredScopes);
    check(canonical(actual.entries) === canonical(inv.entries) && actual.totalBytes === inv.totalBytes, 'RESTORED_EXACT_INVENTORY');
    const finalSourceStat = fs.fstatSync(source);
    check(finalSourceStat.dev === originalSourceStat.dev && finalSourceStat.ino === originalSourceStat.ino
          && finalSourceStat.size === originalSourceStat.size && finalSourceStat.mtimeMs === originalSourceStat.mtimeMs
          && finalSourceStat.ctimeMs === originalSourceStat.ctimeMs && fileHash(plan.ciphertext) === plan.ciphertextSHA256,
          'ORIGINAL_CIPHERTEXT_CHANGED_DURING_RESTORE');
    const manifestFD = fs.openSync(path.join(plan.destination, 'authenticated-original-inventory.json'), 'wx', 0o600);
    try { writeAll(manifestFD, invRaw); fs.fsyncSync(manifestFD); } finally { fs.closeSync(manifestFD); }
    syncDirectory(plan.destination); syncDirectory(plan.parent);
    return {status: 'PASS_AUTHENTICATED_PRIVATE_RESTORE_EXACT_BYTES_NOT_RETIREMENT', ciphertextSHA256: plan.ciphertextSHA256,
      inventorySHA256: header.inventorySHA256, entryCount: inv.entries.length, bytes: inv.totalBytes,
      recipientSPKISHA256: SPKI, receiverIdentity: runtimeIdentity(), originalDataDeleted: false, retirementAuthorized: false};
  } finally { if (aesKey) aesKey.fill(0); fs.closeSync(source); if (payload !== undefined) fs.closeSync(payload); }
}

function main() {
  try {
    const [mode, file] = process.argv.slice(2);
    if (mode === 'identity' && process.argv.length === 3) { console.log(JSON.stringify(runtimeIdentity())); return; }
    check(['preflight', 'seal', 'restore'].includes(mode) && process.argv.length === 4, 'FINITE_CUSTODY_COMMAND_REQUIRED');
    const plan = readJSON(file, 1024 * 1024);
    let result;
    if (mode === 'preflight') {
      check(plan.schema === 'pinkha-t5-private-preflight-v1' && canonical(plan.nodeIdentity) === canonical(runtimeIdentity()), 'PINNED_HOSTED_NODE_REQUIRED');
      check(bytes(plan.nodeIdentity).length + bytes(plan.binding).length + 1024 <= 16384, 'BOUNDED_FINAL_CUSTODY_HEADER_REQUIRED');
      publicKey(plan.publicKey); result = {status: 'PASS_PUBLIC_RECIPIENT_AND_NODE_NOT_CUSTODY', recipientSPKISHA256: SPKI, nodeIdentity: runtimeIdentity()};
    } else result = mode === 'seal' ? seal(plan) : restore(plan);
    console.log(JSON.stringify(result));
  } catch (error) {
    // Never serialize native messages, filenames, plan content, key material or
    // unauthenticated plaintext. All original partial files remain in custody.
    console.log(JSON.stringify({status: 'FAIL_PRIVATE_CUSTODY', code: /^[A-Z_]+$/.test(error.code || '') ? error.code : 'CRYPTO_OR_FILESYSTEM_FAILURE', originalDataDeleted: false}));
    process.exitCode = 1;
  }
}

if (import.meta.url === new URL(process.argv[1], 'file:').href) main();
export {canonical, fileHash, runtimeIdentity, inventory, seal, restore, publicKey};
