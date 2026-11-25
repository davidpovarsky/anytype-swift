"""Owned-root and quarantine controls; fixtures grant no native acceptance."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import sys
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent)]
from release_contract import identity, write
from release_continuation_roots import admit_roots


class RootContinuationControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.old=self.root/'build/old-evidence';self.evidence=self.root/'build/new-evidence'
        self.derived=self.root/'build/old-work/producer-derived'
        self.exported=self.root/'build/new-work/distribution'
        for path in [self.old,self.evidence,self.derived,self.exported]:
            path.mkdir(parents=True)
        self.descriptor=self.old/'release-execution.json'
        self.execution={'source_sha':'1'*40,'execution_id':'local-11111111-1111-4111-8111-111111111111',
            'root':str(self.root),'work_root':str(self.derived.parent),'evidence_root':str(self.old)}
        write(self.descriptor,self.execution)
        write(self.old/'execution.json',{'status':'FAIL','scope':'SYNTHETIC_NO_NATIVE_CREDIT'})
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        self.continuation={'schema':'otzaria.original-editor.release-postbuild-continuation/1',
            'execution_id':'local-22222222-2222-4222-8222-222222222222',
            'previous_evidence':str(self.old),'previous_work':str(self.derived.parent),
            'evidence_root':str(self.evidence),'work_root':str(self.exported.parent),
            'source_sha':self.execution['source_sha'],'build_run_id':self.execution['execution_id'],
            'previous_descriptor_sha256':sha(self.descriptor),
            'previous_execution_sha256':sha(self.old/'execution.json'),'compiler_executions':0}
        write(self.evidence/'continuation.json',self.continuation)
        self.collection={'output_directory':str(self.evidence/'actual-public-symbol-graphs'),
            'collection_continuation':{'execution_id':self.continuation['execution_id'],
                'continuation_sha256':sha(self.evidence/'continuation.json'),
                'compiler_evidence_root':str(self.old),'compiler_descriptor_path':str(self.descriptor),
                'compiler_descriptor_sha256':sha(self.descriptor),
                'original_compiler_execution_id':self.execution['execution_id'],
                'compiler_executions':0,'original_evidence_rewritten':False}}
        write(self.evidence/'compiler-symbolgraph-collection.json',self.collection)
        self.source={'head_sha':self.execution['source_sha'],'run_id':self.execution['execution_id'],
            'execution_identity':identity(self.execution,self.descriptor)}

    def admit(self,quarantined=False):
        return admit_roots(self.derived,self.exported,self.collection,self.source,quarantined=quarantined)

    def quarantine(self):
        retained=self.exported.parent/'producer-derived-preserved'
        self.derived.rename(retained)
        write(self.evidence/'producer-build-path-absent.json',
            {'original':str(self.derived),'preserved_at':str(retained),
             'original_path_exists':False,'deleted':False})

    def test_distinct_original_and_current_roots_require_actual_pinned_provenance(self):
        before=self.descriptor.read_bytes()
        value=self.admit()
        self.assertEqual(value['original_derived'],str(self.derived))
        self.assertEqual(value['continuation_distribution'],str(self.exported))
        self.assertEqual(self.descriptor.read_bytes(),before)

    def test_direct_build_keeps_original_sibling_root_policy(self):
        exported=self.derived.parent/'distribution';exported.mkdir()
        self.assertIsNone(admit_roots(self.derived,exported,{},{}))

    def test_missing_continuation_proof_is_refused(self):
        self.collection.pop('collection_continuation')
        with self.assertRaises(ValueError):self.admit()

    def test_replaced_graph_receipt_is_refused(self):
        write(self.evidence/'compiler-symbolgraph-collection.json',{})
        with self.assertRaises(ValueError):self.admit()

    def test_changed_original_descriptor_and_terminal_are_refused(self):
        for path in [self.descriptor,self.old/'execution.json']:
            before=path.read_bytes();path.write_bytes(before+b' ')
            with self.assertRaises(ValueError):self.admit()
            path.write_bytes(before)

    def test_foreign_existing_work_roots_are_refused(self):
        original=self.derived
        self.derived=self.root/'build/foreign-work/producer-derived';self.derived.mkdir(parents=True)
        with self.assertRaises(ValueError):self.admit()
        self.derived=original

    def test_unrelated_source_or_compiler_identity_is_refused(self):
        for key in ['head_sha','run_id','execution_identity']:
            original=self.source[key];self.source[key]='unrelated'
            with self.assertRaises(ValueError):self.admit()
            self.source[key]=original

    def test_changed_continuation_record_is_refused(self):
        path=self.evidence/'continuation.json'
        value=dict(self.continuation);value['work_root']=str(self.derived.parent)
        write(path,value)
        with self.assertRaises(ValueError):self.admit()

    def test_aliased_work_root_is_refused(self):
        alias=self.root/'build/alias';alias.symlink_to(self.derived.parent,target_is_directory=True)
        self.derived=alias/'producer-derived'
        with self.assertRaises(ValueError):self.admit()

    def test_exact_retained_move_is_admitted_after_original_path_is_absent(self):
        self.quarantine()
        value=self.admit(quarantined=True)
        self.assertTrue(value['producer_quarantined'])

    def test_recreated_original_path_is_refused_after_quarantine(self):
        self.quarantine();self.derived.mkdir()
        with self.assertRaises(ValueError):self.admit(quarantined=True)

    def test_false_retained_move_record_is_refused(self):
        self.quarantine()
        write(self.evidence/'producer-build-path-absent.json',{'deleted':True})
        with self.assertRaises(ValueError):self.admit(quarantined=True)


if __name__=='__main__':
    unittest.main(verbosity=2)
