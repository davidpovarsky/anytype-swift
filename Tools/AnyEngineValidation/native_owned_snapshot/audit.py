"""Read-only audit of fixed native-owned control output and two private frames."""
import hashlib, json, os, pathlib, re, stat, struct
METHODS = [
    "TestNativeOwnedSnapshotBindsActualServiceHandle",
    "TestNativeOwnedSnapshotCloseRevokesAndDrains",
    "TestNativeOwnedSnapshotDeletePreservesLeaseBoundary",
    "TestNativeOwnedSnapshotShutdownAndCanceledAcquire",
]
PACKAGE="github.com/anyproto/anytype-heart/core/pinkha/localstorewitness"
AUTHORITY="heart-owned-local-store-v1"
FACTS=[
    {"actual_service_constructor","native_unknown_and_empty_retained","generic_and_zero_issuance_refused","fresh_same_db_read_transaction","foreign_transaction_not_reused_or_committed","census_authority_unchanged"},
    {"copied_and_zero_lease_refused_without_effect","copied_lease_cannot_release_gate","actual_read_tx_precedes_close","revocation_cancels_scan","backend_close_waited_for_real_release","revoked_release_drained_once","native_reopen_uses_new_handle_generation"},
    {"same_space_distinct_db_epochs","canceled_delete_preserves_store_and_lease","actual_delete_revokes_all_same_space_handles","recreate_refuses_all_old_capabilities","actual_successful_backup_revokes_detached_handle","original_recovery_decision_unchanged"},
    {"canceled_acquisition_preserves_real_holder","service_shutdown_revokes_and_drains","closed_service_refuses_new_open","actual_inflight_sqlite_open_observed","post_open_registration_rechecks_shutdown","unpublished_native_handle_closed"},
]
COUNTS=[
    {"native_witnesses":2,"native_stores":2},
    {"real_handle_closes":1,"reopened_handles":1,"copied_leases":1},
    {"same_space_prior_handles":2,"actual_deletions":1,"actual_backup_renames":1},
]
LABELS=("native-initial","native-ambient-foreign")
def require(ok,reason):
    if not ok:raise ValueError(reason)
def digest(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def strict(raw):
    def pairs(values):
        result={}
        for key,value in values:
            require(key not in result,"duplicate_json_key")
            result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError("nonfinite_json")))
def safe_receipt(r):
    strings={"Version":"native-localstore-witness-v1","Encoding":"anyenc-v1.0.3-decoded-value-roundtrip-v1","Authority":AUTHORITY,
             "InventoryScope":"registered-native-collections-only","NativeBindingScope":"space-state-acl-settings-roots-only"}
    hashes={"OwnerSHA256","SpaceSHA256","SpaceHeaderSHA256","WitnessSHA256"}
    integers={"Generation","Collections","Rows","EncodedValueBytes"}
    booleans={"LocalDecodedRowsComplete":True,"NativeSnapshotProofRequired":True,"NativeIdentityCensusRequired":True,
              "HasNativeSourceAdmission":False,"PermitsDestinationWrites":False}
    require(type(r) is dict and set(r)==set(strings)|hashes|integers|set(booleans)|{"CollectionCoverage"},"receipt_exact_shape")
    require(all(r[k]==v for k,v in strings.items()),"receipt_fixed_scope")
    require(all(type(r[k]) is bool and r[k] is v for k,v in booleans.items()),"receipt_false_authorization")
    require(all(type(r[k]) is str and re.fullmatch("[0-9a-f]{64}",r[k]) for k in hashes),"receipt_hashes")
    require(all(type(r[k]) is int and r[k]>=0 for k in integers) and r["Generation"]>0,"receipt_counts")
    coverage=r["CollectionCoverage"]
    require(type(coverage) is list and len(coverage)==r["Collections"] and 0<len(coverage)<=64,"receipt_collection_coverage")
    for row in coverage:
        require(type(row) is dict and set(row)=={"NameSHA256","Rows","EncodedValueBytes","UnresolvedCollection"},"receipt_collection_shape")
        require(type(row["NameSHA256"]) is str and re.fullmatch("[0-9a-f]{64}",row["NameSHA256"]) and
                type(row["Rows"]) is int and row["Rows"]>=0 and type(row["EncodedValueBytes"]) is int and row["EncodedValueBytes"]>=0 and
                type(row["UnresolvedCollection"]) is bool,"receipt_collection_types")
    require(sum(x["Rows"] for x in coverage)==r["Rows"] and sum(x["EncodedValueBytes"] for x in coverage)==r["EncodedValueBytes"],"receipt_totals")
    return r
def inspect_events(log):
    events=[];streams={};observations={};receipts={}
    for line in log.read_text().splitlines():
        v=strict(line)
        require(type(v) is dict and v.get("Package")==PACKAGE,"executed_native_package")
        events.append({k:v[k] for k in ("Time","Action","Package","Test","Elapsed") if k in v})
        if "Output" in v:
            require(type(v["Output"]) is str,"native_output_type")
            key=v.get("Test","");streams[key]=streams.get(key,"")+v["Output"]
    for method,output in streams.items():
        for line in output.splitlines():
            if line.startswith("NATIVE_OWNED_WITNESS_RECEIPT "):
                _,label,raw=line.split(" ",2)
                require(method==METHODS[0] and label in LABELS and label not in receipts,"native_receipt_method_label")
                receipts[label]=safe_receipt(strict(raw))
            if line.startswith("NATIVE_OWNED_SNAPSHOT_OBSERVATION "):
                _,name,raw=line.split(" ",2)
                require(name==method and name in METHODS and name not in observations,"native_observation_method")
                value=strict(raw);idx=METHODS.index(name)
                require(type(value) is dict and set(value)=={"Facts","Counts"} and type(value["Facts"]) is dict and
                        set(value["Facts"])==FACTS[idx] and all(x is True for x in value["Facts"].values()),"native_observation_facts")
                counts=value["Counts"]
                require(type(counts) is dict and all(type(x) is int and x>=0 for x in counts.values()),"native_observation_count_types")
                if idx<3:require(counts==COUNTS[idx],"native_observation_exact_counts")
                else:
                    require(set(counts)=={"baseline_native_db_fds","observed_inflight_native_db_fds"} and
                            counts["observed_inflight_native_db_fds"]>counts["baseline_native_db_fds"]>0,"native_observed_inflight_descriptors")
                observations[name]=value
    starts=[v["Test"] for v in events if v.get("Action")=="run" and "Test" in v]
    passes=[v["Test"] for v in events if v.get("Action")=="pass" and "Test" in v]
    qualified=(sorted(starts)==sorted(METHODS) and sorted(passes)==sorted(METHODS) and
               not any(v.get("Action") in ("fail","skip") for v in events) and set(observations)==set(METHODS) and set(receipts)==set(LABELS))
    return {"events":events,"starts":starts,"passes":passes,"observations":observations,"receipts":receipts,"qualified":qualified}
def private_dir(p):
    st=p.lstat()
    require(stat.S_ISDIR(st.st_mode) and not p.is_symlink() and stat.S_IMODE(st.st_mode) in (0o700,0o2700),"private_directory_mode")
def audit_private(root,receipts):
    private_dir(root);found={}
    for p in sorted(root.glob("native-case-*/*.witness.bin")):
        require(p.parent.parent==root,"private_frame_parent")
        private_dir(p.parent)
        st=p.lstat()
        require(stat.S_ISREG(st.st_mode) and not p.is_symlink() and stat.S_IMODE(st.st_mode)==0o600 and 0<st.st_size<=64*1024*1024,"private_frame_file")
        label=p.name.removesuffix(".witness.bin")
        require(label in LABELS and label not in found,"private_frame_label")
        r=receipts[label];require(digest(p)==r["WitnessSHA256"],"private_frame_digest")
        data=p.read_bytes();at=0
        def frame():
            nonlocal at
            require(at+8<=len(data),"private_frame_length")
            n=struct.unpack(">Q",data[at:at+8])[0];at+=8
            require(n<=64*1024*1024 and at+n<=len(data),"private_frame_bounds")
            value=data[at:at+n];at+=n;return value
        def number():
            value=frame();require(len(value)==8,"private_uint64_frame");return struct.unpack(">Q",value)[0]
        require(frame()==b"pinkha-localstore-witness-v1" and frame()==r["Encoding"].encode() and frame()==AUTHORITY.encode(),"private_frame_header")
        owner=frame();space=frame()
        require(len(owner)==32 and hashlib.sha256(owner).hexdigest()==r["OwnerSHA256"] and hashlib.sha256(space).hexdigest()==r["SpaceSHA256"],"private_frame_identity_hash")
        require(number()==r["Generation"],"private_frame_generation")
        count=number();require(count==r["Collections"],"private_collection_count")
        names=[];total_rows=0;total_bytes=0;coverage=[]
        for _ in range(count):
            name=frame();require(name and (not names or names[-1]<name),"private_collection_order")
            names.append(name);rows=number();require(rows<=10000,"private_row_bound")
            ids=[];encoded_bytes=0
            for _ in range(rows):
                raw_id=frame();value=frame();require(not ids or ids[-1]<raw_id,"private_row_order");ids.append(raw_id);encoded_bytes+=len(value)
            entry=r["CollectionCoverage"][len(names)-1]
            require(hashlib.sha256(name).hexdigest()==entry["NameSHA256"] and rows==entry["Rows"] and encoded_bytes==entry["EncodedValueBytes"],"private_collection_accounting")
            total_rows+=rows;total_bytes+=encoded_bytes
        require(at==len(data) and total_rows==r["Rows"] and total_bytes==r["EncodedValueBytes"],"private_full_frame_accounting")
        found[label]={"sha256":r["WitnessSHA256"],"bytes":st.st_size,"mode":stat.S_IMODE(st.st_mode),"collections":count,"rows":total_rows,"encoded_value_bytes":total_bytes,
                      "raw_values_published":False,"semantic_reconstruction":False,"hasNativeSourceAdmission":False,"permitsDestinationWrites":False}
    require(set(found)==set(LABELS),"two_private_native_witnesses_required")
    require(receipts[LABELS[0]]==receipts[LABELS[1]],"same_native_snapshot_binding_changed")
    return found
