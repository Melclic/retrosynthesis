#!/usr/bin/env python3
"""
Created on January 16 2020

@author: Melchior du Lac
@description: Galaxy script to query rpRetroPath2.0 REST service

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


def limit_virtual_memory():
    """Limit the virtual of the subprocess call
    """
    resource.setrlimit(resource.RLIMIT_AS, (MAX_VIRTUAL_MEMORY, resource.RLIM_INFINITY))


def run_rp2(sink_path, 
            rules_path, 
            source_inchi, 
            results_csv, 
            max_steps, 
            source_name='target', 
            topx=100, 
            dmin=0, 
            dmax=1000, 
            mwmax_source=1000, 
            mwmax_cof=1000, 
            timeout=30, 
            ram_limit=None, 
            partial_retro=False):
    """Call the KNIME RetroPath2.0 workflow

    :param source_bytes: The source file as bytes
    :param sink_bytes: The sink file as bytes
    :param rules_bytes: The rules file as bytes
    :param max_steps: The maximal number of steps
    :param topx: The top number of reaction rules to keep at each iteraction (Default: 100)
    :param dmin: The minimum diameter of the reaction rules (Default: 0)
    :param dmax: The miximum diameter of the reaction rules (Default: 1000)
    :param mwmax_source: The maximal molecular weight of the intermediate compound (Default: 1000)
    :param mwmax_cof: The coefficient of the molecular weight of the intermediate compound (Default: 1000)
    :param timeout: The timeout of the function in minutes (Default: 30)
    :param partial_retro: Return partial results if the execution is interrupted for any reason (Default: False)
    :param logger: Logger object (Default: None)

    :type source_bytes: bytes
    :type sink_bytes: bytes
    :type rules_bytes: bytes
    :type max_steps: int
    :type topx: int
    :type dmin: int
    :type dmax: int
    :type mwmax_source: int
    :type mwmax_cof: int
    :type timeout: int
    :type partial_retro: bool
    :type logger: logging

    :rtype: tuple
    :return: tuple of bytes with the results, the status message, the KNIME command used
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

