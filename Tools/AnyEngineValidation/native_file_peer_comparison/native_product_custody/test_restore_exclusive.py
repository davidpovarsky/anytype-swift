"""Disposable filesystem controls; never call the real product restore main."""
from pathlib import Path
import hashlib
import importlib.util
import os
import tempfile
import threading
import unittest

spec=importlib.util.spec_from_file_location('native_restore',Path(__file__).with_name('restore.py'))
restore=importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


class ExclusiveRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='pinkha-exclusive-restore-disposable-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def write(self,name,data,mode=0o700):
        path=self.root/name
        with path.open('xb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.chmod(path,mode)
        os.utime(path,ns=(1600000000123456789,1600000000987654321))
        return path

    def identity(self,path):
        st=path.stat()
        return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':st.st_size,
                'mode':st.st_mode & 0o7777,'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns}

    def test_installs_exact_bytes_metadata_and_retires_only_temporary_link(self):
        tmp=self.write('candidate',b'only a disposable synthetic fixture'*17,0o750)
        before=self.identity(tmp)
        dst=self.root/'installed'
        restore.install_exclusively(tmp,dst)
        self.assertEqual(before,self.identity(dst))
        self.assertFalse(tmp.exists())
        self.assertEqual(1,dst.stat().st_nlink)

    def test_existing_destination_is_never_replaced(self):
        tmp=self.write('candidate',b'candidate bytes')
        dst=self.write('installed',b'preexisting destination bytes',0o640)
        before_tmp,before_dst=self.identity(tmp),self.identity(dst)
        with self.assertRaises(FileExistsError):restore.install_exclusively(tmp,dst)
        self.assertEqual(before_tmp,self.identity(tmp))
        self.assertEqual(before_dst,self.identity(dst))

    def test_existing_dangling_symlink_is_never_replaced(self):
        tmp=self.write('candidate',b'candidate bytes')
        dst=self.root/'installed';dst.symlink_to('absent-original-target')
        before=self.identity(tmp)
        with self.assertRaises(FileExistsError):restore.install_exclusively(tmp,dst)
        self.assertTrue(dst.is_symlink())
        self.assertEqual('absent-original-target',os.readlink(dst))
        self.assertEqual(before,self.identity(tmp))
        self.assertFalse((self.root/'absent-original-target').exists())

    def test_concurrent_install_has_one_winner_without_overwrite(self):
        candidates=[self.write('candidate-a',b'A'*1021,0o700),self.write('candidate-b',b'B'*1023,0o750)]
        before=[self.identity(path) for path in candidates]
        destination=self.root/'contended-destination'
        barrier=threading.Barrier(2)
        outcomes=[]
        lock=threading.Lock()
        def install(index):
            try:
                barrier.wait(timeout=5)
                restore.install_exclusively(candidates[index],destination)
                outcome=(index,'installed')
            except FileExistsError:
                outcome=(index,'already-exists')
            except BaseException as error:
                outcome=(index,'unexpected:'+repr(error))
            with lock:outcomes.append(outcome)
        workers=[threading.Thread(target=install,args=(index,),daemon=True) for index in (0,1)]
        for worker in workers:worker.start()
        for worker in workers:worker.join(timeout=10)
        self.assertTrue(all(not worker.is_alive() for worker in workers))
        self.assertEqual(['already-exists','installed'],sorted(value for _,value in outcomes))
        winner=next(index for index,value in outcomes if value=='installed');loser=1-winner
        self.assertEqual(before[winner],self.identity(destination))
        self.assertFalse(candidates[winner].exists())
        self.assertEqual(before[loser],self.identity(candidates[loser]))
        self.assertEqual(1,destination.stat().st_nlink)


if __name__ == '__main__':
    unittest.main(verbosity=2)
