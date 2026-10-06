import atexit
import os
import signal
import subprocess
import threading
import time
from pathlib import Path


_shell_processes: set[subprocess.Popen] = set()
_shell_process_lock = threading.RLock()


def _stop_process_group(process: subprocess.Popen) -> None:
    """Stop a shell process and its children without affecting other tasks."""
    if process.poll() is not None:
        return

    if os.name == "nt":
        for stop in (process.terminate, process.kill):
            if process.poll() is not None:
                return
            try:
                stop()
            except OSError:
                return
            try:
                process.wait(timeout=0.05)
            except subprocess.TimeoutExpired:
                continue
        return

    for sig in (signal.SIGTERM, getattr(signal, "SIGKILL", signal.SIGTERM)):
        try:
            os.killpg(process.pid, sig)
        except (ProcessLookupError, OSError):
            return
        time.sleep(0.05)
        if process.poll() is not None:
            return


def _stop_all_shell_processes() -> None:
    with _shell_process_lock:
        processes = list(_shell_processes)
    for process in processes:
        _stop_process_group(process)


def _handle_termination_signal(signum, _frame) -> None:
    _stop_all_shell_processes()
    raise SystemExit(128 + signum)


def _run_bash_process(command: str, timeout: float = 120) -> tuple[str, int | None]:
    process = None
    try:
        popen_kwargs = {} if os.name == "nt" else {"start_new_session": True}
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=Path.cwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            **popen_kwargs,
        )
        with _shell_process_lock:
            _shell_processes.add(process)
        stdout, stderr = process.communicate(timeout=timeout)
        output = (stdout + stderr).strip() or "(no output)"
        return output[:50000], process.returncode
    except subprocess.TimeoutExpired:
        return f"Error: Timeout ({timeout:g}s)", None
    except OSError as error:
        return f"Error: {type(error).__name__}: {error}", None
    finally:
        if process is not None:
            _stop_process_group(process)
            try:
                process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                pass
            with _shell_process_lock:
                _shell_processes.discard(process)


atexit.register(_stop_all_shell_processes)
if threading.current_thread() is threading.main_thread():
    signal.signal(signal.SIGTERM, _handle_termination_signal)


class BackgroundManager:
    def __init__(self):
        self.tasks: dict[str, dict] = {}
        self.results: dict[str, str] = {}
        self._ready: list[str] = []
        self._counter = 0
        self._lock = threading.Lock()

    def start(self, command: str) -> str:
        if not isinstance(command, str) or not command.strip():
            raise ValueError("Bash command cannot be empty")

        with self._lock:
            self._counter += 1
            task_id = f"bg_{self._counter:04d}"
            self.tasks[task_id] = {
                "command": command,
                "status": "running",
                "exit_code": None,
            }
        thread = threading.Thread(
            target=self._run,
            args=(task_id, command),
            daemon=True,
        )
        try:
            thread.start()
        except Exception:
            with self._lock:
                self.tasks.pop(task_id, None)
            raise

        return task_id

    def _record_completion(
            self,
            task_id: str,
            result: str,
            status: str,
            exit_code: int | None,
    ) -> None:
        with self._lock:
            task = self.tasks.get(task_id)
            if task is None:
                return
            task["exit_code"] = exit_code
            task["status"] = status
            self.results[task_id] = result
            self._ready.append(task_id)

    def collect(self) -> list[dict]:
        with self._lock:
            completed = []
            for task_id in self._ready:
                task = self.tasks.pop(task_id, None)
                result = self.results.pop(task_id, None)
                if task is not None:
                    completed.append({
                        "id": task_id,
                        "command": task["command"],
                        "status": task["status"],
                        "result": result,
                        "exit_code": task["exit_code"],
                    })

            self._ready.clear()
            return completed

    def has_ready(self) -> bool:
        with self._lock:
            return bool(self._ready)

    def has_running(self) -> bool:
        with self._lock:
            return any(task["status"] == "running" for task in self.tasks.values())

    def _run(self, task_id: str, command: str) -> None:
        try:
            output, exit_code = _run_bash_process(command)
            status = "completed" if exit_code == 0 else "failed"

            if status == "failed":
                if exit_code is not None:
                    output = f"Error: command exited with status {exit_code}\n{output}"

            self._record_completion(task_id, output, status, exit_code)
        except Exception as error:
            self._record_completion(
                task_id,
                f"Error: {type(error).__name__}: {error}",
                "failed",
                None,
            )

BACKGROUND = BackgroundManager()
