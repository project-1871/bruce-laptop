import asyncio
import shlex
from collections.abc import AsyncIterator


def _sudo_args(args: list[str]) -> tuple[list[str], bytes | None]:
    from bruce.core.state import STATE
    pw = STATE.sudo_password
    if pw:
        return ["sudo", "-S"] + args, (pw + "\n").encode()
    return ["sudo"] + args, None


async def stream_command(cmd: str | list[str], *, use_sudo: bool = False) -> AsyncIterator[str]:
    args = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
    stdin_data: bytes | None = None
    if use_sudo and args[0] != "sudo":
        args, stdin_data = _sudo_args(args)
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE if stdin_data else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    if stdin_data and proc.stdin:
        proc.stdin.write(stdin_data)
        proc.stdin.close()
    assert proc.stdout is not None
    try:
        async for line in proc.stdout:
            yield line.decode(errors="replace").rstrip()
    finally:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()


async def run_command(cmd: str | list[str], *, use_sudo: bool = False) -> tuple[int, str]:
    args = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
    stdin_data: bytes | None = None
    if use_sudo and args[0] != "sudo":
        args, stdin_data = _sudo_args(args)
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE if stdin_data else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate(input=stdin_data)
    return proc.returncode or 0, stdout.decode(errors="replace")
