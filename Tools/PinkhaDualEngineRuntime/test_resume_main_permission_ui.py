import importlib.util, os, pathlib, tempfile, unittest, hashlib
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("ui_continuation",HERE/"resume_main_permission_ui.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class CompilerIdentityControls(unittest.TestCase):
 def fixture(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
  root=pathlib.Path(t.name)
  (root/"AnyTypeTests/Pinkha").mkdir(parents=True)
  (root/"AnytypeTests/Pinkha").mkdir(parents=True)
  name="Sample.swift";a=root/"AnyTypeTests/Pinkha"/name;b=root/"AnytypeTests/Pinkha"/name
  a.write_bytes(b"actual source\n");os.link(a,b)
  sha=hashlib.sha256(a.read_bytes()).hexdigest()
  listing=(str(b)+"\n").encode()
  log=("SwiftCompile normal arm64 "+str(b)+" (in target 'AnytypeTests' from project 'Anytype')\n").encode()
  files={"AnyTypeTests/Pinkha/"+name:{"bytes":a.stat().st_size,"sha256":sha}}
  return root,name,a,b,sha,listing,log,files
 def test_accepts_same_inode_with_original_compiler_and_inventory(self):
  root,name,a,b,sha,listing,log,files=self.fixture()
  self.assertTrue(m.verify_compiler_pair(root,listing,log,name,sha,files)["sameActualFile"])
 def test_identical_bytes_in_a_different_file_refuse(self):
  root,name,a,b,sha,listing,log,files=self.fixture();b.unlink();b.write_bytes(a.read_bytes())
  with self.assertRaises(AssertionError):m.verify_compiler_pair(root,listing,log,name,sha,files)
 def test_symlink_alias_refuses(self):
  root,name,a,b,sha,listing,log,files=self.fixture();b.unlink();b.symlink_to(a)
  with self.assertRaises(AssertionError):m.verify_compiler_pair(root,listing,log,name,sha,files)
 def test_duplicate_compiler_input_refuses(self):
  root,name,a,b,sha,listing,log,files=self.fixture()
  with self.assertRaises(AssertionError):m.verify_compiler_pair(root,listing+listing,log,name,sha,files)
 def test_missing_actual_compile_line_refuses(self):
  root,name,a,b,sha,listing,log,files=self.fixture()
  with self.assertRaises(AssertionError):m.verify_compiler_pair(root,listing,b"TEST BUILD SUCCEEDED",name,sha,files)
 def test_original_source_hash_cannot_be_replaced_by_new_matching_paths(self):
  root,name,a,b,sha,listing,log,files=self.fixture();a.write_bytes(b"changed source\n")
  with self.assertRaises(AssertionError):m.verify_compiler_pair(root,listing,log,name,sha,files)
 def test_original_inventory_binding_is_required(self):
  root,name,a,b,sha,listing,log,files=self.fixture();files[next(iter(files))]["sha256"]="0"*64
  with self.assertRaises(AssertionError):m.verify_compiler_pair(root,listing,log,name,sha,files)

if __name__=="__main__":unittest.main(verbosity=2)
