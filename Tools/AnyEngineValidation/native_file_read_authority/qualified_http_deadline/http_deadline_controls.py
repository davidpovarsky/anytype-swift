#!/usr/bin/env python3
"""Two fresh loopback controls for the complete-GET deadline, SOURCE ONLY.

Run only in a separately reviewed qualified owned-command invocation. This
process creates no native account and reads no retained private material.
"""
import argparse
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import sys
import threading
import time
import unittest

sys.dont_write_bytecode = True
PARENT = Path('/mnt/development/projects/evidence/pinkha-current-authority-http-controls-20261127')


def source_bytes(path):
    assert path.is_absolute() and path.resolve()==path and not path.is_symlink()
    before = path.lstat()
    assert stat.S_ISREG(before.st_mode) and before.st_size<=128*1024
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    with os.fdopen(fd, 'rb') as stream:
        assert os.fstat(stream.fileno())==before
        data = stream.read(128*1024+1)
        assert os.fstat(stream.fileno())==before
    assert path.lstat()==before and len(data)==before.st_size
    return data


class SlowPeer:
    """One bounded, disposable loopback peer; its thread never starts a child."""
    def __init__(self, phase):
        self.phase = phase
        self.stop = threading.Event()
        self.done = threading.Event()
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen(1)
        self.listener.settimeout(.05)
        self.port = self.listener.getsockname()[1]
        self.accepted = None
        self.errors = []
        self.drips = 0
        self.headerSent = False
        self.thread = threading.Thread(target=self.serve, name='fresh-deadline-'+phase, daemon=False)

    def start(self):
        self.thread.start()

    def serve(self):
        try:
            while not self.stop.is_set():
                try:
                    peer, _ = self.listener.accept()
                    break
                except socket.timeout:
                    continue
            else:
                return
            self.accepted = peer
            peer.settimeout(.1)
            request = bytearray()
            deadline = time.monotonic()+1
            while b'\r\n\r\n' not in request:
                assert time.monotonic()<deadline and len(request)<4096
                part = peer.recv(1024)
                assert part
                request.extend(part)
            assert request.startswith(b'GET /fresh-deadline HTTP/1.1\r\n')
            if self.phase=='header':
                peer.sendall(b'HTTP/1.1 200 OK\r\nX-Slow: ')
            else:
                peer.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 4096\r\nConnection: close\r\n\r\n')
                self.headerSent = True
            deadline = time.monotonic()+2
            while not self.stop.wait(.03):
                assert time.monotonic()<deadline, 'fresh peer exceeded its own two-second bound'
                peer.sendall(b'x')
                self.drips += 1
        except (BrokenPipeError, ConnectionResetError, OSError) as error:
            # Connection close is the expected consequence of deadline refusal.
            if not self.stop.is_set() and not isinstance(error, (BrokenPipeError, ConnectionResetError)):
                self.errors.append(type(error).__name__+': '+str(error))
        except BaseException as error:
            self.errors.append(type(error).__name__+': '+str(error))
        finally:
            if self.accepted is not None:
                self.accepted.close()
            self.done.set()

    def close(self):
        self.stop.set()
        if self.accepted is not None:
            try:
                self.accepted.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.listener.close()
        if self.thread.ident is not None:
            self.thread.join(2)
        return not self.thread.is_alive()


def main():
    if sys.flags.optimize:
        raise RuntimeError('assertions must remain enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controller', type=Path, required=True)
    parser.add_argument('--controller-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'[0-9a-f]{64}', args.controller_sha256)
    assert args.output.parent.parent==PARENT and re.fullmatch(r'attempt[1-9][0-9]{0,2}', args.output.parent.name)
    assert args.output.name=='controls' and args.output.parent.resolve()==args.output.parent
    assert PARENT.is_dir() and PARENT.resolve()==PARENT and not PARENT.is_symlink()
    controller = source_bytes(args.controller)
    assert hashlib.sha256(controller).hexdigest()==args.controller_sha256
    os.umask(0o077)
    args.output.mkdir(mode=0o700, exist_ok=False)
    receipt = args.output/'result.json'
    with receipt.open('xb') as stream:
        stream.write(b'{}\n'); stream.flush(); os.fsync(stream.fileno())
    result = {'status': 'RUNNING', 'controllerSHA256': args.controller_sha256,
              'nativeProcesses': 0, 'accountInputs': 0, 'compilerInvocations': 0,
              'controls': [], 'errors': [], 'callerOwnedGroupRequired': True}
    began = time.monotonic()

    def interrupted(number, _frame):
        raise RuntimeError('deadline control interrupted by signal '+str(number))
    for number in (signal.SIGTERM, signal.SIGINT):
        signal.signal(number, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})

    try:
        specification = importlib.util.spec_from_file_location('current_authority_source_under_test', args.controller)
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)

        class DeadlineControls(unittest.TestCase):
            def exercise(self, phase):
                row = {'name': 'slow-'+phase, 'status': 'RUNNING'}
                result['controls'].append(row)
                peer = SlowPeer(phase)
                connection = None
                response = None
                old_handler = signal.getsignal(signal.SIGALRM)
                original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
                expected_mask = original_mask|{signal.SIGALRM}
                restored = False
                try:
                    self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
                    self.assertNotIn(signal.SIGALRM, signal.sigpending())
                    def previous_alarm(_number, _frame):
                        raise AssertionError('the previous SIGALRM handler must not be invoked')
                    signal.signal(signal.SIGALRM, previous_alarm)
                    peer.start()
                    start = time.monotonic()
                    with self.assertRaisesRegex(TimeoutError, '^absolute HTTP request deadline$'):
                        with module.absolute_http_deadline(.35):
                            connection = http.client.HTTPConnection('127.0.0.1', peer.port, timeout=.1)
                            try:
                                connection.request('GET', '/fresh-deadline', headers={'Connection': 'close'})
                                response = connection.getresponse()
                                if phase=='header':
                                    self.fail('slow header unexpectedly completed')
                                self.assertEqual(response.status, 200)
                                response.read(4097)
                                self.fail('slow body unexpectedly completed')
                            finally:
                                if response is not None:
                                    response.close()
                                if connection is not None:
                                    connection.close()
                    elapsed = time.monotonic()-start
                    self.assertGreaterEqual(elapsed, .2)
                    self.assertLess(elapsed, 1.2)
                    self.assertIs(signal.getsignal(signal.SIGALRM), previous_alarm)
                    self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
                    self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK, set()), expected_mask)
                    self.assertNotIn(signal.SIGALRM, signal.sigpending())
                    restored = True
                    row.update(seconds=elapsed, expectedAbsoluteSeconds=.35, socketOperationTimeoutSeconds=.1,
                               previousHandlerRestored=True, previousMaskRestored=True, ownedTimerCleared=True,
                               deliberatelyPreblockedAlarmWasUnblocked=True, pendingAlarmAfter=False)
                finally:
                    # No controller child process is created. The externally
                    # qualified owner retains this process until its whole
                    # group ends, including any failure of the thread bound.
                    signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    if signal.SIGALRM in signal.sigpending():
                        signal.sigtimedwait({signal.SIGALRM}, 0)
                    signal.signal(signal.SIGALRM, old_handler)
                    signal.pthread_sigmask(signal.SIG_SETMASK, original_mask)
                    row['threadJoined'] = peer.close()
                    row['successfulDripWrites'] = peer.drips
                    row['peerErrors'] = peer.errors
                    row['status'] = 'PASS' if restored and row['threadJoined'] and not peer.errors and peer.drips>=3 and peer.headerSent==(phase=='body') else 'FAIL'
                self.assertTrue(row['threadJoined'])
                self.assertEqual(peer.errors, [])
                self.assertGreaterEqual(peer.drips, 3, 'regular socket activity must outlive the per-operation timeout')
                self.assertEqual(peer.headerSent, phase=='body')
                self.assertEqual(row['status'], 'PASS')

            def testSlowHeaderHasAbsoluteDeadlineAndRestoresSignalState(self):
                self.exercise('header')

            def testSlowBodyHasAbsoluteDeadlineAndRestoresSignalState(self):
                self.exercise('body')

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(DeadlineControls)
        execution = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
        result['actualMethods'] = {'runs': execution.testsRun, 'failures': len(execution.failures),
                                  'errors': len(execution.errors), 'skips': len(execution.skipped)}
        assert execution.testsRun==2 and execution.wasSuccessful()
        assert not execution.skipped and not execution.expectedFailures and not execution.unexpectedSuccesses
        assert len(result['controls'])==2 and {r['name'] for r in result['controls']}=={'slow-header', 'slow-body'}
        assert all(r['status']=='PASS' for r in result['controls'])
        result['status'] = 'PASS_TWO_FRESH_ABSOLUTE_HTTP_DEADLINE_CONTROLS'
    except BaseException as error:
        result['status'] = 'FAIL_HTTP_DEADLINE_CONTROLS'
        result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    finally:
        for number in (signal.SIGTERM, signal.SIGINT):
            signal.signal(number, signal.SIG_IGN)
        try:
            assert source_bytes(args.controller)==controller
            result['sourceUnchanged'] = True
        except BaseException as error:
            result['status'] = 'FAIL_HTTP_DEADLINE_CONTROLS'
            result['errors'].append({'phase': 'source-finalization', 'type': type(error).__name__, 'message': str(error)})
        result['seconds'] = time.monotonic()-began
        temporary = receipt.with_name('result.final.json')
        with temporary.open('x') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, receipt)
        directory = os.open(args.output, os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    print(json.dumps({'status': result['status'], 'result': str(receipt)}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
