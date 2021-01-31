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
import logging
import os


MAX_VIRTUAL_MEMORY = 20000 * 1024 * 1024 # 20GB -- define what is the best
#MAX_VIRTUAL_MEMORY = 20 * 1024 * 1024 # 20GB -- define what is the best


def limit_virtual_memory():
    resource.setrlimit(resource.RLIMIT_AS, (MAX_VIRTUAL_MEMORY, resource.RLIM_INFINITY))


def run_rp2paths(rp2_pathways_bytes, timeout, ram_limit=None):
    """Make a subprocess call of rp2paths

    :param rp2_pathways_bytes: The rp2 pathways file as bytes
    :param timeout: The timeout of the function in minutes
    :param logging: The logging object

    :type rp2_pathways_bytes: bytes
    :type timeout: int
    :type logging: logging

    :rtype: tuple
    :return: tuple of bytes with the out_paths, the compunds, the status message, the command used
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
    out_paths = b''
    out_compounds = b''
    with tempfile.TemporaryDirectory() as tmpOutputFolder:
        rp2_pathways = os.path.join(tmpOutputFolder, 'tmp_rp2_pathways.csv')
        with open(rp2_pathways, 'wb') as outfi:
            outfi.write(rp2_pathways_bytes)
        rp2paths_command = 'python3 /home/rp2paths/RP2paths.py all '+str(rp2_pathways)+' --outdir '+str(tmpOutputFolder)+'/ --timeout '+str(int(timeout*60.0))
        try:
            commandObj = subprocess.Popen(rp2paths_command.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=limit_virtual_memory)
            result = b''
            error = b''
            result, error = commandObj.communicate()
            result = result.decode('utf-8')
            error = error.decode('utf-8')
            #TODO test to see what is the correct phrase
            if 'TIMEOUT' in result:
                logging.error('Timeout from of ('+str(timeout)+' minutes)')
                return b'', b'', b'timeout', str.encode('Command: '+str(rp2paths_command)+'\n Error: '+str(error)+'\n tmpOutputFolder: '+str(glob.glob(tmpOutputFolder+'/*')))
            if 'failed to map segment from shared object' in error:
                logging.error('RP2paths does not have sufficient memory to continue')
                return b'', b'', b'memoryerror', str.encode('Command: '+str(rp2paths_command)+'\n Error: '+str(error)+'\n tmpOutputFolder: '+str(glob.glob(tmpOutputFolder+'/*')))
            ### convert the result to binary and return ###
            try:
                with open(os.path.join(tmpOutputFolder, 'out_paths.csv'), 'rb') as op:
                    out_paths = op.read()
                with open(os.path.join(tmpOutputFolder, 'compounds.txt'), 'rb') as c:
                    out_compounds = c.read()
                return out_paths, out_compounds, b'noerror', b''
            except FileNotFoundError as e:
                logging.error('Cannot find the output files out_paths.csv or compounds.txt')
                return b'', b'', b'filenotfounderror', str.encode('Command: '+str(rp2paths_command)+'\n Error: '+str(e)+'\n tmpOutputFolder: '+str(glob.glob(tmpOutputFolder+'/*')))
        except OSError as e:
            logging.error('Subprocess detected an error when calling the rp2paths command')
            return b'', b'', b'oserror', str.encode('Command: '+str(rp2paths_command)+'\n Error: '+str(e)+'\n tmpOutputFolder: '+str(glob.glob(tmpOutputFolder+'/*')))
        except ValueError as e:
            logging.error('Cannot set the RAM usage limit')
            return b'', b'', b'ramerror', str.encode('Command: '+str(rp2paths_command)+'\n Error: '+str(e)+'\n tmpOutputFolder: '+str(glob.glob(tmpOutputFolder+'/*')))
