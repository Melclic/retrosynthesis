"""
Created on March 7 2019

@author: Melchior du Lac
@description: Standalone version of RP2paths to be called from other scripts

"""
import subprocess
import resource
import tempfile
import glob
import io
import shutil
import logging
import os
import argparse
from typing import Tuple, Optional


MAX_VIRTUAL_MEMORY = 20000 * 1024 * 1024 # 20GB -- define what is the best
#MAX_VIRTUAL_MEMORY = 20 * 1024 * 1024 # 20GB -- define what is the best


def limit_virtual_memory() -> None:
    """Limit virtual memory available to child processes.

    This helper is intended to be passed as the ``preexec_fn`` to
    :pyfunc:`subprocess.Popen` so that the child process is constrained by
    ``MAX_VIRTUAL_MEMORY``.

    Returns:
        None
    """
    resource.setrlimit(resource.RLIMIT_AS, (MAX_VIRTUAL_MEMORY, resource.RLIM_INFINITY))


def run_rp2paths(
    rp2_pathways: str,
    out_paths: str = '',
    out_compounds: str = '',
    timeout: Optional[int] = None,
    ram_limit: Optional[int] = None,
) -> Tuple[str, bytes]:
    """Run RP2paths as a subprocess and collect its outputs.

    The function launches the RP2paths module (via ``python3 -m rp2paths``)
    against the provided pathways file, waits for completion, and copies the
    generated outputs to the caller-provided locations (or the current working
    directory when no destinations are provided).

    Args:
        rp2_pathways: Path to the rp2 pathways input file.
        out_paths: Destination path for the generated `out_paths.csv`. If
            empty, the file is written to the current working directory.
        out_compounds: Destination path for the generated `compounds.txt`. If
            empty, the file is written to the current working directory.
        timeout: Timeout for the rp2paths run in minutes. When ``None``, a
            default of 30 minutes is used.
        ram_limit: Optional RAM limit in GB to apply to the subprocess.

    Returns:
        A tuple ``(status, message_bytes)`` where ``status`` is a short status
        code such as ``'noerror'``, ``'timeout'``, ``'memoryerror'``,
        ``'filenotfounderror'``, etc., and ``message_bytes`` contains additional
        diagnostic information (command, stderr, or empty bytes) encoded as
        UTF-8.
    """
    if ram_limit:
        global MAX_VIRTUAL_MEMORY
        MAX_VIRTUAL_MEMORY = ram_limit*1000*1024*1024
        logging.debug('RAM limit: '+str(ram_limit)+' GB')
    else:
        logging.debug('RAM limit: 20 GB')
    if not timeout:
        logging.debug('Setting timeout to 30 min')
        timeout = 30.0
    with tempfile.TemporaryDirectory() as tmpOutputFolder:
        os.chdir('/home/rp2paths/')
        rp2paths_command = 'python3 -m rp2paths all '+str(rp2_pathways)+' --outdir '+str(tmpOutputFolder)+'/ --timeout '+str(int(timeout*60.0))
        try:
            commandObj = subprocess.Popen(rp2paths_command.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=limit_virtual_memory)
            result = ''
            error = ''
            result, error = commandObj.communicate()
            result = result.decode('utf-8')
            error = error.decode('utf-8')
            #TODO test to see what is the correct phrase
            if 'TIMEOUT' in result:
                logging.error('Timeout from of ('+str(timeout)+' minutes)')
                return 'timeout', str.encode('Command: '+str(rp2paths_command)+'\n Error: '+str(error)+'\n tmpOutputFolder: '+str(glob.glob(tmpOutputFolder+'/*')))
            if 'failed to map segment from shared object' in error:
                logging.error('RP2paths does not have sufficient memory to continue')
                return 'memoryerror', str.encode('Command: '+str(rp2paths_command)+'\n Error: '+str(error)+'\n tmpOutputFolder: '+str(glob.glob(tmpOutputFolder+'/*')))
            ### convert the result to binary and return ###
            try: 
                if out_paths:
                    shutil.copy(os.path.join(tmpOutputFolder, 'out_paths.csv'), out_paths)
                else:
                    shutil.copy(os.path.join(tmpOutputFolder, 'out_paths.csv'), os.path.join(os.getcwd(), 'out_paths.csv'))
                if out_compounds:
                    shutil.copy(os.path.join(tmpOutputFolder, 'compounds.txt'), out_compounds)
                else:
                    shutil.copy(os.path.join(tmpOutputFolder, 'compounds.txt'), os.path.join(os.getcwd(), 'compounds.txt'))
                return 'noerror', str('').encode('utf-8')
            except FileNotFoundError as e:
                logging.error('Cannot find the output files out_paths.csv or compounds.txt')
                return 'filenotfounderror', str.encode('Command: '+str(rp2paths_command)+'\n Error: '+str(e)+'\n tmpOutputFolder: '+str(glob.glob(tmpOutputFolder+'/*')))
        except OSError as e:
            logging.error('Subprocess detected an error when calling the rp2paths command')
            return 'oserror', str.encode('Command: '+str(rp2paths_command)+'\n Error: '+str(e)+'\n tmpOutputFolder: '+str(glob.glob(tmpOutputFolder+'/*')))
        except ValueError as e:
            logging.error('Cannot set the RAM usage limit')
            return 'ramerror', str.encode('Command: '+str(rp2paths_command)+'\n Error: '+str(e)+'\n tmpOutputFolder: '+str(glob.glob(tmpOutputFolder+'/*')))


def main():
    parser = argparse.ArgumentParser('Run RP2paths')
    parser.add_argument('-rp2_pathways', type=str, required=True)
    parser.add_argument('-out_paths', type=str, default='')
    parser.add_argument('-out_compounds', type=str, default='')
    parser.add_argument('-timeout', type=int, default=60)
    parser.add_argument('-ram_limit', type=int, default=10)
    params = parser.parse_args()
    run_rp2paths(rp2_pathways=params.rp2_pathways, 
                 out_paths=params.out_paths, 
                 out_compounds=params.out_compounds, 
                 timeout=params.timeout, 
                 ram_limit=params.ram_limit)

if __name__ == "__main__":
    main()
