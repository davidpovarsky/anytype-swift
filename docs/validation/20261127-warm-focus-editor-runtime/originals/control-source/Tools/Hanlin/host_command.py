"""SDK-only command execution with durable logs and owned POSIX cancellation."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
import signal
import subprocess


class CommandCancelled(KeyboardInterrupt):
    def __init__(self, signum):
        self.signum = signum
        super().__init__("Received " + signal.Signals(signum).name)


@contextmanager
def cancellation_signals():
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}

    def cancel(signum, frame):
        # Finish bounded owned-child cleanup before GitHub's subsequent signal.
        for sig in previous:
            signal.signal(sig, signal.SIG_IGN)
        raise CommandCancelled(signum)

    try:
        for sig in previous:
            signal.signal(sig, cancel)
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def stop_owned_group(process):
    """Only this Popen's new session/group; never discover or kill other jobs."""
    result = dict(pgid=process.pid, term_sent=False, kill_sent=False, child_reaped=False)
    for sig, field in ((signal.SIGTERM, "term_sent"), (signal.SIGKILL, "kill_sent")):
        try:
            os.killpg(process.pid, sig)
            result[field] = True
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=2 if sig == signal.SIGTERM else 1)
        except subprocess.TimeoutExpired:
            if sig == signal.SIGKILL:
                raise
    result["child_reaped"] = process.poll() is not None
    return result


def command(argv, cwd, logdir, env=None):
    if os.name != "posix":
        raise RuntimeError("SDK commands require an owned POSIX process group")
    index = len(list(logdir.glob("command-*.log")))
    log = logdir / ("command-%02d.log" % index)
    receipt_path = log.with_suffix(".json")
    receipt = dict(command=[str(value) for value in argv], cwd=str(cwd), log=str(log),
                   status="STARTING", started_at=datetime.now(timezone.utc).isoformat(), exit_code=None)

    def save():
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    save()
    print(json.dumps(dict(command=argv, log=str(log))), flush=True)
    process = None
    with log.open("x", encoding="utf-8", buffering=1) as stream:
        try:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                       errors="replace", bufsize=1, start_new_session=True)
            receipt.update(status="RUNNING", pid=process.pid, pgid=process.pid)
            save()
            for number, line in enumerate(process.stdout):
                stream.write(line)
                stream.flush()
                if number % 250 == 0 or "error:" in line.lower():
                    print(line.rstrip(), flush=True)
            returncode = process.wait()
            if returncode:
                raise subprocess.CalledProcessError(returncode, argv)
            receipt["status"] = "SUCCEEDED"
        except BaseException as error:
            receipt.update(status="CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAILED",
                           error_type=type(error).__name__, error=str(error))
            if isinstance(error, CommandCancelled):
                receipt["signal"] = error.signum
            if process is not None:
                try:
                    receipt["owned_group_cleanup"] = stop_owned_group(process)
                    remaining, _ = process.communicate(timeout=1)
                    if remaining:
                        stream.write(remaining)
                        stream.flush()
                except Exception as cleanup_error:
                    receipt["owned_group_cleanup_error"] = str(cleanup_error)
            raise
        finally:
            if process is not None:
                receipt["exit_code"] = process.poll()
                process.stdout.close()
            receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
            save()
