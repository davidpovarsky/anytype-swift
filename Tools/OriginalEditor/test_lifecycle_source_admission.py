"""Negative controls for the separately reviewed lifecycle source boundary."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from lifecycle_facade_source import validate_document, RELATIVE, REVIEWED
from framework_profile import read_manifest, verify_project, verify_complete_source
from pbx_source import loads, object_text, render

HERE = Path(__file__).resolve().parent

class LifecycleSourceControls(unittest.TestCase):
    def setUp(self):
        self.value = json.loads((HERE / "LifecycleBatch/source_adoption.json").read_text())
        self.binding = {"path": RELATIVE, "reviewed_source": REVIEWED}
    def test_exact_reviewed_source_grants_no_native_credit(self):
        rows = validate_document(self.value, self.binding)
        self.assertEqual(len(rows), 21)
        self.assertIs(self.value["native_acceptance_reused_by_this_document"], False)
    def test_missing_file_refused(self):
        self.value["files"].pop()
        with self.assertRaises(ValueError):
            validate_document(self.value, self.binding)
    def test_additional_file_refused(self):
        self.value["files"].append(copy.deepcopy(self.value["files"][-1]))
        with self.assertRaises(ValueError):
            validate_document(self.value, self.binding)
    def test_unreviewed_source_refused(self):
        self.value["reviewed_source"] = "1" * 40
        with self.assertRaises(ValueError):
            validate_document(self.value, self.binding)
    def test_native_acceptance_claim_refused(self):
        self.value["native_acceptance_reused_by_this_document"] = True
        with self.assertRaises(ValueError):
            validate_document(self.value, self.binding)
    def test_aliased_document_binding_refused(self):
        self.binding["path"] = "../source_adoption.json"
        with self.assertRaises(ValueError):
            validate_document(self.value, self.binding)
    def test_missing_current_batch_facade_refused(self):
        profile = read_manifest()
        profile["framework_facade_sources"].remove("OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotationBatch.swift")
        historical = json.loads((HERE / "complete_source_continuation.json").read_text())
        with self.assertRaises(ValueError):
            verify_complete_source(profile, historical)
    def test_actual_lifecycle_compiler_membership_required_after_rehash(self):
        profile = read_manifest()
        raw = (HERE.parent.parent / "Anytype.xcodeproj/project.pbxproj").read_text()
        objects = loads(raw)["objects"]
        ref = next(key for key,value in objects.items() if value.get("path") == "AnytypeOriginalAnnotationLifecycle.swift")
        build = next(key for key,value in objects.items() if value.get("isa") == "PBXBuildFile" and value.get("fileRef") == ref)
        target = objects[profile["framework_target_id"]]
        phase = next(key for key in target["buildPhases"] if objects[key]["isa"] == "PBXSourcesBuildPhase")
        objects[phase]["files"].remove(build)
        changed = raw.replace(object_text(raw, phase), "\t\t" + phase + " = " + render(objects[phase], 2) + ";\n", 1).encode()
        profile["candidate_project_sha256"] = hashlib.sha256(changed).hexdigest()
        with self.assertRaises(ValueError):
            verify_project(changed, (HERE / "original_project.pbxproj").read_bytes(), profile)

if __name__ == "__main__":
    unittest.main()
