#!/usr/bin/env python3
"""Run two independent native accounts through signed ACL transport and reconnect."""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sys
import time

import contract
sys.path.insert(0, str(contract.ROOT / "Tools/TorahNativeOperations"))
import run_native_clients as retained
from build import source_snapshot

ARGS=["-test.run","^"+contract.METHOD+"$","-test.count=1","-test.v","-test.timeout=1200s"]


class OwnedPeers(retained.OwnedDocker):
    def start_peer(self, role, network, directory, binary, build, deadline):
        contract.require(role in {"owner","member"}, "Unknown independent account role")
        resource=dict(kind="container",name=self.prefix+"-member-acl-"+role,id=None,role=role,private=str(directory),log="native.log")
        self.resources.append(resource)
        arguments=["container","create","--name",resource["name"],"--label",retained.OWNER_LABEL+"="+self.owner,
            "--platform","linux/amd64","--network",network["Name"],"--read-only","--init=false","--cap-drop","ALL",
            "--security-opt","no-new-privileges","--user",f"{os.getuid()}:{os.getgid()}","--cpus","1","--memory","2g",
            "--pids-limit","256","--workdir","/private","--tmpfs","/tmp:rw,nosuid,nodev,size=128m,mode=1777",
            "--mount",f"type=bind,src={directory},dst=/private","--mount",f"type=bind,src={binary},dst=/fixture/native.test,readonly",
            "-e","PINKHA_MEMBER_ACL_ROLE="+role,"-e","PINKHA_T2_CLIENT_NONCE="+self.owner,
            "-e","PINKHA_T2_CLIENT_FIXTURE_SHA="+build["fixture_sha256"],
            "-e","PINKHA_COHERENT_PEER_PHASE=independent-member",
            "-e","PINKHA_COHERENT_RUNTIME_VERSION="+build["runtime_version"],
            "-e","GOMAXPROCS=2","-e","GOMEMLIMIT=768MiB",contract.IMAGE,"/fixture/native.test",*ARGS]
        resource["id"]=self.command(arguments,"create-member-"+role,self.remaining(deadline))
        contract.require(re.fullmatch("[0-9a-f]{64}",resource["id"]), "Missing real member process identity")
        self.command(["container","start",resource["id"]],"start-member-"+role,self.remaining(deadline))
        return resource

    def wait_peer(self, resource, phase, seconds=120):
        contract.require(phase in contract.PHASES[resource["role"]], "Unreviewed native phase")
        deadline=time.monotonic()+seconds
        path=Path(resource["private"])/(phase+".json")
        next_check=0
        while time.monotonic()<deadline:
            if path.exists(): return contract.load(path)
            if time.monotonic()>=next_check:
                info=self.find(resource,deadline)
                contract.require(info and info["State"].get("Running") is True, "Native member exited before phase receipt")
                next_check=time.monotonic()+5
            time.sleep(.2)
        raise TimeoutError("Bounded member ACL phase did not finish: "+phase)


def validate_container(info, owner, role, phase, network, directory, binary, image_id, build):
    config, host, network_settings = info.get("Config", {}), info.get("HostConfig", {}), info.get("NetworkSettings", {})
    contract.require(config.get("Labels", {}).get(retained.OWNER_LABEL) == owner and config.get("Image") == contract.IMAGE
                     and info.get("Image") == image_id and config.get("User") == f"{os.getuid()}:{os.getgid()}"
                     and info.get("Path") == "/fixture/native.test" and info.get("Args") == ARGS, "Wrong owned native executable")
    contract.require(host.get("ReadonlyRootfs") is True and host.get("Privileged") is False and host.get("CapDrop") == ["ALL"]
                     and "no-new-privileges" in host.get("SecurityOpt", []) and not host.get("PortBindings")
                     and not host.get("PidMode") and not host.get("Init") and host.get("NanoCpus") == 1000000000
                     and host.get("Memory") == 2 * 1024**3 and host.get("PidsLimit") == 256,
                     "Native process isolation or resource limits differ")
    mounts = info.get("Mounts", [])
    destinations = [entry.get("Destination") for entry in mounts]
    contract.require(len(destinations) == len(set(destinations)), "Repeated native mount destination")
    binds = {entry["Destination"]: entry for entry in mounts if entry.get("Type") == "bind"}
    contract.require(set(binds) == {"/private", "/fixture/native.test"}
                     and binds["/private"].get("Source") == str(directory) and binds["/private"].get("RW") is True
                     and binds["/fixture/native.test"].get("Source") == str(binary) and binds["/fixture/native.test"].get("RW") is False
                     and all(entry.get("Type") == "bind" or (entry.get("Type") == "tmpfs" and entry.get("Destination") == "/tmp") for entry in mounts),
                     "Native process can see another store/build tree")
    networks = network_settings.get("Networks", {})
    if network:
        contract.require(host.get("NetworkMode") == network["Name"] and set(networks) == {network["Name"]}
                         and networks[network["Name"]].get("NetworkID") == network["Id"], "Peer has another network")
    else:
        contract.require(host.get("NetworkMode") == "none" and set(networks) == {"none"}
                         and not networks["none"].get("IPAddress"), "Cold reopen can reach a peer")
    env = dict(item.split("=", 1) for item in config.get("Env", []) if "=" in item)
    expected = dict(PINKHA_MEMBER_ACL_ROLE=role, PINKHA_T2_CLIENT_NONCE=owner, PINKHA_T2_CLIENT_FIXTURE_SHA=build["fixture_sha256"],
                    PINKHA_COHERENT_PEER_PHASE=phase, PINKHA_COHERENT_RUNTIME_VERSION=build["runtime_version"])
    contract.require(all(env.get(key) == value for key, value in expected.items())
                     and not any(key in env for key in ("PINKHA_T2_CLIENT_SCENARIO", "PINKHA_T2_CRASH_PHASE",
                                                       "PINKHA_T2_OBSERVED_REMOVE_PHASE", "PINKHA_T2_CONCURRENT_REPLACE_PHASE")),
                     "Another old suite or phase was selected")


def live_identity(info, report):
    host_pid = info.get("State", {}).get("Pid")
    contract.require(type(host_pid) is int and host_pid > 0 and info["State"].get("Running") is True,
                     "Actual native host process not running")
    contract.require(os.readlink(f"/proc/{host_pid}/ns/net") == report["network_namespace"], "Observed native namespace differs")
    return dict(container_id=info["Id"], host_pid=host_pid, namespace=report["network_namespace"],
                sandbox_id=info["NetworkSettings"]["SandboxID"], peer_id=report["peer_id"])



def send(directory, phase, nonce, **public):
    contract.require(set(public) <= {"peer","state","head"}, "Only public routing and signed-head identifiers may be seeded")
    if "state" in public: contract.validate_state(public["state"])
    path=directory/(phase+".command.json")
    contract.require(not path.exists(), "Phase command cannot be replayed")
    contract.save(path,dict(protocol=contract.PROTOCOL,nonce=nonce,phase=phase,**public))


def execute(args, receipt, docker):
    build=contract.load(args.evidence/"build.json")
    contract.validate_build(build,args.expected_app_sha,receipt["run_id"],receipt["run_attempt"])
    before=source_snapshot(args.control)
    contract.require(before==contract.load(args.evidence/"build-control-source-after.json"), "Controller changed after original build")
    binary=args.native_work/build["binary_path"]
    contract.require(binary.is_file() and not binary.is_symlink() and contract.digest(binary)==build["binary_sha256"], "Executable changed")
    receipt.update(build_receipt_sha256=contract.digest(args.evidence/"build.json"),binary_sha256=build["binary_sha256"],
                   fixture_sha256=build["fixture_sha256"],native_source_run=contract.NATIVE_RUN,
                   patch_sha256=contract.PATCH,inventory_sha256=contract.INVENTORY)
    image=json.loads(docker.command(["image","inspect",contract.IMAGE],"inspect-native-image"))[0]
    contract.require(image.get("Os")=="linux" and image.get("Architecture")=="amd64","Wrong runtime image")
    network_resource,network=docker.network()
    directories={}
    for role in ("owner","member"):
        directory=docker.private/role;directory.mkdir(mode=0o700);(directory/"account-root").mkdir(mode=0o700)
        contract.save(directory/"ownership.json",dict(protocol=contract.PROTOCOL,nonce=docker.owner,role=role,synthetic_only=True))
        directories[role]=directory
    resources={}
    for role in directories:
        resources[role]=docker.start_peer(role,network,directories[role],binary,build,time.monotonic()+60)
    native_identities={}
    identities={}
    for role in resources:
        report=docker.wait_peer(resources[role],"identity",240)
        identity=report.get("identity",{})
        contract.require(set(identity)=={"account_id","peer_id","ip","port","network_namespace"} and
                         all(isinstance(identity[k],str) and identity[k] for k in ("account_id","peer_id","ip","network_namespace")) and
                         type(identity["port"]) is int and 0<identity["port"]<=65535, "Malformed public native identity")
        contract.validate_common(report,"identity",role,docker.owner,build,identity)
        info=docker.find(resources[role])
        validate_container(info,docker.owner,role,"independent-member",network,directories[role],binary,image["Id"],build)
        native_identities[role]=live_identity(info,report)
        contract.require(info["NetworkSettings"]["Networks"][network["Name"]]["IPAddress"]==identity["ip"]==report["actual_ipv4"][0],
                         "Native and Docker addresses differ")
        identities[role]=identity
    owner,member=identities["owner"],identities["member"]
    contract.require(all(owner[k]!=member[k] for k in ("account_id","peer_id","ip","network_namespace")), "Same account/device/network reused")
    contract.require(all(native_identities["owner"][k]!=native_identities["member"][k] for k in
                         ("container_id","host_pid","namespace","sandbox_id","peer_id")), "Processes are not independent")
    contract.require(set(docker.find(network_resource).get("Containers",{}))=={v["id"] for v in resources.values()}, "Unexpected native LAN participant")
    receipt["native_peers"]=native_identities
    receipt["independent_wallets"]=True
    receipt["seed_fields"]=["public_account_and_peer_identity","public_operation_identity_and_hashes","acl_head_id"]
    receipt["seeded_private_key_files"]=0
    state=contract.load(directories["owner"]/"state.json")
    contract.validate_state(state)
    contract.require(state["AccountID"]==owner["account_id"], "Operation owner differs from native account")
    def read(role,phase,permission,head=None,seconds=120):
        value=docker.wait_peer(resources[role],phase,seconds)
        contract.validate_common(value,phase,role,docker.owner,build,identities[role])
        contract.validate_acl(value,state,owner,member,permission,head)
        if phase in contract.WIRE_PHASES:
            raw=(directories[role]/(phase+".pb")).read_bytes()
            contract.require(value["wire_sha256"]==contract.sha(raw), "Native response bytes changed")
            if phase in {"publication-fence","revoked"}:
                contract.require(value.get("snapshot_present") is False and
                    value.get("error_code")==contract.validate_denial(raw,{4,9}), "Revoked read published data")
            elif phase=="final":
                contract.require(value.get("snapshot_present") is False and value.get("stopped_error_code")==5 and
                    contract.validate_denial(raw,{5})==5, "Stopped account published data")
            else:
                contract.require(value["variant_sha256"]==contract.validate_positive_wire(raw,state,identities[role]["account_id"]),
                                 "Native signed operation differed across members")
        return value
    send(directories["owner"],"grant",docker.owner,peer=member)
    grant_owner=read("owner","grant",3,seconds=240)
    send(directories["member"],"grant",docker.owner,peer=owner,state=state,head=grant_owner["acl_head"])
    grant_member=read("member","grant",3,grant_owner["acl_head"],360)
    contract.same_acl(grant_owner,grant_member)
    contract.require(grant_owner["variant_sha256"]==grant_member["variant_sha256"], "Member did not receive owner's original signed operation")
    send(directories["owner"],"reader",docker.owner)
    reader_owner=read("owner","reader",4)
    contract.require(reader_owner["acl_head"]!=grant_owner["acl_head"], "No signed role change occurred")
    send(directories["member"],"reader",docker.owner,head=reader_owner["acl_head"])
    reader_member=read("member","reader",4,reader_owner["acl_head"])
    contract.same_acl(reader_owner,reader_member)
    for value in (reader_owner,reader_member):
        contract.require(value["variant_sha256"]==grant_owner["variant_sha256"], "Role change altered original provenance")

    docker.command(["network","disconnect",network_resource["id"],resources["member"]["id"]],"detach-independent-member",30)
    detached=docker.find(resources["member"])
    contract.require(detached["NetworkSettings"].get("Networks")=={} and
                     set(docker.find(network_resource).get("Containers",{}))=={resources["owner"]["id"]},
                     "Actual member network was not detached")
    contract.require(live_identity(detached,reader_member)==native_identities["member"], "Detach replaced the native process")
    send(directories["member"],"offline",docker.owner)
    offline=read("member","offline",4,reader_owner["acl_head"],90)
    contract.require(offline.get("real_native_preparation_captured") is True, "Native preparation was not retained before revocation")
    contract.same_acl(reader_owner,offline)
    send(directories["owner"],"revoke",docker.owner)
    revoked_owner=read("owner","revoke",0)
    contract.require(revoked_owner["acl_head"]!=reader_owner["acl_head"] and
                     revoked_owner["read_key_id"]!=reader_owner["read_key_id"], "Revocation did not rotate actual read key")
    contract.require(docker.find(resources["member"])["NetworkSettings"].get("Networks")=={}, "Reader reconnected before unseen-revocation check")
    send(directories["member"],"unknown-revocation",docker.owner,head=revoked_owner["acl_head"])
    unknown=read("member","unknown-revocation",4,reader_owner["acl_head"],90)
    contract.same_acl(reader_owner,unknown)
    contract.require(unknown.get("policy")=="last-known-local-authority-before-native-revocation-observation" and
                     unknown.get("unseen_owner_head")==revoked_owner["acl_head"] and
                     unknown["variant_sha256"]==grant_owner["variant_sha256"], "Unseen revocation policy was overstated")
    # The owned bridge uses Docker IPAM. Rejoining the same live process must
    # not request a static address from an automatically allocated subnet.
    docker.command(["network","connect",network_resource["id"],resources["member"]["id"]],"reconnect-independent-member",30)
    connected=docker.find(resources["member"])
    contract.require(set(connected["NetworkSettings"].get("Networks",{}))=={network["Name"]} and
                     connected["NetworkSettings"]["Networks"][network["Name"]]["NetworkID"]==network["Id"],
                     "Reader did not reconnect to its original isolated network")
    reconnect_ip=connected["NetworkSettings"]["Networks"][network["Name"]]["IPAddress"]
    contract.require(str(ipaddress.IPv4Address(reconnect_ip))==reconnect_ip and reconnect_ip!=owner["ip"],
                     "Daemon did not assign a distinct valid member address")
    contract.require(set(docker.find(network_resource).get("Containers",{}))=={v["id"] for v in resources.values()},
                     "Reconnect changed the owned network participants")
    contract.require(live_identity(connected,reader_member)==native_identities["member"], "Reconnect replaced member process")
    receipt["network_reconnect"]=dict(status="DAEMON_CONNECTED_NATIVE_REVOCATION_PENDING",
                                     original_ipv4=member["ip"], assigned_ipv4=reconnect_ip,
                                     address_assignment="DOCKER_IPAM", exact_revocation_head=revoked_owner["acl_head"])
    send(directories["member"],"reconnect",docker.owner,peer=owner,head=revoked_owner["acl_head"])
    fence=read("member","publication-fence",0,revoked_owner["acl_head"],150)
    revoked_member=read("member","revoked",0,revoked_owner["acl_head"])
    contract.same_acl(revoked_owner,fence)
    contract.same_acl(revoked_owner,revoked_member)
    contract.require(fence["actual_ipv4"]==revoked_member["actual_ipv4"]==[reconnect_ip],
                     "Reconnected native address differs from the actual Docker assignment")
    contract.require(fence.get("prepared_before_revocation") is True and fence.get("finalized_after_observed_revocation") is True,
                     "Missing interleaved native publication fence")
    receipt["network_detach"]=dict(status="PASS_DAEMON_DETACH_AND_NATIVE_NO_INTERFACE",
                                  offline_receipt_sha256=contract.digest(directories["member"]/"offline.json"))
    receipt["network_reconnect"]["status"]="PASS_SAME_NATIVE_PROCESS_RECONNECTED"
    for role in directories:
        send(directories[role],"stop",docker.owner)
    results={}
    stores={}
    for role,resource in resources.items():
        final=read(role,"final",0,revoked_owner["acl_head"],90)
        contract.require(final.get("account_stop_verified") is True and final.get("test_passed") is True and
                         final["rpc_calls"].get("AccountStop")==final["rpc_calls"].get("AppShutdown")==1 and
                         final.get("returned_byte_calls")==final["rpc_calls"], "Account lifecycle did not stop")
        contract.require(docker.command(["container","wait",resource["id"]],"wait-native-"+role,90)=="0","Native test failed")
        info=docker.find(resource)
        contract.require(info["State"].get("Running") is False and info["State"].get("ExitCode")==0,"Native exit not observed")
        log=directories[role]/"native.log"
        docker.command(["container","logs",resource["id"]],"native-log-"+role,30,log)
        text=log.read_text()
        starts=re.findall(r"^=== RUN\s+(\S+)\s*$",text,re.M)
        terminals=re.findall(r"^--- (PASS|FAIL|SKIP): (\S+) \(",text,re.M)
        contract.require(starts==[contract.METHOD] and terminals==[("PASS",contract.METHOD)] and "PASS" in text.splitlines(),
                         "Only the new actual native method may pass")
        files=list((directories[role]/"account-root").rglob("*.db"))
        contract.require(files and all(p.is_file() and not p.is_symlink() for p in files),"Missing actual independent database")
        stores[role]={(p.stat().st_dev,p.stat().st_ino) for p in files}
        results[role]=dict(method=contract.METHOD,passed=1,failed=0,skipped=0,log_sha256=contract.digest(log))
    contract.require(not stores["owner"].intersection(stores["member"]), "Independent accounts shared database inodes")
    contract.require(source_snapshot(args.control)==before and contract.digest(binary)==build["binary_sha256"], "Executed source or binary changed")
    contract.save(args.evidence/"member-control-source-after.json",source_snapshot(args.control))
    receipt.update(status=contract.PASS,network_acl_transport="PASS_DISTINCT_MEMBERS_SIGNED_GRANT_ROLE_REVOKE",
                   observed_revocation_publication_fence="PASS_REAL_PREPARE_THEN_REMOTE_REVOKE_THEN_NATIVE_FINALIZE",
                   native_results=results,actual_native_processes=2,actual_named_pass=2,actual_fail=0,actual_skip=0,
                   distinct_database_inodes=True,old_test_methods_executed=0)


def main():
    parser=argparse.ArgumentParser(__doc__)
    for name in ("control","native-work","private","evidence"): parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--expected-app-sha",required=True)
    args=parser.parse_args()
    for name in ("control","native_work","private","evidence"): setattr(args,name,getattr(args,name).resolve())
    os.umask(0o077)
    args.evidence.mkdir(parents=True,exist_ok=True)
    path=args.evidence/"receipt.json"
    contract.require(not path.exists() and not args.private.exists(),"Fresh owned member attempt required")
    args.private.mkdir(mode=0o700)
    receipt=dict(protocol=contract.PROTOCOL,status="NOT_RUN",app_sha=args.expected_app_sha,
                 run_id=os.environ.get("GITHUB_RUN_ID"),run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),commands=[],**contract.LIMITS)
    contract.require(contract.is_hash(args.expected_app_sha,40) and (receipt["run_id"] or "").isdigit() and
                     (receipt["run_attempt"] or "").isdigit(),"Genuine run/source identity required")
    checkpoint=lambda:contract.save(path,receipt)
    docker=OwnedPeers(args.private,receipt,checkpoint)
    contract.save(args.private/"owner.json",dict(protocol=contract.PROTOCOL,nonce=docker.owner))
    previous={number:signal.getsignal(number) for number in (signal.SIGINT,signal.SIGTERM)}
    cancelled=False
    def cancel(number,_):
        nonlocal cancelled
        if not cancelled:
            cancelled=True
            raise KeyboardInterrupt(signal.Signals(number).name)
    for number in previous:signal.signal(number,cancel)
    try:
        execute(args,receipt,docker)
    except BaseException as error:
        receipt.update(status="CANCELLED" if isinstance(error,KeyboardInterrupt) else "FAIL",error_type=type(error).__name__)
    finally:
        try:
            docker.cleanup()
            receipt["evidence_export"]=contract.export(args.private,args.evidence/"actual")
            if receipt["status"]==contract.PASS:
                required={role+"/"+name for role,names in contract.PUBLISHED.items() for name in names}
                contract.require(receipt["evidence_export"]["status"]=="PASS_TWO_DISTINCT_WALLET_SECRET_SCAN" and
                                 set(receipt["evidence_export"]["files"])==required,"Incomplete original member proof")
            contract.require(contract.load(args.private/"owner.json")==dict(protocol=contract.PROTOCOL,nonce=docker.owner),"Owned cleanup boundary changed")
            shutil.rmtree(args.private)
            receipt["owned_data_cleanup"]="PASS"
        except BaseException as error:
            receipt.update(status="FAIL",cleanup_or_publication_error=type(error).__name__)
        for number,handler in previous.items():signal.signal(number,handler)
    okay=retained.finish_evidence(receipt,args.evidence,path,checkpoint,emit_notice=False)
    return int(not okay or receipt["status"]!=contract.PASS)


if __name__=="__main__":
    raise SystemExit(main())
