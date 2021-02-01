import os
import logging
import tempfile
import glob

import runRR
import runRP2
import runRP2paths

RR_FILE_FORMAT = 'csv'

def run(sink_bytes,
        source_inchi,
        max_steps,
        rr_diameters=[2,4,6,8,10,12,14,16],
        rr_type='all',
        rr_input_file_bytes=None,
        rr_input_file_format=None,
        source_name='target',
        topx=100,
        dmin=0,
        dmax=1000,
        mwmax_source=1000,
        mwmax_cof=1000,
        time_out=120,
        ram_limit=None,
        partial_retro=False):
    with tempfile.TemporaryDirectory() as tmp_dir:
        if rr_input_file_format=='csv':
            rr_file_path = os.path.join(tmp_dir, 'rr.csv')
        elif rr_input_file_format=='tar':
            rr_file_path = os.path.join(tmp_dir, 'rr.tar')
        if not rr_type in ['all', 'forward', 'retro']:
            return b'', b'', b'', b'rr_type' 
        rr_ouput_path = os.path.join(tmp_dir, 'rr.csv')
        ################ RetroRules #####################
        if not rr_input_file_bytes:
            rr_status = runRR.passRules(rr_ouput_path, rr_type, rr_diameters, RR_FILE_FORMAT)
        else:
            rr_input_file_path = os.path.join(tmp_dir, 'in_rules.csv')
            with open(rules_file_path, 'wb') as outbi:
                outbi.write(rr_input_file_bytes)
            rr_status = runRR.parseRules(rr_input_file_path, rr_ouput_path, rr_type, rr_diameters, rr_input_file_format, RR_FILE_FORMAT)
        if not rr_status:
            return b'', b'', b'', b'rr_status'
        ############### RetroPath2 ######################
        rules_bytes = b''
        with open(rr_ouput_path, 'rb') as outbi:
            rules_bytes = outbi.read()
        rp2_results = runRP2.run_rp2(sink_bytes,
                                     rules_bytes,
                                     source_inchi,
                                     max_steps,
                                     source_name,
                                     topx,
                                     dmin,
                                     dmax,
                                     mwmax_source,
                                     mwmax_cof,
                                     time_out,
                                     ram_limit,
                                     partial_retro)
        rules_bytes = None 
        if rp2_results[1]==b'time_outerror' or rp2_results[1]==b'time_outwarning':
            if not partial_retro:
                logging.error('Timeout of RetroPath2.0 -- Try increasing the time_out limit of the tool')
                return b'', b'', b'', b'rp2_time_out'
            else:
                if rp2_results[0]==b'':
                    return b'', b'', b'', b'rp2_time_out'
                else:
                    logging.warning('Timeout of RetroPath2.0 -- Try increasing the time_out limit of the tool -- Using partial rp2_resultss')
        elif rp2_results[1]==b'memwarning' or rp2_results[1]==b'memerror':
            if not partial_retro:
                logging.error('RetroPath2.0 has exceeded its memory limit')
                return b'', b'', b'', b'rp2_mem'
            else:
                if rp2_results[0]==b'':
                    logging.error('Memory limit reached by RetroPath2.0 caused it to not find any solutions')
                    return b'', b'', b'', b'rp2_mem'
                else:
                    logging.warning('RetroPath2.0 has exceeded its memory limit -- Using partial rp2_resultss')
        elif rp2_results[1]==b'sourceinsinkerror':
            logging.error('Source exists in the sink')
            return b'', b'', b'', b'rp2_source_in_sink'
        elif rp2_results[1]==b'sourceinsinknotfounderror':
            logging.error('Cannot find the sink-in-source file')
            return b'', b'', b'', b'rp2_knime'
        elif rp2_results[1]==b'ramerror' or rp2_results[1]==b'ramwarning':
            logging.error('Memory allocation error')
            return b'', b'', b'', b'rp2_ram'
        elif rp2_results[1]==b'oserror' or rp2_results[1]==b'oswarning':
            logging.error('RetroPath2.0 has generated an OS error')
            return b'', b'', b'', b'rp2_os'
        elif rp2_results[1]==b'norp2_resultswarning':
            if partial_retro:
                if rp2_results[0]==b'':
                    return b'', b'', b'', b'rp2_no_rp2_resultss'
                else:
                    logging.warning('RetroPath2.0 did not complete successfully -- using partial')
            else:
                logging.error('RetroPath2.0 could not complete successfully')
                return b'', b'', b'', b'rp2_no_rp2_results'
        elif rp2_results[1]==b'norp2_resultserror':
            logging.error('Empty rp2_rp2_results')
            return b'', b'', b'', b'rp2_no_rp2_results'
        elif rp2_results[1]==b'noerror':
            pass
        else:
            logging.error('Could not recognise the status message returned: '+str(rp2_results[1]))
            return b'', b'', b'', b'rp2_status'
        ############### RP2paths ####################
        rp2paths_results = runRP2paths.run_rp2paths(rp2_results[0], time_out, ram_limit)
        if rp2paths_results[2]==b'filenotfounderror':
            logging.error("FileNotFound Error from rp2paths \n "+str(rp2paths_results[3]))
            return b'', b'', b'', b'rp2paths_filenotfound'
        elif rp2paths_results[2]==b'oserror':
            logging.error("rp2paths has generated an OS error \n"+str(rp2paths_results[3]))
            return b'', b'', b'', b'rp2paths_oserror'
        elif rp2paths_results[2]==b'memoryerror':
            logging.error("rp2paths does not have sufficient memory to continue \n"+str(rp2paths_results[3]))
            return b'', b'', b'', b'rp2paths_mem'
        elif rp2paths_results[2]==b'ramerror':
            logging.error("Could not setup a RAM limit \n"+str(rp2paths_results[3]))
            return b'', b'', b'', b'rp2paths_ram'
        elif rp2paths_results[2]==b'time_out':
            logging.error("rp2paths has reached its time_out limit, try to increase it \n"+str(rp2paths_results[3]))
            return b'', b'', b'', b'rp2paths_time_out'
        if rp2paths_results[0]==b'' and rp2paths_results[1]==b'':
            logging.error("rp2paths has not found any rp2paths_resultss and returns empty files \n"+str(rp2paths_results[3]))
            return b'', b'', b'', b'rp2paths_empty'
        return rp2_results[0], rp2paths_results[0], rp2paths_results[1], b'noerrors'
