import asyncio
import shlex
from collections.abc import AsyncIterator


async def stream_command(cmd: str | list[str], *, use_sudo: bool = False) -> AsyncIterator[str]:
    args = shlex.split(cmd) if isinstance(cmd, str) else list(cmd)
    if use_sudo and args[0] != "sudo":
        args = ["sudo"] + args
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
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
    if use_sudo and args[0] != "sudo":
        args = ["sudo"] + args
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    return proc.returncode or 0, stdout.decode(errors="replace")
