import datetime, hashlib, json, os, pathlib, shutil, stat, subprocess, time, zipfile

repo = "davidpovarsky/anytype-swift"
run_id = 0
head = "UNBOUND"
if run_id <= 0 or len(head) != 40:
    raise RuntimeError("bind one exact activated generation run before execution")
owned = pathlib.Path(r"C:\Users\DAVID\Code") / f"otzaria-schema-rpc-generation-observer-20261122-{run_id}"
owned.mkdir(exist_ok=False)
gh = shutil.which("gh")
if not gh:
    raise RuntimeError("GitHub CLI unavailable")
deadline = time.monotonic() + 3300
record = {"schema": "otzaria.finite-schema-rpc-generation-observer/1", "run_id": run_id, "expected_head": head, "events": [], "status": "OBSERVING", "owned_directory": str(owned)}


def save():
    temporary = owned / "WATCHER_RESULT.json.tmp"
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, owned / "WATCHER_RESULT.json")


def api(path, seconds=35):
    result = subprocess.run([gh, "api", path], capture_output=True, timeout=seconds)
    if result.returncode:
        raise RuntimeError("GitHub API read failed: " + str(result.returncode))
    return json.loads(result.stdout)


def event(kind, **values):
    record["events"].append({"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "event": kind, **values})
    save()


try:
    previous = None
    while time.monotonic() < deadline:
        try:
            run = api(f"repos/{repo}/actions/runs/{run_id}")
        except (subprocess.TimeoutExpired, RuntimeError, json.JSONDecodeError) as error:
            event("READ_FAILED", error_type=type(error).__name__)
            time.sleep(min(30, max(0, deadline - time.monotonic())))
            continue
        if run["head_sha"] != head or run["run_attempt"] != 1 or run["head_branch"] != "codex/otzaria-schema-rpc-copy-20261122" or run["event"] != "push":
            raise RuntimeError("Run source/attempt/event differs")
        state = (run["status"], run.get("conclusion"))
        if state != previous:
            event("RUN_STATE", status=state[0], conclusion=state[1]); previous = state
        if state[0] == "completed":
            record["run"] = {key: run.get(key) for key in ("id", "head_sha", "head_branch", "run_attempt", "event", "status", "conclusion", "html_url", "created_at", "updated_at")}
            break
        time.sleep(min(45, max(0, deadline - time.monotonic())))
    else:
        raise TimeoutError("Finite generation observer deadline elapsed")
    data = api(f"repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100")
    wanted = f"Otzaria-Schema-RPC-Generation-{run_id}-1"
    artifacts = [a for a in data.get("artifacts", []) if a["name"] == wanted and not a["expired"]]
    if len(artifacts) != 1:
        raise RuntimeError("Expected exact single generation artifact")
    artifact = artifacts[0]
    if artifact["workflow_run"]["head_sha"] != head or artifact["workflow_run"]["id"] != run_id:
        raise RuntimeError("Artifact source differs")
    if not 0 < artifact["size_in_bytes"] <= 256 * 1024 * 1024:
        raise RuntimeError("Unexpected generation artifact size")
    archive = owned / "generation-artifact.zip"
    with archive.open("xb") as out:
        done = subprocess.run([gh, "api", f"repos/{repo}/actions/artifacts/{artifact['id']}/zip"], stdout=out, stderr=subprocess.PIPE, timeout=180)
    if done.returncode:
        raise RuntimeError("Artifact download failed")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if archive.stat().st_size != artifact["size_in_bytes"] or artifact.get("digest") != "sha256:" + digest:
        raise RuntimeError("Archive bytes differ from actual GitHub digest/size")
    extracted = owned / "extracted"; extracted.mkdir()
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist()) != len(set(z.namelist())) or z.testzip() is not None:
            raise RuntimeError("Artifact duplicate member/CRC failure")
        if sum(i.file_size for i in z.infolist()) > 512 * 1024 * 1024:
            raise RuntimeError("Unexpected expanded source evidence size")
        for info in z.infolist():
            path = pathlib.PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or any(":" in part or "\\" in part for part in path.parts) or stat.S_ISLNK(info.external_attr >> 16):
                raise RuntimeError("Unsafe artifact member")
            target = extracted.joinpath(*path.parts)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True); continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as source, target.open("xb") as destination:
                shutil.copyfileobj(source, destination)
    index = json.loads((extracted / "EVIDENCE_INDEX.json").read_bytes())
    actual = {p.relative_to(extracted).as_posix() for p in extracted.rglob("*") if p.is_file()}
    expected = {row["path"] for row in index["files"]}
    if len(expected) != len(index["files"]) or actual != expected | {"EVIDENCE_INDEX.json"}:
        raise RuntimeError("Artifact manifest membership differs")
    for row in index["files"]:
        path = extracted / row["path"]
        raw = path.read_bytes()
        if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise RuntimeError("Artifact payload hash differs")
    result = json.loads((extracted / "RESULT.json").read_bytes())
    if result.get("control_head") != head or result.get("manifest_sha256") != "48c43f21ac8f31b3c6bd7022e838273046c3baa001813bb598be6f4aaf35c7a6":
        raise RuntimeError("Generation result source or input manifest differs")
    record["artifact"] = {"id": artifact["id"], "name": artifact["name"], "bytes": archive.stat().st_size, "sha256": digest, "path": str(archive), "payloads": len(index["files"])}
    record["generation_result"] = result
    record["status"] = "TERMINAL_ARTIFACT_RETAINED"
    event("ARTIFACT_VERIFIED", artifact_id=artifact["id"], generation_status=result.get("status"))
except BaseException as error:
    record.update({"status": "OBSERVER_FAILED", "error_type": type(error).__name__, "error": str(error)})
    save()
    raise
finally:
    save()
    print(json.dumps(record))
