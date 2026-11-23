"""Independent private framing/accounting audit; public results contain no native IDs."""
import collections
import hashlib
import json
import re
import stat

ROW_KINDS = {
    "unresolved_row", "space_state", "tree_head", "acl_head", "tree_change",
    "tree_root", "acl_record", "acl_root", "unknown_collection_row", "opaque_client_row",
}
ISSUE_CODES = {
    "unknown_collection", "opaque_client_collection", "unsupported_row_shape",
    "unknown_field", "ambiguous_field", "missing_field", "unsupported_string_field",
    "opaque_payload_shape", "unsupported_numeric_metadata", "unsupported_reference_array",
    "empty_head_list", "unsupported_reference_identity", "duplicate_reference",
    "acl_head_cardinality", "unsupported_native_identity", "acl_tree_metadata",
    "unknown_deletion_state", "unsupported_derived_state", "not_in_capture",
    "wrong_namespace", "wrong_root", "target_unresolved", "cross_tree",
}
DOMAINS = {"tree_head", "acl_head", "acl", "acl_root", "change", "tree_root"}
OUTCOMES = {"resolved_identity_only", "not_in_capture", "wrong_namespace", "wrong_root", "target_unresolved", "cross_tree"}
LABELS = {
    "native": "TestLocalTreeCensusNativeStorageRelationships",
    "captured-old": "TestLocalTreeCensusUsesCapturedCheckpointWithoutLiveReads",
    "captured-new": "TestLocalTreeCensusUsesCapturedCheckpointWithoutLiveReads",
    "unknowns": "TestLocalTreeCensusRetainsUnknownRowsAndExactTypedIdentities",
    "references": "TestLocalTreeCensusReportsMissingCrossTreeAndACLReferences",
    "boundary": "TestLocalTreeCensusQualificationLimitsAndPrivateReceipt",
}

def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def safe_receipt(value):
    fixed = {
        "Version": "native-local-tree-storage-census-v1",
        "Scope": "captured-local-tree-storage-only",
        "Authority": "owned-fixture-only-v1",
        "Representation": "anyenc-v1.0.3-decoded-value-roundtrip-v1",
        "AllCapturedRowsAccounted": True,
        "SemanticIdentityCensusComplete": False,
        "NativeSnapshotProofRequired": True,
        "NativeIdentityCensusRequired": True,
        "HasNativeSourceAdmission": False,
        "PermitsDestinationWrites": False,
    }
    hashes = {"SourceWitnessSHA256", "CensusSHA256", "OwnerSHA256", "SpaceSHA256"}
    counts = {"Generation", "Collections", "EmptyCollections", "Rows", "References",
              "ResolvedReferences", "Issues", "UnresolvedRows", "UnknownCollections", "PrivateBytes"}
    require(isinstance(value, dict) and set(value) == set(fixed) | hashes | counts |
            {"RowsByKind", "IssuesByCode", "AllRecognizedReferencesResolved"},
            "census_safe_receipt_shape")
    require(all(type(value[k]) is type(v) and value[k] == v for k, v in fixed.items()),
            "census_scope_or_authority_changed")
    require(all(type(value[k]) is str and re.fullmatch("[0-9a-f]{64}", value[k]) for k in hashes),
            "census_unsafe_digest")
    require(all(type(value[k]) is int and value[k] >= 0 for k in counts) and
            value["Generation"] >= 1 and value["Collections"] >= 1 and
            0 < value["Rows"] <= 10000 and value["References"] <= 100000 and
            value["Issues"] <= 100000 and 0 < value["PrivateBytes"] <= 64 << 20,
            "census_invalid_count")
    require(type(value["AllRecognizedReferencesResolved"]) is bool, "census_invalid_completion_flag")
    for key, allowed, total in (("RowsByKind", ROW_KINDS, value["Rows"]),
                                ("IssuesByCode", ISSUE_CODES, value["Issues"])):
        rows = value[key]
        require(isinstance(rows, list) and all(isinstance(v, dict) and
                set(v) == {"Kind", "Count"} and type(v["Kind"]) is str and v["Kind"] in allowed and
                type(v["Count"]) is int and v["Count"] > 0 for v in rows), "census_unsafe_count_rows")
        require([v["Kind"] for v in rows] == sorted(set(v["Kind"] for v in rows)) and
                sum(v["Count"] for v in rows) == total, "census_count_accounting_mismatch")
    return value

class Frames:
    def __init__(self, raw):
        require(isinstance(raw, bytes) and len(raw) <= 64 << 20, "private_census_size")
        self.raw, self.at = raw, 0

    def frame(self):
        require(self.at + 8 <= len(self.raw), "private_frame_header")
        size = int.from_bytes(self.raw[self.at:self.at + 8], "big")
        self.at += 8
        require(size <= 64 << 20 and self.at + size <= len(self.raw), "private_frame_bounds")
        value = self.raw[self.at:self.at + size]
        self.at += size
        return value

    def integer(self, low=0, high=100000):
        raw = self.frame()
        require(len(raw) == 8, "private_integer_size")
        value = int.from_bytes(raw, "big", signed=True)
        require(low <= value <= high, "private_integer_bounds")
        return value

    def text(self, allowed):
        raw = self.frame()
        require(raw in {v.encode("ascii") for v in allowed}, "private_fixed_kind")
        return raw.decode("ascii")

    def end(self):
        require(self.at == len(self.raw), "private_trailing_data")

def decoded(data):
    nodes = 0
    def at(pos, depth):
        nonlocal nodes
        nodes += 1
        require(nodes <= 100000 and depth <= 64 and pos < len(data), "native_value_bounds")
        tag = data[pos]
        pos += 1
        if tag in (1, 4, 5):
            return (tag, None), pos
        if tag == 2:
            require(pos + 8 <= len(data), "native_number_bounds")
            return (tag, data[pos:pos + 8]), pos + 8
        if tag == 3:
            end = data.find(b"\0", pos)
            require(end >= pos, "native_string_bounds")
            return (tag, data[pos:end]), end + 1
        if tag == 8:
            require(pos + 4 <= len(data), "native_binary_header")
            size = int.from_bytes(data[pos:pos + 4], "big")
            pos += 4
            require(pos + size <= len(data), "native_binary_bounds")
            return (tag, data[pos:pos + size]), pos + size
        if tag in (6, 7):
            values = []
            while True:
                require(pos < len(data), "native_container_bounds")
                if data[pos] == 0:
                    return (tag, tuple(values)), pos + 1
                if tag == 7:
                    end = data.find(b"\0", pos)
                    require(end >= pos, "native_key_bounds")
                    key = data[pos:end]
                    if key == bytes([31]):
                        key = b""
                    value, pos = at(end + 1, depth + 1)
                    values.append((key, value))
                else:
                    value, pos = at(pos, depth + 1)
                    values.append(value)
        raise RuntimeError("native_encoding_tag")
    value, end = at(0, 0)
    require(end == len(data), "native_value_trailing_bytes")
    return value

def unique(value, key):
    require(value[0] == 7, "native_row_is_not_object")
    values = [v for k, v in value[1] if k == key]
    return values[0] if len(values) == 1 else None

def string(value):
    return value[1] if value is not None and value[0] == 3 else None

def parsed_witness(raw):
    r = Frames(raw)
    require(r.frame() == b"pinkha-localstore-witness-v1" and
            r.frame() == b"anyenc-v1.0.3-decoded-value-roundtrip-v1" and
            r.frame() == b"owned-fixture-only-v1", "native_witness_frame_identity")
    nonce, space = r.frame(), r.frame()
    generation = r.integer(1, (1 << 63) - 1)
    require(len(nonce) == 32 and len(space) > 0, "native_witness_binding")
    count = r.integer(1, 64)
    cols, names, all_rows = [], [], []
    for ci in range(count):
        name = r.frame()
        names.append(name)
        rows, identities = [], []
        for ordinal in range(r.integer(0, 10000)):
            identity_raw, value_raw = r.frame(), r.frame()
            identity, value = decoded(identity_raw), decoded(value_raw)
            require(unique(value, b"id") == identity, "native_exact_typed_row_identity")
            identities.append(identity_raw)
            item = {"collection": ci, "ordinal": ordinal, "nativeID": identity_raw,
                    "identity": identity, "value": value, "value_raw": value_raw}
            rows.append(item)
            all_rows.append(item)
        require(identities == sorted(set(identities)), "native_row_identity_order")
        cols.append({"name": name, "rows": rows})
    require(names == sorted(set(names)) and len(all_rows) <= 10000, "native_collection_accounting")
    r.end()
    return {"nonce": nonce, "space": space, "generation": generation,
            "cols": cols, "rows": all_rows, "sha256": sha(raw)}

def expected_references(w, rows):
    state = [v for col in w["cols"] if col["name"] == b"state" for v in col["rows"]
             if v["identity"] == (3, w["space"])]
    require(len(state) == 1, "native_state_binding")
    acl = string(unique(state[0]["value"], b"a"))
    require(acl, "native_acl_binding")
    out = []
    for number, row in enumerate(rows):
        value = w["rows"][number]["value"]
        if not row["id"] or row["kind"] in {"unresolved_row", "unknown_collection_row", "opaque_client_row"}:
            continue
        def ref(field, position, kind, domain, identity, tree=b""):
            out.append((number, position, kind, domain, field, identity, tree))
        def scalar(field, kind, domain, tree=b""):
            v = string(unique(value, field))
            if v:
                ref(field, -1, kind, domain, v, tree)
        def array(field, kind, domain, tree=b""):
            v = unique(value, field)
            if v is not None and v[0] == 6:
                for position, item in enumerate(v[1]):
                    identifier = string(item)
                    if identifier:
                        ref(field, position, kind, domain, identifier, tree)
        if row["kind"] == "space_state":
            a, s = string(unique(value, b"a")), string(unique(value, b"s"))
            require(a and s, "native_state_required_roots")
            ref(b"a", -1, "state_acl_head", "acl_head", a)
            ref(b"a", -1, "state_acl_root", "acl_root", a)
            ref(b"s", -1, "state_settings_head", "tree_head", s)
            ref(b"s", -1, "state_settings_root", "tree_root", s, s)
        elif row["kind"] in {"tree_head", "acl_head"}:
            array(b"h", "head", "acl" if row["kind"] == "acl_head" else "change", row["id"])
            if row["kind"] == "tree_head":
                ref(b"id", -1, "tree_root", "tree_root", row["id"], row["id"])
                scalar(b"s", "common_snapshot", "change", row["id"])
                scalar(b"p", "parent_tree", "tree_head")
        elif row["kind"] in {"tree_root", "tree_change"}:
            require(row["tree"] == string(unique(value, b"t")), "native_tree_owner_bytes")
            ref(b"t", -1, "change_tree_head", "tree_head", row["tree"])
            array(b"p", "predecessor", "change", row["tree"])
            scalar(b"i", "snapshot_base", "change", row["tree"])
        elif row["kind"] in {"acl_root", "acl_record"}:
            scalar(b"p", "acl_predecessor", "acl")
    return out

def parse_census(raw, witness_raw, receipt):
    r = Frames(raw)
    require(r.frame() == b"pinkha-local-tree-storage-census-v1" and
            r.frame() == b"local-structural-identities-no-source-admission",
            "private_census_identity")
    require(r.frame() == sha(witness_raw).encode("ascii") and r.frame() == witness_raw,
            "private_exact_nested_witness")
    w = parsed_witness(witness_raw)
    rows = []
    for number in range(r.integer(0, 10000)):
        row = {"collection": r.integer(0, 63), "ordinal": r.integer(0, 9999),
               "kind": r.text(ROW_KINDS), "nativeID": r.frame(), "id": r.frame(), "tree": r.frame(),
               "deleted": r.integer(-1, 2), "derived": r.integer(-1, 1), "unresolved": r.integer(0, 1)}
        require(number < len(w["rows"]), "private_extra_census_row")
        original = w["rows"][number]
        require(all(row[k] == original[k] for k in ["collection", "ordinal", "nativeID"]),
                "private_lost_reordered_or_coerced_row")
        if row["id"]:
            require(original["identity"] == (3, row["id"]), "private_coerced_native_string_identity")
        rows.append(row)
    require(len(rows) == len(w["rows"]), "private_missing_census_rows")
    references = []
    kinds = {"state_acl_head", "state_acl_root", "state_settings_head", "state_settings_root",
             "head", "tree_root", "common_snapshot", "parent_tree", "change_tree_head",
             "predecessor", "snapshot_base", "acl_predecessor"}
    for _ in range(r.integer()):
        ref = {"row": r.integer(0, len(rows)-1), "position": r.integer(-1, 99999),
               "kind": r.text(kinds), "domain": r.text(DOMAINS), "field": r.frame(),
               "id": r.frame(), "tree": r.frame(), "outcome": r.text(OUTCOMES),
               "target": r.integer(-1, len(rows)-1), "observed": r.integer(-1, len(rows)-1)}
        require(ref["id"], "private_empty_reference")
        if ref["outcome"] == "resolved_identity_only":
            require(ref["target"] >= 0 and ref["observed"] == ref["target"], "private_resolved_target_missing")
            target = rows[ref["target"]]
            require(target["id"] == ref["id"], "private_reference_identity_mismatch")
            domain = ref["domain"]
            allowed = {"tree_head": {"tree_head"}, "acl_head": {"acl_head"},
                       "acl_root": {"acl_root"}, "acl": {"acl_root", "acl_record"},
                       "tree_root": {"tree_root"}, "change": {"tree_root", "tree_change"}}[domain]
            require(target["kind"] in allowed, "private_resolved_wrong_namespace")
            if domain in {"tree_root", "change"}:
                require(target["tree"] == ref["tree"], "private_resolved_cross_tree")
        else:
            require(ref["target"] == -1, "private_unresolved_edge_invented")
        if ref["observed"] >= 0:
            require(rows[ref["observed"]]["id"] == ref["id"], "private_observed_identity_mismatch")
        references.append(ref)
    require([tuple(v[k] for k in ["row", "position", "kind", "domain", "field", "id", "tree"])
             for v in references] == expected_references(w, rows), "private_reference_accounting")
    issues = []
    for _ in range(r.integer()):
        issue = {"collection": r.integer(0, len(w["cols"])-1), "row": r.integer(-1, len(rows)-1),
                 "field": r.frame(), "position": r.integer(-1, 99999), "code": r.text(ISSUE_CODES)}
        if issue["row"] >= 0:
            require(rows[issue["row"]]["collection"] == issue["collection"] and
                    rows[issue["row"]]["unresolved"] == 1, "private_issue_source_binding")
        issues.append(issue)
    r.end()
    counts = {
        "SourceWitnessSHA256": sha(witness_raw), "CensusSHA256": sha(raw),
        "OwnerSHA256": sha(w["nonce"]), "SpaceSHA256": sha(w["space"]),
        "Generation": w["generation"], "Collections": len(w["cols"]),
        "EmptyCollections": sum(not v["rows"] for v in w["cols"]), "Rows": len(rows),
        "References": len(references), "ResolvedReferences": sum(v["target"] >= 0 for v in references),
        "Issues": len(issues), "UnresolvedRows": sum(v["unresolved"] for v in rows),
        "UnknownCollections": sum(v["code"] == "unknown_collection" for v in issues),
        "PrivateBytes": len(raw),
    }
    require(all(receipt[k] == v for k, v in counts.items()), "private_public_count_or_hash_mismatch")
    for key, values in (("RowsByKind", collections.Counter(v["kind"] for v in rows)),
                        ("IssuesByCode", collections.Counter(v["code"] for v in issues))):
        require(receipt[key] == [{"Kind": k, "Count": values[k]} for k in sorted(values)],
                "private_public_typed_accounting")
    require(receipt["AllRecognizedReferencesResolved"] == (
            counts["ResolvedReferences"] == counts["References"] and counts["UnresolvedRows"] == 0
            and counts["UnknownCollections"] == 0), "private_public_completion_flag")
    return w, {"status": "PASS_PRIVATE_SOURCE_ACCOUNTING", **counts,
               "exact_nested_witness": True, "all_captured_rows_bound": True,
               "all_recognized_references_accounted": True, "raw_private_values_published": False}

def audit_private_pairs(root, receipts):
    require(set(receipts) == set(LABELS), "private_pair_labels")
    found = {label: [] for label in LABELS}
    for path in root.rglob("*"):
        require(not path.is_symlink(), "private_artifact_symlink")
        if path.is_file() and path.name.endswith(".census.bin"):
            label = path.name[:-len(".census.bin")]
            require(label in found, "unexpected_private_census")
            found[label].append(path)
    result, parsed, dirs = {}, {}, {}
    for label in LABELS:
        require(len(found[label]) == 1, "missing_or_duplicate_private_pair")
        census = found[label][0]
        witness = census.with_name(label + ".witness.bin")
        for path in (census, witness):
            mode = path.lstat().st_mode
            require(stat.S_ISREG(mode) and stat.S_IMODE(mode) == 0o600, "private_pair_file_mode")
        require(stat.S_IMODE(census.parent.stat().st_mode) in {0o700, 0o2700}, "private_pair_directory_mode")
        parsed[label], result[label] = parse_census(census.read_bytes(), witness.read_bytes(), receipts[label])
        dirs[label] = census.parent
    before, after = parsed["captured-old"], parsed["captured-new"]
    require(dirs["captured-old"] == dirs["captured-new"] and
            all(before[k] == after[k] for k in ("nonce", "space", "generation")) and
            before["sha256"] != after["sha256"] and len(after["rows"]) == len(before["rows"]) + 1 and
            len(after["cols"]) == len(before["cols"]) + 1, "private_historical_checkpoint_binding")
    return result
