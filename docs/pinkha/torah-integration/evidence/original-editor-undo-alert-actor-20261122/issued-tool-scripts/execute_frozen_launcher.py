import pathlib,hashlib,runpy
p=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\oe-editorpage-actor-20261122\run_undo_alert_boundary.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='9bd622c904c47ecb825ba1cca3a27d57c20ebce686aac3dbce877844f6bc3525'
runpy.run_path(str(p),run_name='__main__')
