from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CommandResult:
    command: str
    stdout: str
    stderr: str
    returncode: int


class CommandRunner:
    """Runs shell commands and PowerShell scripts without mutating the system."""

    def run(self, args: list[str], timeout: int = 30) -> CommandResult:
        command_text = " ".join(args)
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
            return CommandResult(
                command=command_text,
                stdout=completed.stdout,
                stderr=completed.stderr,
                returncode=completed.returncode,
            )
        except FileNotFoundError as error:
            return CommandResult(command=command_text, stdout="", stderr=str(error), returncode=127)
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout if isinstance(error.stdout, str) else ""
            stderr = error.stderr if isinstance(error.stderr, str) else ""
            return CommandResult(command=command_text, stdout=stdout, stderr=stderr or "Command timed out", returncode=124)

    def run_powershell(self, script: str, timeout: int = 30) -> CommandResult:
        for executable in ("pwsh", "powershell"):
            result = self.run([executable, "-NoLogo", "-NoProfile", "-Command", script], timeout=timeout)
            if result.returncode != 127:
                return result
        return CommandResult(
            command="pwsh/powershell -NoLogo -NoProfile -Command ...",
            stdout="",
            stderr="PowerShell executable was not found.",
            returncode=127,
        )

    def run_powershell_json(self, script: str, timeout: int = 30) -> tuple[CommandResult, Any | None]:
        result = self.run_powershell(script, timeout=timeout)
        if not result.stdout.strip():
            return result, None
        try:
            return result, json.loads(result.stdout)
        except json.JSONDecodeError:
            return result, None
