"""Isolated code-check runner.

Runs ONLY on a dedicated, separate Docker host (SANDBOX_DOCKER_HOST) — never the production
host's Docker socket. Each run is a disposable container with:
  no network, read-only root FS, non-root user, CPU/memory/PID limits, tmpfs scratch with a
  size cap, all capabilities dropped, no-new-privileges, and a hard wall-clock timeout.
Files are passed in via stdin as a tar stream; nothing from the platform is mounted.

Disabled by default. When disabled, the validator records the check as SKIPPED.
"""

from __future__ import annotations

import io
import subprocess
import tarfile

from app.core.config import settings

CHECK_SCRIPT = (
    "set -e; mkdir -p /tmp/w && cd /tmp/w && tar -x -f - && "
    "python -I -c \"import sys,pathlib,py_compile;"
    "fs=[str(p) for p in pathlib.Path('.').rglob('*.py')];"
    "[py_compile.compile(f, doraise=True) for f in fs];print('compiled', len(fs))\""
)


def enabled() -> bool:
    return settings.SANDBOX_ENABLED and bool(settings.SANDBOX_DOCKER_HOST)


def _tar(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def run_python_compile_check(files: dict[str, str]) -> dict:
    if not enabled():
        return {"status": "SKIPPED", "reason": "Sandbox not configured"}
    cmd = [
        "docker", "--host", settings.SANDBOX_DOCKER_HOST, "run", "--rm", "-i",
        "--network", "none", "--read-only", "--user", "65534:65534",
        "--memory", settings.SANDBOX_MEMORY, "--memory-swap", settings.SANDBOX_MEMORY, "--cpus", settings.SANDBOX_CPUS,
        "--pids-limit", "64", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--tmpfs", "/tmp:rw,size=64m,noexec,nosuid", "--stop-timeout", "1",
        settings.SANDBOX_IMAGE, "sh", "-c", CHECK_SCRIPT,
    ]
    try:
        proc = subprocess.run(cmd, input=_tar(files), capture_output=True, timeout=settings.SANDBOX_TIMEOUT_SECONDS, check=False)  # noqa: S603
    except subprocess.TimeoutExpired:
        return {"status": "FAILED", "reason": "Sandbox timeout"}
    except FileNotFoundError:
        return {"status": "ERROR", "reason": "docker CLI not available on worker"}
    return {
        "status": "PASSED" if proc.returncode == 0 else "FAILED",
        "exit_code": proc.returncode,
        "stdout": proc.stdout.decode(errors="replace")[-2000:],
        "stderr": proc.stderr.decode(errors="replace")[-2000:],
    }
