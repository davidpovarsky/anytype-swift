"""Rejection/orchestration controls; these generated fixtures are not Apple proof."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import coherent_heart_release as coherent
import run_t5_apple_pair as pair
import run_ui27 as ui
import t5_remaining_freshness as freshness

SOURCE, RUN, ATTEMPT, TOKEN = "a" * 40, "98765", "1", "b" * 32
UDID, BASELINE = "12345678-1234-1234-1234-123456789ABC", "22345678-1234-1234-1234-123456789ABC"
ROOT_SHA = "c" * 64


def fixture(root_sha=ROOT_SHA):
    documents, originals, parsed = [], {}, []
    for index, name in enumerate(("page", "note", "quote")):
        block = None if index == 0 else name + "-block"
        canonical = dict(version=2, records=[dict(spaceId="fresh-space", objectId=name, blockId=block,
            item=dict(kind="ref", providerID="sefaria", canonicalKey="Genesis 3:3", externalID="Genesis 3:3",
                      role="sourceQuote" if index == 2 else "context", futurePairField={"keep": TOKEN},
                      providerPayload="opaque original sourceQuote payload" if index == 2 else ""))])
        raw = json.dumps(canonical, sort_keys=True)
        originals[name] = raw; parsed.append(canonical)
        documents.append(dict(objectID=name, typeKey=("ot-page", "ot-note", "ot-custom-chiddush")[index],
            initialName=name + " original", blockID=block, blockText=None if index == 0 else name + " text",
            canonicalSHA256=pair.sha_bytes(raw.encode()), publicSHA256="d" * 64))
    ledger = dict(token=TOKEN, appSourceSHA=SOURCE, rootPathSHA256=root_sha, rootRelativePath=pair.ROOT_RELATIVE_PATH,
                  accountID="fresh-account", spaceID="fresh-space", manifestID="manifest", manifestSHA256="e" * 64,
                  canonicalKey="pinkhaTorahSources", documents=documents, completedPhases=[])
    observations = []
    for ordinal, (name, reference, native, host, moved, reachable) in enumerate(freshness.STAGES, 1):
        readbacks = []
        for index, document in enumerate(documents):
            current = copy.deepcopy(parsed[index])
            if index == 2 and moved:
                current["records"][0]["item"].update(canonicalKey="Genesis 3:4", externalID="Genesis 3:4")
            raw = json.dumps(current, sort_keys=True)
            readbacks.append(dict(objectID=document["objectID"], spaceID=ledger["spaceID"], title=document["initialName"],
                typeKey=document["typeKey"], canonicalRaw=raw, canonicalSHA256=pair.sha_bytes(raw.encode())))
        nodes = [dict(id="quote", childIDs=["quote-block"] if reachable else [])]
        if reachable: nodes.append(dict(id="quote-block", childIDs=[]))
        observations.append(dict(name=name, sourceReference=reference, spaceID=ledger["spaceID"], serviceID="service-1",
            serviceQueryOrdinal=ordinal, nativeCandidatesBefore=sorted(documents[i]["objectID"] for i in native),
            nativeCandidatesAfter=sorted(documents[i]["objectID"] for i in native),
            targets=[dict(objectID=documents[i]["objectID"], blockID=documents[i]["blockID"], canUnlink=i == 0) for i in host],
            coverage="indexedTargetsOnly", limitations=["indexFreshnessUnverified"] + ([] if reachable else ["staleCandidates"]),
            readbacks=readbacks, quoteGraph=dict(spaceID=ledger["spaceID"], rootID="quote", targetID="quote-block",
                targetReachable=reachable, nodes=nodes),
            quoteBlockTextSHA256=pair.sha_bytes(b"quote text") if reachable else None))
    return dict(protocolVersion=freshness.PROTOCOL, status=freshness.NATIVE_PASS, token=TOKEN, appSourceSHA=SOURCE,
        runID=RUN, runAttempt=ATTEMPT, processID=1234, runtimeProfile=freshness.RUNTIME_PROFILE,
        runtimeVersion=ui.heart_profiles.select(freshness.RUNTIME_PROFILE).version, actualCapability="verified",
        accountID=ledger["accountID"], spaceID=ledger["spaceID"], rootPathSHA256=root_sha, serverConfiguration="localOnly",
        ledger=ledger, originalCanonical=originals, serviceID="service-1", serviceQueryCount=6,
        nativeMutationCounts={"ObjectSetDetails": 2, "BlockListDelete": 1}, observations=observations,
        accountStopCompleted=True, accountNotRunningConfirmed=True, appShutdownCompleted=True,
        historicalPaginationInvocations=0, runtimePairPhasesExecuted=[], mixedVersionAccepted=False,
        wholeIndexCompleteness="NOT_PROVEN", forcedNetworkOutage="NOT_RUN", productLookupFlag="OFF")


def validate(value):
    return freshness.validate_receipt(value, source=SOURCE, run_id=RUN, run_attempt=ATTEMPT,
        token=TOKEN, root_sha=ROOT_SHA, runtime=ui.heart_profiles.select(freshness.RUNTIME_PROFILE).version)


class RemainingFreshnessControls(unittest.TestCase):
    def test_exact_six_observations_preserve_bounded_scope(self):
        self.assertEqual(validate(fixture()), freshness.COUNTS)
        freshness.validate_counts(freshness.COUNTS)
        for key in freshness.COUNTS:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                freshness.validate_counts(dict(freshness.COUNTS, **{key: True}))

    def test_wrong_current_identity_and_widened_claims_fail(self):
        changes = [dict(appSourceSHA="f" * 40), dict(runID="old-run"), dict(runAttempt="2"), dict(token="a" * 32),
                   dict(rootPathSHA256="d" * 64), dict(runtimeVersion="prefix-only"), dict(runtimeProfile="r15-attachment-v1"),
                   dict(processID=True), dict(processID=0), dict(accountStopCompleted=False), dict(appShutdownCompleted=False),
                   dict(historicalPaginationInvocations=36), dict(runtimePairPhasesExecuted=["old-create"]),
                   dict(mixedVersionAccepted=True), dict(wholeIndexCompleteness="PROVEN"), dict(productLookupFlag="ON"),
                   dict(serviceQueryCount=7), dict(nativeMutationCounts={"ObjectSetDetails": 2, "BlockListDelete": True})]
        for change in changes:
            bad = fixture(); bad.update(change)
            with self.subTest(change=change), self.assertRaises(RuntimeError): validate(bad)

    def test_same_service_and_native_membership_are_required(self):
        changes = [lambda b: b["observations"].pop(),
                   lambda b: b["observations"].reverse(),
                   lambda b: b["observations"][2].update(serviceID="replacement-service"),
                   lambda b: b["observations"][2].update(serviceQueryOrdinal=1),
                   lambda b: b["observations"][2].update(nativeCandidatesBefore=[]),
                   lambda b: b["observations"][4].update(targets=copy.deepcopy(b["observations"][2]["targets"])),
                   lambda b: b["observations"][5].update(targets=copy.deepcopy(b["observations"][0]["targets"])),
                   lambda b: b["observations"][5].update(limitations=["indexFreshnessUnverified"])]
        for index, change in enumerate(changes):
            bad = fixture(); change(bad)
            with self.subTest(index=index), self.assertRaises(RuntimeError): validate(bad)

    def test_payload_unknown_fields_and_unrelated_native_details_are_retained(self):
        changes = [lambda b: b["observations"][1]["readbacks"][0].update(title="changed page"),
                   lambda b: b["observations"][1]["readbacks"][1].update(typeKey="ot-page"),
                   lambda b: b["observations"][3]["readbacks"][2].update(canonicalRaw=b["observations"][1]["readbacks"][2]["canonicalRaw"]),
                   lambda b: b["ledger"].update(completedPhases=["old-create"])]
        for index, change in enumerate(changes):
            bad = fixture(); change(bad)
            with self.subTest(index=index), self.assertRaises(RuntimeError): validate(bad)
        bad = fixture()
        target = bad["observations"][1]["readbacks"][2]
        canonical = json.loads(target["canonicalRaw"])
        canonical["records"][0]["item"].pop("futurePairField")
        target["canonicalRaw"] = json.dumps(canonical, sort_keys=True)
        target["canonicalSHA256"] = pair.sha_bytes(target["canonicalRaw"].encode())
        with self.assertRaisesRegex(RuntimeError, "unknown fields"): validate(bad)

    def test_deleted_quote_requires_actual_live_graph_exclusion(self):
        bad = fixture()
        bad["observations"][-1]["quoteGraph"]["nodes"] = copy.deepcopy(bad["observations"][0]["quoteGraph"]["nodes"])
        with self.assertRaisesRegex(RuntimeError, "actual live graph"): validate(bad)
        bad = fixture(); bad["observations"][0]["quoteBlockTextSHA256"] = "f" * 64
        with self.assertRaisesRegex(RuntimeError, "quote body"): validate(bad)

    def test_original_pair_source_is_retained_byte_for_byte(self):
        source = Path(__file__).resolve().parents[2]
        proof = freshness.source_contract(source)
        self.assertEqual(proof["original_sha256"], freshness.ORIGINAL_SHA)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); path = root / freshness.SWIFT
            path.parent.mkdir(parents=True)
            raw = (source / freshness.SWIFT).read_bytes()
            path.write_bytes(raw.replace(b"import Foundation", b"import Foundation ", 1))
            with self.assertRaisesRegex(RuntimeError, "byte-identical"): freshness.source_contract(root)

    def _execute(self, root, secret_in_log=False):
        app, work, proof = root / "app", root / "private", root / "proof"
        work.mkdir(); app.mkdir()
        source_file = Path(__file__).resolve().parents[2] / freshness.SWIFT
        target = app / freshness.SWIFT; target.parent.mkdir(parents=True); target.write_bytes(source_file.read_bytes())
        container = root / "container"
        native_root = container / pair.ROOT_RELATIVE_PATH; native_root.mkdir(parents=True)
        root_sha = pair.sha_bytes(str(native_root.resolve()).encode())
        directory = container / freshness.PRIVATE; directory.mkdir(parents=True)
        pair.write(directory / "receipt.json", fixture(root_sha))
        secrets = dict(token=TOKEN, mnemonic="test-only disposable mnemonic", accountKey="test-only-account-key")
        pair.write(directory / "secrets.json", secrets)
        profile = ui.heart_profiles.select(freshness.RUNTIME_PROFILE)
        build = dict(app=str(app / "Anytype.app"), configuration=str(app / "native.xctestrun"),
            code_sha256="e" * 64, runtime_binding={"controller_fixture_only": True}, same_job_build_receipt_sha256="f" * 64)
        context = SimpleNamespace(verify_current=Mock())
        owned = SimpleNamespace(key="t5-remaining-freshness", prepare=Mock(return_value="owned-quote-fixture"), record_created=Mock())
        selection = dict(udid=BASELINE, device={"identifier": "ipad"}, runtime={"identifier": "ios27"})
        commands, installed = [], False

        def command(argv, app, directory, name, timeout, check=True, output=None):
            nonlocal installed
            commands.append(argv)
            self.assertNotIn("build-for-testing", argv)
            directory.mkdir(parents=True, exist_ok=True)
            log = output or directory / (name + ".log")
            log.write_text(UDID if name == "create" else "controller-only log")
            if name == "install": installed = True
            return dict(return_code=0, timed_out=False), log

        def selected(**kwargs):
            self.assertEqual(kwargs["selections"], [freshness.METHOD])
            self.assertEqual(kwargs["configuration"], Path(build["configuration"]))
            self.assertEqual(kwargs["environment"]["PINKHA_T5_FRESHNESS_RUN_ATTEMPT"], ATTEMPT)
            phase = kwargs["directory"]; phase.mkdir(parents=True)
            pair.write(phase / "summary.json", dict(totalTestCount=1, passedTests=1, failedTests=0, skippedTests=0,
                devicesAndConfigurations=[{"device": {"deviceId": UDID, "architecture": "arm64", "osVersion": "27.1"}}]))
            pair.write(phase / "tests.json", {freshness.METHOD: "Passed"})
            pair.write(phase / "selection.json", dict(blueprint="AnytypeTests", methods=[freshness.METHOD], device_udid=UDID))
            (phase / "test.log").write_text(secrets["accountKey"] if secret_in_log else "controller-only test log")
            return dict(passed=1, failed=0, skipped=0)

        api = SimpleNamespace(**{name: getattr(pair, name) for name in ("require", "write", "digest", "sha_bytes", "contains_secret")},
            run_logged=command, app_container=lambda udid, kind, required=True: container if installed else None)
        ui_api = SimpleNamespace(heart_profiles=ui.heart_profiles, code_carriers=lambda path: {"sha256": build["code_sha256"]})
        with patch.object(coherent, "validate_build", return_value=profile), \
             patch.object(freshness, "uuid4", return_value=SimpleNamespace(hex=TOKEN)), \
             patch.object(freshness.simulator, "ensure_ready", return_value={"status": "OWNED_SIMULATOR_READY"}), \
             patch.object(freshness.simulator, "shutdown_owned", return_value={"status": "OWNED_SIMULATOR_SHUTDOWN_COMMAND_SUCCEEDED"}) as stop, \
             patch.object(freshness.native_ui, "select_tests", side_effect=selected):
            try:
                outcome = freshness.run_after_coherent_build(app=app, work=work, proof=proof, build=build,
                    selection=selection, pair=api, ui=ui_api, method_results=lambda value: value,
                    source=SOURCE, run_id=RUN, run_attempt=ATTEMPT, build_context=context, owned_device=owned)
            finally:
                stop.assert_called_once()
        return outcome, commands, context, owned

    def test_controller_selects_new_method_reuses_app_and_scans_original_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            outcome, commands, context, owned = self._execute(Path(temporary))
            self.assertEqual(outcome["status"], freshness.PASS)
            self.assertEqual(outcome["actual_counts"], freshness.COUNTS)
            self.assertEqual([command[2] for command in commands], ["create", "install"])
            self.assertEqual(outcome["additional_app_builds"], 0)
            self.assertEqual(outcome["additional_ui_runner_builds"], 0)
            self.assertGreaterEqual(context.verify_current.call_count, 2)
            owned.record_created.assert_called_once_with(UDID)

    def test_credential_in_native_log_withholds_all_projection_and_still_shuts_down(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "credentials found"):
                self._execute(root, secret_in_log=True)
            self.assertFalse((root / "proof/remaining-freshness/actual").exists())
            result = json.loads((root / "proof/remaining-freshness/result.json").read_bytes())
            self.assertEqual(result["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
