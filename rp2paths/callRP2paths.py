#!/usr/bin/env python3

"""
Created on March 7 2019

@author: Melchior du Lac
@description: Standalone version of RP2paths. Returns bytes to be able to use the same file in REST application

"""
import subprocess
import resource
import tempfile
import glob
import io
import shutil
import argparse
import os
import glob

import logging
#import logging.config
#from logsetup import LOGGING_CONFIG


#logging.config.dictConfig(LOGGING_CONFIG)
#logger = logging.getLogger(__name__)
logger = logging.getLogger(os.path.basename(__file__))



MAX_VIRTUAL_MEMORY = 20000 * 1024 * 1024 # 20GB -- define what is the best
#MAX_VIRTUAL_MEMORY = 20 * 1024 * 1024 # 20GB -- define what is the best

##
#
#
def limit_virtual_memory():
    """The function to set the memory limits
    """
    resource.setrlimit(resource.RLIMIT_AS, (MAX_VIRTUAL_MEMORY, resource.RLIM_INFINITY))

def run(rp2_pathways, rp2paths_pathways, rp2paths_compounds, timeout=30):
    """Call the KNIME RetroPath2.0 workflow

    :param rp2_pathways: The path to the RetroPath2.0 scope results
    :param timeout: The timeout of the function in minutes
    :param logger: Logger object (Default: None)

    :param source_bytes: str
    :param sink_bytes: int
    :param logger: logging

    :rtype: tuple
    :return: tuple of bytes with the out_paths results, compounds results, the status message, the command used
    """
    ### not sure why throws an error:
    #if logger==None:
    #    logger = logging.getLogger(__name__)
    logger.debug('Running RP2paths with timeout of '+str(timeout))
    out_paths = b''
    out_compounds = b''
    with tempfile.TemporaryDirectory() as tmp_output_folder:
        rp2paths_command = 'python /home/rp2paths/RP2paths.py all '+str(rp2_pathways)+' --outdir '+str(tmp_output_folder)+' --timeout '+str(int(timeout*60.0))
        try:
            commandObj = subprocess.Popen(rp2paths_command.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=limit_virtual_memory)
            result = b''
            error = b''
            result, error = commandObj.communicate()
            result = result.decode('utf-8')
            error = error.decode('utf-8')
            #TODO test to see what is the correct phrase
            if 'TIMEOUT' in result:
                logger.error('Timeout from of ('+str(timeout)+' minutes)')
                return False
            if 'failed to map segment from shared object' in error:
                logger.error('RP2paths does not have sufficient memory to continue')
                return False
            ### convert the result to binary and return ###
            logger.debug(glob.glob(os.path.join(tmp_output_folder, '*')))
            try:
                shutil.copy2(os.path.join(tmp_output_folder, 'out_paths.csv'), rp2paths_pathways)
                shutil.copy2(os.path.join(tmp_output_folder, 'compounds.txt'), rp2paths_compounds)
                return True
            except FileNotFoundError as e:
                logger.error('Cannot find the output files out_paths.csv or compounds.txt')
                return False
        except OSError as e:
            logger.error('Subprocess detected an error when calling the rp2paths command')
            return False
        except ValueError as e:
            logger.error('Cannot set the RAM usage limit')
            return False

# Wrapper for the RP2paths script that takes the same input (results.csv) as the original script but returns
# the out_paths.csv so as to be compliant with Galaxy
if __name__ == "__main__":
    parser = argparse.ArgumentParser('Python wrapper for the python RP2paths script')
    parser.add_argument('-rp_pathways', type=str)
    parser.add_argument('-rp2paths_pathways', type=str)
    parser.add_argument('-rp2paths_compounds', type=str)
    parser.add_argument('-timeout', type=int, default=30)
    params = parser.parse_args()
    if params.timeout<=0:
        logger.error('Timeout cannot be less or equal to 0 :'+str(params.timeout))
        exit(1)
    result = run(params.rp_pathways, params.rp2paths_pathways, params.rp2paths_compounds, params.timeout)
