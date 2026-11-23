import pathlib,hashlib,json
p=pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123/ram-projected-graph-attempt1/result.json")
b=p.read_bytes()
assert len(b)==21501
assert hashlib.sha256(b).hexdigest()=="249c5a4a5a16ce7f39669925d03e804c8dab1517899c487179d123912b66601f"
print(b.decode("utf-8"))
