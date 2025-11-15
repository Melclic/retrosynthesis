#!/usr/bin/env python3
"""
Created on January 16 2020

@author: Melchior du Lac
@description: Script to run RetroPath2.0 from command line

"""


import subprocess
import logging
import csv
import glob
import resource
import os
import tempfile
import argparse
import shutil
from typing import Tuple, Optional


KPATH = '/usr/local/knime/knime'
RP_WORK_PATH = '/home/rp2/RetroPath2.0.knwf'


logging.basicConfig(
    level=logging.DEBUG,
    #level=logging.WARNING,
    #level=logging.ERROR,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S',
)


#MAX_VIRTUAL_MEMORY = 20000*1024*1024 # 20 GB -- define what is the best
MAX_VIRTUAL_MEMORY = 30000*1024*1024 # 30 GB -- define what is the best


def limit_virtual_memory() -> None:
    """Set an upper limit on the virtual memory available to child processes.

    This function is intended to be used as the ``preexec_fn`` for
    :pyfunc:`subprocess.Popen` so that the launched KNIME process cannot
    exceed the configured virtual memory limit.

    Returns:
        None
    """
    resource.setrlimit(resource.RLIMIT_AS, (MAX_VIRTUAL_MEMORY, resource.RLIM_INFINITY))


def run_rp2(
    sink_path: str,
    rules_path: str,
    source_inchi: str,
    results_csv: str,
    max_steps: int,
    source_name: str = 'target',
    topx: int = 100,
    dmin: int = 0,
    dmax: int = 1000,
    mwmax_source: int = 1000,
    mwmax_cof: int = 1000,
    timeout: int = 30,
    ram_limit: Optional[int] = None,
    partial_retro: bool = False,
) -> Tuple[str, bytes]:
    """Execute the KNIME RetroPath2.0 workflow and collect results.

    The function prepares temporary input files, constructs the KNIME CLI
    command with the provided parameters, runs KNIME as a subprocess and
    interprets the outputs and errors. The KNIME runtime timeout is provided
    in minutes and will be converted to seconds when passed to
    :pyfunc:`subprocess.Popen.communicate`.

    Args:
        sink_path: Path to the sink (organism) molecules file used by KNIME.
        rules_path: Path to the reaction rules CSV file.
        source_inchi: InChI string for the target/source molecule.
        results_csv: Destination path where KNIME results.csv should be copied.
        max_steps: Maximum allowed number of retrosynthesis steps.
        source_name: Name to assign to the source in the input CSV (default: "target").
        topx: Number of top-ranked rules to keep at each iteration (default: 100).
        dmin: Minimum reaction-rule diameter to request (default: 0).
        dmax: Maximum reaction-rule diameter to request (default: 1000).
        mwmax_source: Maximum molecular weight for source compounds (default: 1000).
        mwmax_cof: Maximum molecular weight for cofactors (default: 1000).
        timeout: Timeout for the KNIME run, in minutes (default: 30).
        ram_limit: Optional RAM limit in GB to apply to the subprocess (default: None).
        partial_retro: If True, allow returning partial results on failures (default: False).

    Returns:
        A tuple (status, message_bytes) where ``status`` is a short status code
        (e.g. 'noerror', 'timeouterror', 'memerror', etc.) and ``message_bytes``
        contains additional information (command, error messages, or empty
        bytes) encoded as UTF-8.

    Notes:
        - Temporary files are created in a temporary directory and removed on
          function exit. When partial results are requested and available, the
          results CSV will be copied to ``results_csv`` before returning.
        - The function logs detailed debug information to the module logger.
    """
    logger = logging.getLogger(__name__)
    logger.debug('Timeout: '+str(timeout*60.0)+' seconds')
    if ram_limit:
        global MAX_VIRTUAL_MEMORY
        MAX_VIRTUAL_MEMORY = ram_limit*1000*1024*1024
        logger.debug('RAM limit: '+str(ram_limit)+' GB')
    else:
        logger.debug('RAM limit: 30 GB')
    is_time_out = False
    is_results_empty = True
    ### run the KNIME RETROPATH2.0 workflow
    with tempfile.TemporaryDirectory() as tmp_output_folder:
        source_path = os.path.join(tmp_output_folder, 'source.csv')
        with open(source_path, 'w') as fi:
            csv_writer = csv.writer(fi, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(['Name', 'InChI'])
            csv_writer.writerow([source_name, source_inchi.replace(' ', '')])
        results_path = os.path.join(tmp_output_folder, 'results.csv')
        source_in_sink_path = os.path.join(tmp_output_folder, 'source-in-sink.csv')
        ### run the KNIME RETROPATH2.0 workflow
        try:
            knime_command = KPATH+' -nosplash -nosave -reset --launcher.suppressErrors -application org.knime.product.KNIME_BATCH_APPLICATION -workflowFile='+RP_WORK_PATH+' -workflow.variable=input.dmin,"'+str(dmin)+'",int -workflow.variable=input.dmax,"'+str(dmax)+'",int -workflow.variable=input.max-steps,"'+str(max_steps)+'",int -workflow.variable=input.sourcefile,"'+str(source_path)+'",String -workflow.variable=input.sinkfile,"'+str(sink_path)+'",String -workflow.variable=input.rulesfile,"'+str(rules_path)+'",String -workflow.variable=input.topx,"'+str(topx)+'",int -workflow.variable=input.mwmax-source,"'+str(mwmax_source)+'",int -workflow.variable=input.mwmax-cof,"'+str(mwmax_cof)+'",int -workflow.variable=output.dir,"'+str(tmp_output_folder)+'/",String -workflow.variable=output.solutionfile,"results.csv",String -workflow.variable=output.sourceinsinkfile,"source-in-sink.csv",String -preferences=/home/retrosynthesis/pref.epf'
            logging.debug(knime_command)
            commandObj = subprocess.Popen(knime_command.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=limit_virtual_memory)
            result = ''
            error = ''
            try:
                #commandObj.wait(timeout=timeout) #subprocess timeout is in seconds while we input minutes
                result, error = commandObj.communicate(timeout=timeout*60.0) #subprocess timeout is in seconds while we input minutes
            except subprocess.TimeoutExpired as e:
                commandObj.kill()
                is_time_out = True
            #(result, error) = commandObj.communicate()
            result = result.decode('utf-8')
            error = error.decode('utf-8')
            logger.debug('RetroPath2.0 results message: '+str(result))
            logger.debug('RetroPath2.0 error message: '+str(error))
            logger.debug('Output folder: '+str(glob.glob(tmp_output_folder+'/*')))
            #check to see if the results.csv is empty
            try:
                count = 0
                with open(results_path) as f:
                    reader = csv.reader(f, delimiter=',', quotechar='"')
                    for i in reader:
                        count += 1
                if count>1:
                    is_results_empty = False
            except (IndexError, FileNotFoundError) as e:
                logger.debug('No results.csv file')
                #is_results_empty is already set to True
                pass
            ########################################################################
            ##################### HANDLE all the different cases ###################
            ########################################################################
            ### if source is in sink. Note making sure that it contains more than the default first line
            try:
                count = 0
                with open(source_in_sink_path) as f:
                    reader = csv.reader(f, delimiter=',', quotechar='"')
                    for i in reader:
                        count += 1
                if count>1:
                    logger.error('Source has been found in the sink')
                    return 'sourceinsinkerror', str('Command: '+str(knime_command)+'\n Error: Source found in sink\n tmp_output_folder: '+str(glob.glob(tmp_output_folder+'/*'))).encode('utf-8')
            except FileNotFoundError as e:
                logger.error('Cannot find source-in-sink.csv file')
                logger.error(e)
                return 'sourceinsinknotfounderror', str('Command: '+str(knime_command)+'\n Error: '+str(e)+'\n tmp_output_folder: '+str(glob.glob(tmp_output_folder+'/*'))).encode('utf-8')
            ### handle timeout
            if is_time_out:
                if not is_results_empty and partial_retro:
                    logger.warning('Timeout from retropath2.0 ('+str(timeout)+' minutes)')
                    shutil.copy(results_path, results_csv)
                    return 'timeoutwarning', str('Command: '+str(knime_command)+'\n tmp_output_folder: '+str(glob.glob(tmp_output_folder+'/*'))).encode('utf-8')
                else:
                    logger.error('Timeout from retropath2.0 ('+str(timeout)+' minutes)')
                    return 'timeouterror', str('Command: '+str(knime_command)+'\n tmp_output_folder: '+str(glob.glob(tmp_output_folder+'/*'))).encode('utf-8')
            ### if java has an memory issue
            if 'There is insufficient memory for the Java Runtime Environment to continue' in result:
                if not is_results_empty and partial_retro:
                    logger.warning('RetroPath2.0 does not have sufficient memory to continue')
                    shutil.copy(results_path, results_csv)
                    logger.warning('Passing the results file instead')
                    return 'memwarning', str('Command: '+str(knime_command)+'\n Error: Memory error \n tmp_output_folder: '+str(glob.glob(tmp_output_folder+'/*'))).encode('utf-8')
                else:
                    logger.error('RetroPath2.0 does not have sufficient memory to continue')
                    return 'memerror', str('Command: '+str(knime_command)+'\n Error: Memory error \n tmp_output_folder: '+str(glob.glob(tmp_output_folder+'/*'))).encode('utf-8')
            ############## IF ALL IS GOOD ##############
            ### csv scope copy to the .dat location
            try:
                csv_scope = glob.glob(tmp_output_folder+'/*_scope.csv')
                shutil.copy(results_path, results_csv)
                return 'noerror', str('').encode('utf-8')
            except IndexError as e:
                if not is_results_empty and partial_retro:
                    logger.warning('No scope file generated')
                    shutil.copy(results_path, results_csv)
                    logger.warning('Passing the results file instead')
                    return 'noresultwarning', str('Command: '+str(knime_command)+'\n tmp_output_folder: '+str(glob.glob(tmp_output_folder+'/*'))).encode('utf-8')
                else:
                    logger.error('RetroPath2.0 has not found any results')
                    return 'noresulterror', str('Command: '+str(knime_command)+'\n Error: '+str(e)+'\n tmp_output_folder: '+str(glob.glob(tmp_output_folder+'/*'))).encode('utf-8')
        except OSError as e:
            if not is_results_empty and partial_retro:
                logger.warning('Running the RetroPath2.0 Knime program produced an OSError')
                logger.warning(e) 
                shutil.copy(results_path, results_csv)
                logger.warning('Passing the results file instead')
                return 'oswarning', str('Command: '+str(knime_command)+'\n tmp_output_folder: '+str(glob.glob(tmp_output_folder+'/*'))).encode('utf-8')
            else:
                logger.error('Running the RetroPath2.0 Knime program produced an OSError')
                logger.error(e)
                return 'oserror', str('Command: '+str(knime_command)+'\n Error: '+str(e)+'\n tmp_output_folder: '+str(glob.glob(tmp_output_folder+'/*'))).encode('utf-8')
        except ValueError as e:
            if not is_results_empty and partial_retro:
                logger.warning('Cannot set the RAM usage limit')
                logger.warning(e)
                shutil.copy(results_path, results_csv)
                logger.warning('Passing the results file instead')
                return 'ramwarning', str('Command: '+str(knime_command)+'\n tmp_output_folder: '+str(glob.glob(tmp_output_folder+'/*'))).encode('utf-8')
            else:
                logger.error('Cannot set the RAM usage limit')
                logger.error(e)
                return 'ramerror', str('Command: '+str(knime_command)+'\n Error: '+str(e)+'\n tmp_output_folder: '+str(glob.glob(tmp_output_folder+'/*'))).encode('utf-8')

def main():
    parser = argparse.ArgumentParser('Run RP2')
    parser.add_argument('-sink_path', type=str, required=True)
    parser.add_argument('-rules_path', type=str, required=True)
    parser.add_argument('-source_inchi', type=str, required=True)
    parser.add_argument('-results_csv', type=str, required=True)
    parser.add_argument('-max_steps', type=int, default=5)
    parser.add_argument('-source_name', type=str, default='target')
    parser.add_argument('-topx', type=int, default=100)
    parser.add_argument('-dmin', type=int, default=0)
    parser.add_argument('-dmax', type=int, default=1000)
    parser.add_argument('-mwmax_source', type=int, default=1000)
    parser.add_argument('-mwmax_cof', type=int, default=1000)
    parser.add_argument('-timeout', type=int, default=30)
    parser.add_argument('-ram_limit', type=int, default=30)
    parser.add_argument('-partial_retro', type=bool, default=False)
    params = parser.parse_args()
    run_rp2(sink_path=params.sink_path,
            rules_path=params.rules_path, 
            source_inchi=params.source_inchi,
            results_csv=params.results_csv,
            max_steps=params.max_steps,
            source_name=params.source_name,
            topx=params.topx,
            dmin=params.dmin,
            dmax=params.dmax,
            mwmax_source=params.mwmax_source,
            mwmax_cof=params.mwmax_cof,
            timeout=params.timeout,
            ram_limit=params.ram_limit, 
            partial_retro=params.partial_retro)

if __name__ == "__main__":
    main()

