"""One bounded source-pin control. No Swift, Native or App execution."""
from pathlib import Path
import hashlib
import unittest
import g02_native_phase as native
import g02_word_consumer as consumer

class Checks:
    @staticmethod
    def sha(raw): return hashlib.sha256(raw).hexdigest()
    @staticmethod
    def require(condition, reason):
        if not condition: raise ValueError(reason)

class SuccessorPins(unittest.TestCase):
    def test_exact_corrected_source_and_closed_gate(self):
        root=Path(__file__).resolve().parents[1]
        corrected=(root/'TorahNativeDerivedProductIntegrationTests.swift').read_bytes()
        previous=(root/'originals/TorahNativeDerivedProductIntegrationTests.swift').read_bytes()
        declared=native.qualify_native_source(Checks,corrected)
        self.assertEqual(declared['casesPerInvocation'],1)
        self.assertFalse(declared['AppleCompilationProvenByThisSourceCheck'])
        for rejected in [previous,corrected[:native.ORIGINAL_BYTES],corrected+b'\n']:
            with self.assertRaises(ValueError):native.qualify_native_source(Checks,rejected)
        for admission in [{},{'runtimeReady':True,'plan':'g02-word-only'}]:
            with self.assertRaisesRegex(ValueError,'G02_RUNTIME_CLOSED'):
                consumer.require_runtime_ready(admission,root)

if __name__=='__main__':unittest.main(verbosity=2)
