#!/usr/bin/env python3
"""Run the complete checked-in pytest suite."""

import subprocess
import sys
from typing import Optional, Sequence


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run every test below tests/ and return pytest's exit status."""
    extra_args = list(sys.argv[1:] if argv is None else argv)
    command = [sys.executable, "-m", "pytest", "tests", "-v", *extra_args]

    print("=== Running complete test suite via pytest ===", flush=True)
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
