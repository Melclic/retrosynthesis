#!/usr/bin/env python3
"""
Run RetroPath2-wrapper with validated standardization mode, temporary file handling,
and post-processing with rp2paths.

Features:
  * Accepts a source InChI string instead of a CSV.
  * Writes the source InChI to a temporary CSV file (name = "target").
  * Generates the rules file with rrparser into a temporary file.
  * Runs RetroPath2 with the generated files into a temporary output folder.
  * Runs rp2paths on the RetroPath2 output and writes out_paths.csv.
  * Final out_paths.csv can be saved to a user-provided path.
"""

from __future__ import annotations

import argparse
import csv
import os
import pandas as pd
import shutil
import subprocess
import sys
import tempfile
import glob
from typing import Optional
import resource  # may not be available on all systems
from pathlib import Path

from rrparser import parse_rules
#from retropath2_wrapper import retropath2
#from retropath2_wrapper.knime import Knime

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
)

# -----------------------------
# Constants / defaults
# -----------------------------

ALLOWED_STD_MODES = {
    "H added + Kekulized",
    "H added + Aromatized",
}
DISALLOWED_STD_MODE = "Aromatized (no Hs added)"

DEFAULT_RULES_OUTPUT_FORMAT = "csv"    # 'csv' | 'tsv'
DEFAULT_RULES_TYPE = "all"           # 'all' | 'retro' | 'forward'
DEFAULT_DIAMETERS = "2,4,6,8,10,12,14,16"

DEFAULT_STD_MODE = "H added + Kekulized"
DEFAULT_MAX_STEPS = 6
DEFAULT_TOPX = 1000
DEFAULT_DMIN = 0
DEFAULT_DMAX = 1000
DEFAULT_MWMAX_SOURCE = 1000
DEFAULT_MWMAX_COF = 1000
DEFAULT_RP2_TIMEOUT = 60
DEFAULT_RP2_RAM_LIMIT = 30
DEFAULT_PARTIAL_RETRO = False

DEFAULT_KEXEC = "/home/knime/knime/knime"
DEFAULT_KINSTALL = "/home/knime/knime/"
DEFAULT_KVER = "4.7.8"
DEFAULT_RP2_WORKFLOW = "/home/rp2/RetroPath2.0.knwf"

# --- Status codes ---
STATUS_OK = 0
STATUS_TIMEOUT_ERROR = 10
STATUS_MEM_ERROR = 20
STATUS_SOURCE_IN_SINK_ERROR = 30
STATUS_SOURCE_IN_SINK_NOT_FOUND = 31
STATUS_NO_RESULT_ERROR = 40
STATUS_OS_ERROR = 50
STATUS_RAM_ERROR = 60

MAX_VIRTUAL_MEMORY = 30000 * 1024 * 1024  # default 30 GB

# -----------------------------
# Validation / helpers
# -----------------------------

def validate_diameters(diameters: str) -> str:
    """Validate and normalize diameters input.

    Ensures the input is a comma-separated string of integers chosen from
    {2,4,6,8,10,12,14,16}, with optional whitespace. Returns a sorted list.

    Args:
        diameters (str): Comma-separated diameters string, e.g. "2, 4,6".

    Returns:
        List[int]: A sorted list of validated diameters.

    Raises:
        ValueError: If any value is not in the allowed set.

    Example:
        >>> validate_diameters("2, 4, 6")
        [2, 4, 6]
        >>> validate_diameters("2,9")
        ValueError: Invalid diameter(s) found: [9]. Allowed: [2, 4, 6, 8, 10, 12, 14, 16].
    """
    allowed = {2, 4, 6, 8, 10, 12, 14, 16}
    # Remove whitespace and split
    parts = [p.strip() for p in diameters.split(",") if p.strip()]
    try:
        values = [int(p) for p in parts]
    except ValueError:
        raise ValueError(f"Diameters must be integers, got: {parts}")

    invalid = [v for v in values if v not in allowed]
    if invalid:
        raise ValueError(
            f"Invalid diameter(s) found: {invalid}. Allowed: {sorted(allowed)}."
        )
    return ",".join(str(v) for v in sorted(values))

def validate_std_mode(std_mode: str) -> None:
    """Validate the standardization mode."""
    if std_mode == DISALLOWED_STD_MODE:
        raise ValueError(
            f"The std_mode {std_mode!r} is not permitted. "
            f"Allowed: {', '.join(sorted(ALLOWED_STD_MODES))}."
        )
    if std_mode not in ALLOWED_STD_MODES:
        allowed = ", ".join(sorted(ALLOWED_STD_MODES | {DISALLOWED_STD_MODE}))
        raise ValueError(f"Invalid std_mode {std_mode!r}. Options: {allowed}.")

'''
def build_knime(kexec: str, kinstall: str, kver: str, rp2_workflow_file: str = DEFAULT_RP2_WORKFLOW) -> Knime:
    """Construct a Knime object and patch its installer."""
    k = Knime(kexec=kexec, kinstall=kinstall, kver=kver, workflow=rp2_workflow_file)

    def dummy_install(logger) -> int:
        return 0

    k.install = dummy_install  # type: ignore[attr-defined]
    return k
'''


def generate_source_file_from_inchi(outfile: str, source_inchi: str) -> None:
    """Write a source InChI into a CSV file with the compound name 'target'.

    Args:
        outfile (str): Path to the output CSV file.
        source_inchi (str): InChI string of the source compound.

    Returns:
        None

    Example:
        >>> generate_source_file_from_inchi("source.csv", "InChI=1S/C2H6/c1-2/h1-2H3")
        # Creates a CSV file like:
        # name,inchi
        # target,InChI=1S/C2H6/c1-2/h1-2H3
    """
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(["Name", "InChI"])
        writer.writerow(["target", source_inchi.replace(" ", "")])

def run_rp2paths(target_scope_file: str, outdir: str):
    """Run rp2paths on target_scope.csv and return path to out_paths.csv."""
    subprocess.run(
        [
            sys.executable, "-m", "rp2paths", "all",
            str(target_scope_file),
            "--outdir", str(outdir),
        ],
        check=True,
    )

def limit_virtual_memory() -> None:
    """Limit virtual memory of the subprocess (best-effort)."""
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MAX_VIRTUAL_MEMORY, resource.RLIM_INFINITY))
    except (ValueError, OSError) as e:
        logging.warning(f"Could not apply RLIMIT_AS: {e}")


def _count_csv_rows(path: str) -> int:
    """Return number of rows in a CSV file."""
    count = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=",", quotechar='"')
        for _ in reader:
            count += 1
    return count


def run_rp2(
    sink_file: str,
    rules_file: str,
    source_file: str,
    scope_results: str,
    max_steps: int = DEFAULT_MAX_STEPS,
    std_mode: str = DEFAULT_STD_MODE,
    topx: int = DEFAULT_TOPX,
    dmin: int = DEFAULT_DMIN,
    dmax: int = DEFAULT_DMAX,
    mwmax_source: int = DEFAULT_MWMAX_SOURCE,
    mwmax_cof: int = DEFAULT_MWMAX_COF,
    timeout: int = DEFAULT_RP2_TIMEOUT,
    ram_limit: Optional[int] = DEFAULT_RP2_RAM_LIMIT,
    partial_retro: bool = DEFAULT_PARTIAL_RETRO,
) -> int:
    """Run KNIME RetroPath2.0 and write scope/results to `scope_results`.

    Returns:
        int: One of STATUS_* codes.
    """

    logging.debug(f'partial_retro: {partial_retro}')
    global MAX_VIRTUAL_MEMORY
    if ram_limit is not None:
        MAX_VIRTUAL_MEMORY = ram_limit * 1000 * 1024 * 1024  # GB → bytes (approx)

    is_time_out = False

    with tempfile.TemporaryDirectory() as tmp_output_folder:

        results_path = os.path.join(tmp_output_folder, "results.csv")
        source_in_sink_path = os.path.join(tmp_output_folder, "source-in-sink.csv")

        cmd = [
            DEFAULT_KEXEC,
            "-nosplash",
            "-nosave",
            "-reset",
            "--launcher.suppressErrors",
            "-application",
            "org.knime.product.KNIME_BATCH_APPLICATION",
            f"-workflowFile={DEFAULT_RP2_WORKFLOW}", 
            f'-workflow.variable=input.dmin,"{dmin}",int',
            f'-workflow.variable=input.dmax,"{dmax}",int',
            f'-workflow.variable=input.max-steps,"{max_steps}",int',
            f'-workflow.variable=input.sourcefile,"{source_file}",String',
            f'-workflow.variable=input.sinkfile,"{sink_file}",String',
            f'-workflow.variable=input.rulesfile,"{rules_file}",String',
            f'-workflow.variable=input.topx,"{topx}",int',
            f'-workflow.variable=input.mwmax-source,"{mwmax_source}",int',
            f'-workflow.variable=input.mwmax-cof,"{mwmax_cof}",int',
            f'-workflow.variable=input.std_mode,"{std_mode}",String',
            f'-workflow.variable=output.dir,"{tmp_output_folder}",String',
            f'-workflow.variable=output.solutionfile,"results.csv",String',
            f'-workflow.variable=output.sourceinsinkfile,"source-in-sink.csv",String',
        ]

        try:
            logging.debug('Running the following command: ')
            logging.debug(' '.join(cmd))
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=limit_virtual_memory,
                text=True,
            )
            try:
                stdout_text, _ = proc.communicate(timeout=timeout * 60.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                logging.warning('RetroPath2 timed out')
                is_time_out = True
                stdout_text, _ = proc.communicate()
                
            logging.debug(f'Output RP2: {glob.glob(os.path.join(tmp_output_folder, "*"))}')
            is_results_empty = True
            try:
                count = _count_csv_rows(results_path)
                if count > 1:
                    is_results_empty = False
            except (IndexError, FileNotFoundError):
                pass

            try:
                count = _count_csv_rows(str(source_in_sink_path))
                if count > 1:
                    return STATUS_SOURCE_IN_SINK_ERROR
            except FileNotFoundError:
                return STATUS_SOURCE_IN_SINK_NOT_FOUND

            if is_time_out:
                if is_results_empty:
                    return STATUS_TIMEOUT_ERROR
                else:
                    if not partial_retro:
                        return STATUS_TIMEOUT_ERROR

            if "There is insufficient memory for the Java Runtime Environment to continue" in stdout_text:
                logging.warning('RetroPath2 ran out of memory')
                if is_results_empty:
                    return STATUS_MEM_ERROR
                else:
                    if not partial_retro:
                        return STATUS_MEM_ERROR

            logging.debug(f'is_results_empty: {is_results_empty}')
            logging.debug(f'is_time_out: {is_time_out}')
            csv_scope = glob.glob(os.path.join(tmp_output_folder, "*_scope.csv"))
            logging.debug(f'csv_scope: {csv_scope}')
            if csv_scope:
                logging.debug(f'Copying to {scope_results}')
                shutil.copyfile(csv_scope[0], scope_results)
                return STATUS_OK
            elif not is_results_empty and partial_retro:
                logging.debug('Using partial results')
                logging.debug(f'Copying to scope_results')
                shutil.copyfile(results_path, scope_results)
                return STATUS_OK

            return STATUS_NO_RESULT_ERROR

        except OSError:
            return STATUS_OS_ERROR
        except ValueError:
            return STATUS_RAM_ERROR



# -----------------------------
# Runner
# -----------------------------

def run_pipeline(
    *,
    sink_file: str,
    source_inchi: str,
    out_scope: str,
    out_paths: str,
    out_compounds: str,
    rules_file: Optional[str] = None,
    # rules-generation params
    diameters: str = DEFAULT_DIAMETERS,
    rule_type: str = DEFAULT_RULES_TYPE,
    # rp2 params
    max_steps: int = DEFAULT_MAX_STEPS,
    std_mode: str = DEFAULT_STD_MODE,
    topx: int = DEFAULT_TOPX,
    dmin: int = DEFAULT_DMIN,
    dmax: int = DEFAULT_DMAX,
    mwmax_source: int = DEFAULT_MWMAX_SOURCE,
    mwmax_cof: int = DEFAULT_MWMAX_COF,
    timeout: int = DEFAULT_RP2_TIMEOUT,
    ram_limit: Optional[int] = DEFAULT_RP2_RAM_LIMIT,
    partial_retro: bool = DEFAULT_PARTIAL_RETRO,
) -> None:
    """Run the full pipeline and return the final out_paths.csv path."""
    sink_file = Path(sink_file).expanduser().resolve()
    rules_file = Path(rules_file).expanduser().resolve()
    logging.debug(f'sink_file: {sink_file}')
    logging.debug(f'rules_file: {rules_file}')
    validate_std_mode(std_mode)

    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)

        # 1) Rules (use provided or generate)
        if rules_file:
            rules_path = Path(rules_file)
        else:
            rules_path = tmpdir / f"rules.{DEFAULT_RULES_OUTPUT_FORMAT}"
            logging.debug(f"rules_path: {rules_path}")
            logging.debug("---- Parsing rules ----")
            parse_rules(
                outfile=str(rules_path),
                rule_type=rule_type,
                diameters=diameters,
                output_format=DEFAULT_RULES_OUTPUT_FORMAT,
            )

        # 2) Source from InChI
        logging.debug("------- generating source -------")
        source_path = tmpdir / "source.csv"
        generate_source_file_from_inchi(
            outfile=str(source_path),
            source_inchi=source_inchi,
        )

        logging.debug(f'tmp folder output: {glob.glob(str(tmpdir / "*"))}')

        # 3) Run RetroPath2 (writes scope/results to the given path)
        logging.debug("--------- RP2 -----------")
        rp2_scope_final = tmpdir / "target_scope.csv"
        rc = run_rp2(
            sink_file=sink_file,
            rules_file=str(rules_path),
            source_file=str(source_path),
            scope_results=str(rp2_scope_final),
            max_steps=max_steps,
            std_mode=std_mode,
            topx=topx,
            dmin=dmin,
            dmax=dmax,
            mwmax_source=mwmax_source,
            mwmax_cof=mwmax_cof,
            timeout=timeout,
            ram_limit=ram_limit,
            partial_retro=partial_retro,
        )
        logging.debug(f"RP2 status code: {rc}")
        logging.debug(f'RP2 output after run: {glob.glob(str(tmpdir / "*"))}')
        if rc!=0:
            raise RuntimeError(f"RP2 status code: {rc}")

        # Ensure scope/results CSV exists for downstream rp2paths
        if rp2_scope_final.is_file():
            shutil.copy(str(rp2_scope_final), out_scope)
        else:
            raise RuntimeError("RetroPath2 did not produce a scope/results CSV at expected path.")

        # 4) Run rp2paths on the scope
        with tempfile.TemporaryDirectory() as rp2paths_tmpdirname:
            rp2paths_tmpdir = Path(rp2paths_tmpdirname)
            run_rp2paths(str(rp2_scope_final), str(rp2paths_tmpdir))
            logging.debug(f'RP2paths output: {glob.glob(str(rp2paths_tmpdir / "*"))}')

            rp2paths_out = rp2paths_tmpdir / "out_paths.csv"
            if rp2paths_out.is_file():
                shutil.copyfile(str(rp2paths_out), out_paths)
            else:
                raise RuntimeError("RP2paths did not produce out_paths.csv")

            rp2paths_compounds = rp2paths_tmpdir / "compounds.txt" 
            #for some stupid reason compount.txt is a TSV 
            if rp2paths_compounds.is_file():
                cmp = pd.read_csv(str(rp2paths_compounds), sep='\t')
                cmp = cmp.set_index('Compound ID')
                cmp.to_csv(str(out_compounds), quotechar='"', quoting=csv.QUOTE_ALL)
                #shutil.copyfile(str(rp2paths_compounds), out_compounds)
            else:
                raise RuntimeError("RP2paths did not produce compounts.txt")

# -----------------------------
# CLI
# -----------------------------

def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    p = argparse.ArgumentParser(
        description="Run RetroPath2 from an InChI and post-process with rp2paths."
    )
    p.add_argument("--sink-file", required=True, help="Path to sink CSV file.")
    p.add_argument("--source-inchi", required=True, help="InChI string for the source compound.")
    p.add_argument("--out-scope", required=True,
                   help="User path for the output of retropath.")
    p.add_argument("--out-paths", required=True,
                   help="User path for the output paths of RP2paths.")
    p.add_argument("--out-compounds", required=True,
                   help="User path for the output compounds of RP2paths")
    # Optional outputs / inputs
    p.add_argument("--rules-file", required=False, default=None, help="Path to rules CSV file.")

    # Rules-generation
    p.add_argument("--diameters", default=DEFAULT_DIAMETERS,
                   help="Diameters (comma-separated from {2,4,6,8,10,12,14,16}).")
    p.add_argument("--rule-type", default=DEFAULT_RULES_TYPE, choices=["all", "retro", "forward"],
                   help="Rule type for parsing.")

    # RP2 controls
    p.add_argument("--std-mode", default=DEFAULT_STD_MODE, help="Standardization mode.")
    p.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS, help="Maximum number of steps.")
    p.add_argument("--topx", type=int, default=DEFAULT_TOPX, help="Top-X enumeration limit.")
    p.add_argument("--dmin", type=int, default=DEFAULT_DMIN, help="Minimum rule diameter.")
    p.add_argument("--dmax", type=int, default=DEFAULT_DMAX, help="Maximum rule diameter.")
    p.add_argument("--mwmax-source", type=int, default=DEFAULT_MWMAX_SOURCE,
                   help="Max molecular weight for intermediates.")
    p.add_argument("--mwmax-cof", type=int, default=DEFAULT_MWMAX_COF,
                   help="Coefficient for molecular weight constraint.")
    p.add_argument("--timeout", type=int, default=DEFAULT_RP2_TIMEOUT,
                   help="KNIME batch timeout (minutes).")
    p.add_argument("--ram-limit", type=int, default=DEFAULT_RP2_RAM_LIMIT,
                   help="Virtual memory GB limit (best-effort).")
    p.add_argument("--accept-partial-results", 
                   action=argparse.BooleanOptionalAction,
                   default=DEFAULT_PARTIAL_RETRO,
                   help="Return partial results if scope not produced.")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    try:
        # normalize/validate diameters
        cleaned_diameters = validate_diameters(args.diameters)

        pipe_status = run_pipeline(
            sink_file=args.sink_file,
            source_inchi=args.source_inchi,
            rules_file=args.rules_file,
            # rules-gen
            diameters=cleaned_diameters,
            rule_type=args.rule_type,
            # rp2
            max_steps=args.max_steps,
            std_mode=args.std_mode,
            topx=args.topx,
            dmin=args.dmin,
            dmax=args.dmax,
            mwmax_source=args.mwmax_source,
            mwmax_cof=args.mwmax_cof,
            timeout=args.timeout,
            ram_limit=args.ram_limit,
            partial_retro=args.accept_partial_results,
            out_scope=args.out_scope,
            out_paths=args.out_paths,
            out_compounds=args.out_compounds,
        )
        return 0
    except Exception as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
