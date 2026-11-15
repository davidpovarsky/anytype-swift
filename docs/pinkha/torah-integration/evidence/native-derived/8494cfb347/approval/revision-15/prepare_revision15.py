"""Render the isolated T5 native revision from immutable r14 and scoped sources."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.request

PIN = "d98420b1113536afd08cde6de9a5816f6d27ffff"
ROOT = Path(__file__).resolve().parents[8]
OUT = Path(__file__).resolve().parent
R14 = OUT.parent / "revision-14"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def section(path, before, after):
    result = "diff --git a/" + path + " b/" + path + "\n"
    if not before:
        result += "new file mode 100644\n"
    return result + "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
        fromfile="a/" + path if before else "/dev/null", tofile="b/" + path))


def apply_section(lines, original):
    source, output, offset, n = original.splitlines(True), [], 0, 0
    while n < len(lines):
        match = re.match(r"@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@", lines[n])
        if not match:
            n += 1
            continue
        start = max(0, int(match[1]) - 1)
        output.extend(source[offset:start])
        offset, n = start, n + 1
        while n < len(lines) and not lines[n].startswith("@@"):
            line = lines[n]
            if line.startswith((" ", "-")):
                if source[offset] != line[1:]:
                    raise RuntimeError("r14 context mismatch")
                if line.startswith(" "):
                    output.append(line[1:])
                offset += 1
            elif line.startswith("+"):
                output.append(line[1:])
            n += 1
    output.extend(source[offset:])
    return "".join(output)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--heart-source", type=Path)
    args = parser.parse_args()
    prior = json.loads((R14 / "native-heart-integration.json").read_text())
    patch = (R14 / "native-heart-integration.patch").read_bytes().replace(b"\r\n", b"\n")
    if sha(patch) != prior["patch_sha256"]:
        raise RuntimeError("immutable r14 patch differs")
    sections = {}
    current = None
    for line in patch.decode().splitlines(True):
        if line.startswith("diff --git "):
            current = line.strip().split(" b/", 1)[1]
            sections[current] = []
        sections[current].append(line)
    entries = {item["path"]: item for item in prior["files"]}
    def original(path):
        if args.heart_source:
            if subprocess.check_output(["git", "-C", str(args.heart_source), "rev-parse", "HEAD"], text=True).strip() != PIN:
                raise RuntimeError("wrong Heart source SHA")
            content = subprocess.check_output(["git", "-C", str(args.heart_source), "show", PIN + ":" + path]).decode()
        else:
            url = "https://raw.githubusercontent.com/anyproto/anytype-heart/" + PIN + "/" + path
            content = urllib.request.urlopen(url, timeout=30).read().decode()
        if path in entries and sha(content.encode()) != entries[path]["before_sha256"]:
            raise RuntimeError("pinned original source differs from r14 provenance: " + path)
        return content
    replacement = {}
    for source, target in [("torah", "torah"), ("engine", "torahindex")]:
        for path in (ROOT / "Modules/PinkhaHeart" / source).glob("*.go"):
            content = path.read_text(encoding="utf8").replace(
                "github.com/davidpovarsky/anytype-swift/Modules/PinkhaHeart/torah",
                "github.com/anyproto/anytype-heart/core/pinkha/torah")
            replacement["core/pinkha/" + target + "/" + path.name] = ("", content)
    replacement["core/pinkha/torah/testdata/derived-query-golden.json"] = ("", (
        ROOT / "Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/Fixtures/derived-query-golden.json").read_text(encoding="utf8"))
    bundle_path = "pkg/lib/bundle/pinkha_torah.go"
    bundle = apply_section(sections[bundle_path], "")
    bundle = bundle.replace("if key==torah.VersionKey{format=model.RelationFormat_number}",
        "if key==torah.VersionKey||key==torah.RelatedVersionKey{format=model.RelationFormat_number}\n"
        "  if key==torah.RelatedSourcesKey{format=model.RelationFormat_tag}")
    replacement[bundle_path] = ("", bundle)
    filter_path = "pkg/lib/database/filter.go"
    before = original(filter_path)
    native_filter = apply_section(sections[filter_path], before)
    old = "func makeFilter(spaceID string, rawFilter FilterRequest, store ObjectStore) (Filter, error) {\n"
    private = """ if string(rawFilter.RelationKey)==torah.RelatedSourcesKey {
  if rawFilter.Condition!=model.BlockContentDataviewFilter_In {return nil,fmt.Errorf("private Torah lookup supports exact positive In only")}
  strings,ok:=rawFilter.Value.TryStringList()
  if !ok||len(strings)==0{return nil,fmt.Errorf("private Torah lookup requires nonempty string list")}
  values:=make([]domain.Value,0,len(strings))
  for _,value:=range strings {if value==""{return nil,fmt.Errorf("empty Torah lookup identity")};values=append(values,domain.String(value))}
  return FiltersAnd{
   FilterIn{Key:domain.RelationKey(torah.ReadyKey),Value:[]domain.Value{domain.Bool(true)}},
   FilterIn{Key:domain.RelationKey(torah.RelatedVersionKey),Value:[]domain.Value{domain.Int64(torah.RelatedVersion)}},
   FilterIn{Key:rawFilter.RelationKey,Value:values},
  },nil
 }
"""
    if native_filter.count(old) != 1:
        raise RuntimeError("filter wrapper mismatch")
    replacement[filter_path] = (before, native_filter.replace(old, old + private))
    option_path = "core/block/object/objectcreator/relation_option.go"
    option_before = original(option_path)
    option_after = apply_section(sections[option_path], option_before)
    old = "torah.IsProperty(details.GetString(bundle.RelationKeyRelationKey))"
    if option_after.count(old) != 1:
        raise RuntimeError("native option guard mismatch")
    replacement[option_path] = (option_before, option_after.replace(old, "torah.IsLocalKey(details.GetString(bundle.RelationKeyRelationKey))"))
    relation_path = "core/block/object/objectcreator/relation.go"
    relation_before = original(relation_path)
    relation_after = relation_before.replace('"github.com/anyproto/anytype-heart/core/domain"',
        '"github.com/anyproto/anytype-heart/core/domain"\n torah "github.com/anyproto/anytype-heart/core/pinkha/torah"')
    old = '\tif !details.Has(bundle.RelationKeyRelationFormat) {'
    if relation_after.count(old) != 1:
        raise RuntimeError("native relation creator boundary mismatch")
    relation_after = relation_after.replace(old, ''' if torah.IsPrivateKey(details.GetString(bundle.RelationKeyRelationKey)) {
  return "",nil,fmt.Errorf("private Torah lookup metadata is not an installable Property")
 }
''' + old)
    replacement[relation_path] = (relation_before, relation_after)
    detail_path = "core/details.go"
    detail_before = original(detail_path)
    detail_after = apply_section(sections[detail_path], detail_before)
    old = ' for _,key:=range req.RelationKeys {\n  if torah.IsProperty(key)'
    if detail_after.count(old) != 1:
        raise RuntimeError("native object attachment boundary mismatch")
    detail_after = detail_after.replace(old, ''' for _,key:=range req.RelationKeys {
  if torah.IsPrivateKey(key){return &pb.RpcObjectRelationAddResponse{Error:&pb.RpcObjectRelationAddResponseError{Code:pb.RpcObjectRelationAddResponseError_BAD_INPUT,Description:"private Torah lookup metadata cannot be attached"}}}
  if torah.IsProperty(key)''')
    replacement[detail_path] = (detail_before, detail_after)
    type_path = "core/relations.go"
    type_before = original(type_path)
    type_after = type_before.replace('"github.com/anyproto/anytype-heart/core/domain"',
        '"github.com/anyproto/anytype-heart/core/domain"\n torah "github.com/anyproto/anytype-heart/core/pinkha/torah"')
    old = 'func (mw *Middleware) ObjectTypePropertyAdd(cctx context.Context, req *pb.RpcObjectTypePropertyAddRequest) *pb.RpcObjectTypePropertyAddResponse {\n'
    if type_after.count(old) != 1:
        raise RuntimeError("native Type attachment RPC boundary mismatch")
    type_after = type_after.replace(old, old + ''' if torah.IsPrivateKey(req.Key){return &pb.RpcObjectTypePropertyAddResponse{Error:&pb.RpcObjectTypePropertyAddResponseError{Code:pb.RpcObjectTypePropertyAddResponseError_BAD_INPUT,Description:"private Torah lookup metadata cannot be installed on a Type"}}}
''')
    replacement[type_path] = (type_before, type_after)
    test_path = "pkg/lib/localstore/objectstore/spaceindex/pinkha_torah_related_test.go"
    replacement[test_path] = ("", (ROOT / "Tools/PinkhaNativeDerived/native_test_templates/pinkha_torah_related_test.go").read_text(encoding="utf8"))
    for path, (original, content) in replacement.items():
        sections[path] = [section(path, original, content)]
        entries[path] = dict(path=path, before_sha256=sha(original.encode()) if original else None,
            after_sha256=sha(content.encode()))
    result = "".join("".join(sections[path]) for path in sorted(sections)).encode()
    (OUT / "native-heart-integration.patch").write_bytes(result)
    inventory = dict(heart_sha=PIN, patch_sha256=sha(result), status="SOURCE_CANDIDATE_RUNTIME_PROOF_REQUIRED",
        previous_patch_sha256=prior["patch_sha256"], public_projection_version=1,
        features={"t5_related_lookup": 1}, cache_proof_generation="pinkha-torah-cache-v2",
        required_client_feature_flag="PINKHA_NATIVE_T5_LOOKUP_V1", client_enablement="DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF",
        files=[entries[path] for path in sorted(entries)])
    (OUT / "native-heart-integration.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf8")
    print(json.dumps(dict(patch_sha256=inventory["patch_sha256"], files=len(entries), enablement=inventory["client_enablement"])))


if __name__ == "__main__":
    main()
