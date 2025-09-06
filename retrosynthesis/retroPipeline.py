import os
import logging
import tempfile
import argparse
import shutil
import tarfile
import glob

import runRR
import runRP2
import runRP2paths

RR_FILE_FORMAT = 'csv'

def run(sink_path,
        source_inchi,
        max_steps,
        rp2_output='',
        rp2_paths='',
        rp2_cmps='',
        tar_all=None,
        rr_diameters=[2,4,6,8,10,12,14,16],
        rr_type='all',
        rr_input_file=None,
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
        rp2paths_out_paths = os.path.join(tmp_dir, 'out_paths.csv')
        rp2paths_out_compounds = os.path.join(tmp_dir, 'out_compounds.csv')
        rp2_path_results = os.path.join(tmp_dir, 'results.csv')
        if not rr_type in ['all', 'forward', 'retro']:
            logging.error('Cannot recognise the input rr_type: '+str(rr_type))
            return 'rr_type' 
        ################ RetroRules #####################
        rules_path = os.path.join(tmp_dir, 'reaction_rules.csv')
        if not rr_input_file:
            rr_status = runRR.passRules(output=rules_path,
                                        rules_type=rr_type, 
                                        diameters=rr_diameters, 
                                        output_format=RR_FILE_FORMAT)
        else:
            rr_status = runRR.parseRules(rule_file=rr_input_file, 
                                         output=rules_path, 
                                         rules_type=rr_type, 
                                         diameters=rr_diameters, 
                                         input_format=rr_input_file_format, 
                                         output_format=RR_FILE_FORMAT)
        if not rr_status:
            logging.error('Reaction rule failed')
            return 'rr_status'
        ############### RetroPath2 ######################
        rp2_results = runRP2.run_rp2(sink_path=sink_path,
                                     rules_path=rules_path,
                                     source_inchi=source_inchi,
                                     results_csv=rp2_path_results,
                                     max_steps=max_steps,
                                     source_name=source_name,
                                     topx=topx,
                                     dmin=dmin,
                                     dmax=dmax,
                                     mwmax_source=mwmax_source,
                                     mwmax_cof=mwmax_cof,
                                     timeout=time_out,
                                     ram_limit=ram_limit,
                                     partial_retro=partial_retro)
        if rp2_results[0]=='time_outerror' or rp2_results[0]=='time_outwarning':
            logging.error('Timeout of RetroPath2.0 -- Try increasing the time_out limit of the tool')
            return 'rp2_time_out'
        elif rp2_results[0]=='memwarning' or rp2_results[0]=='memerror':
            logging.error('RetroPath2.0 has exceeded its memory limit')
            return 'rp2_mem'
        elif rp2_results[0]=='sourceinsinkerror':
            logging.error('Source exists in the sink')
            return 'rp2_source_in_sink'
        elif rp2_results[0]=='sourceinsinknotfounderror':
            logging.error('Cannot find the sink-in-source file')
            return 'rp2_knime'
        elif rp2_results[0]=='ramerror' or rp2_results[0]=='ramwarning':
            logging.error('Memory allocation error')
            return 'rp2_ram'
        elif rp2_results[0]=='oserror' or rp2_results[0]=='oswarning':
            logging.error('RetroPath2.0 has generated an OS error')
            return 'rp2_os'
        elif rp2_results[0]=='norp2_resultswarning':
            logging.error('RetroPath2.0 could not complete successfully')
            return 'rp2_no_rp2_results'
        elif rp2_results[0]=='norp2_resultserror':
            logging.error('Empty rp2_rp2_results')
            return 'rp2_no_rp2_results'
        elif rp2_results[0]=='noresulterror':
            logging.error('No Results found')
            return 'rp2_no_rp2_results'
        elif rp2_results[0]=='noerror':
            pass
        else:
            logging.error('Could not recognise the status message returned: '+str(rp2_results[0]))
            return 'rp2_status'
        ############### RP2paths ####################
        rp2paths_results = runRP2paths.run_rp2paths(rp2_pathways=rp2_path_results, 
                                                    out_paths=rp2paths_out_paths, 
                                                    out_compounds=rp2paths_out_compounds, 
                                                    timeout=time_out, 
                                                    ram_limit=ram_limit)
        if rp2paths_results[0]=='filenotfounderror':
            logging.error("FileNotFound Error from rp2paths")
            return 'rp2paths_filenotfound'
        elif rp2paths_results[0]=='oserror':
            logging.error("rp2paths has generated an OS error")
            return 'rp2paths_oserror'
        elif rp2paths_results[0]=='memoryerror':
            logging.error("rp2paths does not have sufficient memory to continue")
            return 'rp2paths_mem'
        elif rp2paths_results[0]=='ramerror':
            logging.error("Could not setup a RAM limit")
            return 'rp2paths_ram'
        elif rp2paths_results[0]=='time_out':
            logging.error("rp2paths has reached its time_out limit, try to increase it")
            return 'rp2paths_time_out'
        elif rp2paths_results[0]=='':
            logging.error("rp2paths has not found any rp2paths_resultss and returns empty files")
            return 'rp2paths_empty'
        elif rp2paths_results[0]=='noerror':
            pass
        else:
            logging.error('Cannot interpret the rp2paths output: '+str(rp2paths_results[0]))
            return 'bad_rp2paths_output'
        if rp2_output:
            shutil.copy(rp2_path_results, rp2_output)
        else:
            shutil.copy(rp2_path_results, os.path.join(os.getcwd(), 'rp2_output.csv'))
        if rp2_paths:
            shutil.copy(rp2paths_out_paths, rp2_paths)
        else:
            shutil.copy(rp2paths_out_paths, os.path.join(os.getcwd(), 'rp2paths_out_paths.csv'))
        if rp2_cmps:
            shutil.copy(rp2paths_out_compounds, rp2_cmps)
        else:
            shutil.copy(rp2paths_out_compounds, os.path.join(os.getcwd(), 'rp2paths_out_compounds.csv'))
        if tar_all:
            if not tar_all.endswith('tar.gz'):
                tar_all += '.tar.gz'
            with tarfile.open(tar_all, "w:gz") as tar:
                tar.add(rp2paths_out_paths, arcname=os.path.basename(rp2paths_out_paths))
                tar.add(rp2paths_out_compounds, arcname=os.path.basename(rp2paths_out_compounds))
                tar.add(rules_path, arcname=os.path.basename(rules_path))
                tar.add(rp2_path_results, arcname=os.path.basename(rp2_path_results))
        return 'noerrors'


def main():
    parser = argparse.ArgumentParser(description='Run the retrosynthesis pipeline')
    parser.add_argument("-sink", "--sink_path", type=str, help="Input sink (organims) molecule", required=True)
    parser.add_argument("-source", "--source_inchi", type=str, help="Input (target) Inchi", required=True)
    parser.add_argument("-orp", "--rp2_output", type=str, help="RP2 results file", default='')
    parser.add_argument("-orp2p", "--rp2_paths", type=str, help="RP2paths pathway results file", default='')
    parser.add_argument("-orp2pc", "--rp2_cmps", type=str, help="RP2paths compounds results file", default='')
    parser.add_argument("-co", "--compressed_results", type=str, help="Output TAR with all the intermediate files", default='')
    parser.add_argument("-s", "--max_steps", type=int, help="Maximum heterologous pathway length", default=5)
    parser.add_argument("-d", "--rr_diameters", type=str, help="Diameters of the reaction rules", default='2,4,6,8,10,12,14,16')
    parser.add_argument("-rt", "--rr_type", type=str, help="The type of retrorules", default='all')
    parser.add_argument("-rri", "--rr_input_file", type=str, help="RetroRules input file", default=None)
    parser.add_argument("-rrf", "--rr_input_format", type=str, help="RetroRules input format", default=None)
    parser.add_argument("-sn", "--source_name", type=str, help="The name of the source", default='target')
    parser.add_argument("-t", "--topx", type=int, help='TopX reaction rule at each iteration', default=100)
    parser.add_argument("-dmin", "--min_dimension", type=int, help='Minimal reaction rule dimension', default=0)
    parser.add_argument("-dmax", "--max_dimension", type=int, help='Maximal reaction rule dimension', default=1000)
    parser.add_argument("-ms", "--mwmax_source", type=int, help='Max source iteraction', default=1000)
    parser.add_argument("-mc", "--mwmax_cof", type=int, help='Max source coefficient', default=1000)
    parser.add_argument("-to", "--time_out", type=int, help='Time out', default=120)
    parser.add_argument("-r", "--ram_limit", type=int, help='Ram limit of the execution', default=20)
    parser.add_argument("-p", "--partial_retro", type=bool, help='Ram limit of the execution', default=False)
    args = parser.parse_args()
    run(sink_path=args.sink_path,
        source_inchi=args.source_inchi,
        max_steps=args.max_steps,
        rp2_output=args.rp2_output,
        rp2_paths=args.rp2_paths,
        rp2_cmps=args.rp2_cmps,
        tar_all=args.compressed_results,
        rr_diameters=[int(i) for i in args.rr_diameters.split(',')],
        rr_type=args.rr_type,
        rr_input_file=args.rr_input_file,
        rr_input_file_format=args.rr_input_format,
        source_name=args.source_name,
        topx=args.topx,
        dmin=args.min_dimension,
        dmax=args.max_dimension,
        mwmax_source=args.mwmax_source,
        mwmax_cof=args.mwmax_cof,
        time_out=args.time_out,
        ram_limit=args.ram_limit,
        partial_retro=args.partial_retro)

if __name__ == "__main__":
    main()
