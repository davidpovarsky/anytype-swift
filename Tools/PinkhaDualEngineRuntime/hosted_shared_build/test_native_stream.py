"""Portable stream-boundary controls; none executes Apple/native/application tests."""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import threading
import types
import unittest
from unittest import mock

import native_inputs
import native_stream


class NativeStreamControls(unittest.TestCase):
    def fifo_case(self, data, expected):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.pipe"
            os.mkfifo(path, 0o600)
            identity = native_stream.fifo_identity(path)
            errors = []
            def writer():
                try:
                    with path.open("wb", buffering=0) as file:
                        file.write(data)
                except BrokenPipeError:
                    pass
                except BaseException as error:
                    errors.append(error)
            thread = threading.Thread(target=writer, daemon=True)
            thread.start()
            try:
                with mock.patch.object(native_stream, "ARCHIVE_BYTES", len(expected)), \
                     mock.patch.object(native_stream, "ARCHIVE_SHA", hashlib.sha256(expected).hexdigest()), \
                     mock.patch.object(native_stream, "FIFO_SECONDS", 3):
                    return native_stream.receive_archive(path, identity)
            finally:
                thread.join(timeout=3)
                self.assertFalse(thread.is_alive(), "Fixture writer must actually drain")
                self.assertEqual(errors, [])

    def test_exact_fifo_bytes_are_received(self):
        self.assertEqual(self.fifo_case(b"original-source", b"original-source"), b"original-source")

    def test_truncated_fifo_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete or changed"):
            self.fifo_case(b"original", b"original-source")

    def test_extra_fifo_byte_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "exceeded its exact byte bound"):
            self.fifo_case(b"original-source!", b"original-source")

    def test_replaced_fifo_is_rejected_before_open(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.pipe"
            os.mkfifo(path, 0o600)
            identity = native_stream.fifo_identity(path)
            identity["inode"] += 1
            with self.assertRaisesRegex(ValueError, "identity changed"):
                native_stream.receive_archive(path, identity)

    def test_stream_roundtrip_uses_original_payload_reader(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "actual"
            source.write_bytes(b"framework-fixture")
            row = native_inputs.regular(source)
            compressed_source = io.BytesIO()
            content = b"original-archived-source-fixture"
            with tarfile.open(fileobj=compressed_source, mode="w:gz") as archive:
                member = tarfile.TarInfo("any/original.swift")
                member.size, member.mode, member.mtime = len(content), 0o644, 10
                archive.addfile(member, io.BytesIO(content))
            source_rows = {"any/original.swift": {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
                                                   "mode": 0o644, "mtimeNS": 10000000000}}
            output = io.BytesIO()
            with mock.patch.object(native_stream.sys, "stdout", types.SimpleNamespace(buffer=output)):
                payload, manifest = native_stream.stream_payload({"native/fixture": source},
                    {"native/fixture": row}, compressed_source.getvalue(), source_rows,
                    {"fixtureOnly": True})
            archive_path = root / "payload.tar.gz"
            archive_path.write_bytes(output.getvalue())
            self.assertEqual(payload, {"bytes": len(output.getvalue()), "sha256": hashlib.sha256(output.getvalue()).hexdigest()})
            actual = native_inputs.read_payload(archive_path, expected_manifest=hashlib.sha256(manifest).hexdigest())
            self.assertEqual(actual["files"], 2)
            self.assertEqual(actual["bytes"], len(content) + source.stat().st_size)

    def test_wrong_original_archive_hash_is_rejected_before_parsing(self):
        with self.assertRaisesRegex(ValueError, "Exact original archived source bytes"):
            native_stream.qualify_archive(b"not-an-original-archive", b"not-a-manifest")


if __name__ == "__main__":
    unittest.main()
