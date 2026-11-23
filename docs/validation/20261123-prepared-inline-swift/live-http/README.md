# Original live HTTP failure and bounded fixture repair

The first real Swift-to-native HTTP XCTest executed and failed. The native requests successfully prepared and committed the zero-byte file, then prepared the 4095-byte file. Both files use the same ordinary owner. The owner's payload root already exists after the first file commits, so the next intent correctly begins file-root-committed. The test incorrectly required file-prepared for every file.

Only that live fixture changed. The first file must still start file-prepared; the second must start file-root-committed and reuse the exact first payload root while reserving distinct file/change/fingerprint identities. No production source, native source, size bound, outcome or authority check changed.

The failed original XCTest, its original source, supervisor, result and complete input inventories remain unchanged here. The repaired fixture compiled and registered exactly one live method. No product method was executed during that compilation, and none of the twelve portable client methods or the three native HTTP controls was repeated.

The repaired live execution has not run at this checkpoint. It requires a fresh nonce-bound native server and independent native readback. A passing original XCTest and a passing native bridge are both required before live qualification.
