"""Application restart helpers shared by the Qt entry points."""

import subprocess
import sys
from pathlib import Path


def build_restart_command(executable=None, argv=None, frozen=None):
    """Return the command needed to start a replacement app instance."""
    actual_executable = executable or sys.executable
    actual_argv = list(sys.argv if argv is None else argv)
    is_frozen = getattr(sys, "frozen", False) if frozen is None else bool(frozen)

    if is_frozen:
        return [actual_executable, *actual_argv[1:]]
    if actual_argv:
        return [actual_executable, *actual_argv]
    return [actual_executable]


def start_replacement_process():
    """Launch a new copy of the current application without waiting for it."""
    return subprocess.Popen(
        build_restart_command(),
        cwd=str(Path.cwd()),
        close_fds=True,
    )
