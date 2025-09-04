#!/usr/bin/env python3
"""
Run RetroPath2-wrapper with a validated standardization mode.

This script wraps a call to `retropath2_wrapper.retropath2`, letting you pass
paths and parameters from the command line, and enforcing constraints on the
standardization mode (`std_mode`).

Allowed `std_mode` options:
  * "H added + Kekulized"
  * "H added + Aromatized"

Disallowed (will raise an error):
  * "Aromatized (no Hs added)"
"""

from __future__ import annotations

import argparse
import sys
from typing import Dict, Optional

from retropath2_wrapper import retropath2
from retropath2_wrapper.knime import Knime

ALLOWED_STD_MODES = {
    "H added + Kekulized",
    "H added + Aromatized",
}
DISALLOWED_STD_MODE = "Aromatized (no Hs added)"


def validate_std_mode(std_mode: str) -> None:
    """Validate the standardization mode.

    Args:
        std_mode: The requested standardization mode.

    Raises:
        ValueError: If `std_mode` is not recognized or explicitly disallowed.
    """
    if std_mode == DISALLOWED_STD_MODE:
        raise ValueError(
            f"The std_mode {std_mode!r} is not permitted. "
            f"Allowed: {', '.join(sorted(ALLOWED_STD_MODES))}."
        )
    if std_mode not in ALLOWED_STD_MODES:
        allowed = ", ".join(sorted(ALLOWED_STD_MODES | {DISALLOWED_STD_MODE}))
        raise ValueError(f"Invalid std_mode {std_mode!r}. Options: {allowed}.")


def build_knime(kexec: str, kinstall: str, kver: str) -> Knime:
    """Construct a Knime object and patch its installer.

    Args:
        kexec: Path to the KNIME executable.
        kinstall: KNIME installation directory.
        kver: KNIME version string (e.g., "4.7.8").

    Returns:
        A configured `Knime` instance with its `install` method patched.
    """
    k = Knime(kexec=kexec, kinstall=kinstall, kver=kver)

    # Monkey-patch install method
    def dummy_install(logger) -> int:
        return 0

    k.install = dummy_install  # type: ignore[attr-defined]
    return k


def run_retropath(
    *,
    sink_file: str,
    source_file: str,
    rules_file: str,
    outdir: str,
    std_mode: str = "H added + Aromatized",
    max_steps: int = 6,
    topx: int = 1000,
    kexec: str = "/home/knime/knime/knime",
    kinstall: str = "/home/knime/knime/",
    kver: str = "4.7.8",
) -> int:
    """Run RetroPath2 with validated arguments.

    Args:
        sink_file: Path to sink CSV file.
        source_file: Path to source CSV file.
        rules_file: Path to rules CSV file.
        outdir: Output directory path.
        std_mode: Standardization mode (default: "H added + Aromatized").
        max_steps: Maximum number of steps (default: 6).
        topx: Top-X enumeration limit (default: 1000).
        kexec: Path to the KNIME executable (default: /home/knime/knime/knime).
        kinstall: KNIME installation directory (default: /home/knime/knime/).
        kver: KNIME version string (default: 4.7.8).

    Returns:
        The integer return code from `retropath2` (0 on success if it returns None).

    Raises:
        ValueError: If `std_mode` is invalid or disallowed.
        Exception: Propagates any runtime error from `retropath2`.
    """
    validate_std_mode(std_mode)

    std_params: Dict[str, str] = {"std_hydrogen": std_mode}
    k = build_knime(kexec=kexec, kinstall=kinstall, kver=kver)

    rc: Optional[int] = retropath2(
        sink_file=sink_file,
        source_file=source_file,
        rules_file=rules_file,
        outdir=outdir,
        max_steps=max_steps,
        topx=topx,
        kexec=kexec,
        kinstall=kinstall,
        kver=kver,
        knime=k,
        **std_params,
    )
    return 0 if rc is None else int(rc)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional list of CLI arguments; defaults to `sys.argv[1:]`.

    Returns:
        Parsed arguments namespace.
    """
    p = argparse.ArgumentParser(description="Run RetroPath2-wrapper with std_mode validation.")
    p.add_argument("--sink-file", required=True, help="Path to sink CSV file.")
    p.add_argument("--source-file", required=True, help="Path to source CSV file.")
    p.add_argument("--rules-file", required=True, help="Path to rules CSV file.")
    p.add_argument("--outdir", required=True, help="Output directory.")
    p.add_argument(
        "--std-mode",
        default="H added + Aromatized",
        help=(
            "Standardization mode (default: 'H added + Aromatized'). "
            f"Allowed: {', '.join(sorted(ALLOWED_STD_MODES))}. "
            f"Disallowed: {DISALLOWED_STD_MODE}."
        ),
    )
    p.add_argument("--max-steps", type=int, default=6, help="Maximum number of steps (default: 6).")
    p.add_argument("--topx", type=int, default=1000, help="Top-X enumeration limit (default: 1000).")
    p.add_argument("--kexec", default="/home/knime/knime/knime", help="Path to KNIME executable.")
    p.add_argument("--kinstall", default="/home/knime/knime/", help="KNIME installation directory.")
    p.add_argument("--kver", default="4.7.8", help="KNIME version string (default: 4.7.8).")
    return p.parse_args(argv)


def main(
    argv: list[str] | None = None,
    std_mode: str = "H added + Aromatized",
    max_steps: int = 6,
    topx: int = 1000,
    kexec: str = "/home/knime/knime/knime",
    kinstall: str = "/home/knime/knime/",
    kver: str = "4.7.8",
) -> int:
    """Entry point for the CLI.

    Args:
        argv: Optional list of CLI arguments; defaults to `sys.argv[1:]`.
        std_mode: Standardization mode (default: "H added + Aromatized").
        max_steps: Maximum number of steps (default: 6).
        topx: Top-X enumeration limit (default: 1000).
        kexec: Path to the KNIME executable (default: /home/knime/knime/knime).
        kinstall: KNIME installation directory (default: /home/knime/knime/).
        kver: KNIME version string (default: 4.7.8).

    Returns:
        Process exit code (0 on success).
    """
    args = parse_args(argv)
    try:
        return run_retropath(
            sink_file=args.sink_file,
            source_file=args.source_file,
            rules_file=args.rules_file,
            outdir=args.outdir,
            std_mode=args.std_mode or std_mode,
            max_steps=args.max_steps or max_steps,
            topx=args.topx or topx,
            kexec=args.kexec or kexec,
            kinstall=args.kinstall or kinstall,
            kver=args.kver or kver,
        )
    except Exception as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
