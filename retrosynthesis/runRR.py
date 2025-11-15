#!/usr/bin/env python3
"""
Created on September 21 2019

@author: Melchior du Lac
@description: Return RetroRules from user defined diameters

"""

import csv
import io
import os
import shutil
import argparse
import tarfile
import tempfile

import logging
#import logging.config
#from logsetup import LOGGING_CONFIG


#logging.config.dictConfig(LOGGING_CONFIG)
#logger = logging.getLogger(__name__)
logger = logging.getLogger(os.path.basename(__file__))
from typing import List

def passRules(
    output: str,
    rules_type: str = 'all',
    diameters: List[int] = [2, 4, 6, 8, 10, 12, 14, 16],
    output_format: str = 'csv',
) -> bool:
    """Parse a bundled rules file and write rules filtered by diameter.

    This function selects the appropriate built-in rules CSV depending on
    ``rules_type`` and filters rows whose diameter is included in
    ``diameters``. The filtered rules are written to ``output`` either as a
    plain CSV file or as a gzipped tar archive containing `Rules.csv`.

    Args:
        output: Path to write the filtered rules to (CSV path or .tar.gz).
        rules_type: Which bundled rules to use: 'all', 'forward', or 'retro'.
        diameters: List of integer diameters to retain.
        output_format: Either 'csv' or 'tar' to control output packaging.

    Returns:
        True on success, False on failure.
    """
    logger.debug('Parsing the rules diamters '+str(diameters)+' for type '+str(rules_type)+' with output '+str(output_format)) 
    rule_file = None
    if rules_type=='all':
        rule_file = '/home/retrorules/rules_rall_rp2.csv' 
    elif rules_type=='forward':
        rule_file = '/home/retrorules/rules_rall_rp2_forward.csv'
    elif rules_type=='retro':
        rule_file = '/home/retrorules/rules_rall_rp2_retro.csv'
    else:
        logger.error('Cannot detect input: '+str(rules_type))
        return False
    #check the input diameters are valid #
    try:
        valid_diameters = []
        if isinstance(diameters, str):
            s_diameters = [int(i) for i in diameters.split(',')]
            for i in s_diameters:
                if i not in [2,4,6,8,10,12,14,16]:
                    logger.warning('Diameters must be either 2,4,6,8,10,12,14,16. Ignoring entry: '+str(i))
                else:
                    valid_diameters.append(i)
        else:
            for i in diameters:
                if i not in [2,4,6,8,10,12,14,16]:
                    logger.warning('Diameters must be either 2,4,6,8,10,12,14,16. Ignoring entry: '+str(i))
                else:
                    valid_diameters.append(i) 
    except ValueError:
        logger.error('Invalid diamter entry. Must be int of either 2,4,6,8,10,12,14,16')
        return False
    ##### create temp file to write ####
    with tempfile.TemporaryDirectory() as tmp_output_folder:
        outfile_path = os.path.join(tmp_output_folder, 'tmp_rules.csv')
        with open(rule_file, 'r') as rf:
            with open(outfile_path, 'w') as o:
                rf_csv = csv.reader(rf)
                o_csv = csv.writer(o, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
                o_csv.writerow(next(rf_csv))
                for row in rf_csv:
                    try:
                        if int(row[4]) in valid_diameters:
                            o_csv.writerow(row)
                    except ValueError:
                        logger.error('Cannot convert diameter to integer: '+str(row[4]))
                        return False
        if output_format=='tar':
            with tarfile.open(output, mode='w:gz') as ot:
                info = tarfile.TarInfo('Rules.csv')
                info.size = os.path.getsize(outfile_path)
                ot.addfile(tarinfo=info, fileobj=open(outfile_path, 'rb'))
        elif output_format=='csv':
            shutil.copy(outfile_path, output)
        else:
            logger.error('Cannot detect the output_format: '+str(output_format))
            return False
    return True


def parseRules(
    rule_file: str,
    output: str,
    rules_type: str = 'all',
    diameters: List[int] = [2, 4, 6, 8, 10, 12, 14, 16],
    input_format: str = 'csv',
    output_format: str = 'csv',
) -> bool:
    """Parse a rules file and write filtered rules by diameter.

    Supports both CSV and TSV input formats. Filters rows based on the
    provided ``diameters`` and, depending on ``rules_type``, filters by rule
    usage (forward/retro/both). The filtered rules are written to ``output``
    either as CSV or as a gzipped tar archive containing `Rules.csv`.

    Args:
        rule_file: Path to the input rules file (CSV or TSV).
        output: Path to write the filtered rules to (CSV path or .tar.gz).
        rules_type: Which rules to retain: 'all', 'forward', or 'retro'.
        diameters: List of integer diameters to retain.
        input_format: 'csv' or 'tsv' indicating the input file format.
        output_format: 'csv' or 'tar' indicating desired output packaging.

    Returns:
        True on success, False on failure.
    """
    #check the input diameters are valid #
    try:
        valid_diameters = []
        if isinstance(diameters, str):
            s_diameters = [int(i) for i in diameters.split(',')]
            for i in s_diameters:
                if i not in [2,4,6,8,10,12,14,16]:
                    logger.warning('Diameters must be either 2,4,6,8,10,12,14,16. Ignoring entry: '+str(i))
                else:
                    valid_diameters.append(i)
        else:
            for i in diameters:
                if i not in [2,4,6,8,10,12,14,16]:
                    logger.warning('Diameters must be either 2,4,6,8,10,12,14,16. Ignoring entry: '+str(i))
                else:
                    valid_diameters.append(i) 
    except ValueError:
        logger.error('Invalid diamter entry. Must be int of either 2,4,6,8,10,12,14,16')
        return False
    ##### create temp file to write ####
    with tempfile.TemporaryDirectory() as tmp_output_folder:
        ##### parse the input ######
        outfile_path = os.path.join(tmp_output_folder, 'tmp_rules.csv')
        if input_format=='tsv':
            with open(rule_file, 'r') as in_f:
                with open(outfile_path, 'w') as out_f:
                    out_csv = csv.writer(out_f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
                    out_csv.writerow([
                        "Rule ID",
                        "Rule",
                        "EC number",
                        "Reaction order",
                        "Diameter",
                        "Score",
                        "Legacy ID",
                        "Reaction direction",
                        "Rule relative direction",
                        "Rule usage",
                        "Score normalized"])
                    for row in csv.DictReader(in_f, delimiter='\t'):
                        try:
                            if int(row['Diameter']) in valid_diameters:
                                if rules_type=='all' or (rules_type=='retro' and (row['Rule_usage']=='both' or row['Rule_usage']=='retro')) or (rules_type=='forward' and (row['Rule_usage']=='both' or row['Rule_usage']=='forward')):
                                    out_csv.writerow([
                                        row['# Rule_ID'],
                                        row['Rule_SMARTS'],
                                        row['Reaction_EC_number'],
                                        row['Rule_order'],
                                        row['Diameter'],
                                        row['Score'],
                                        row['Legacy_ID'],
                                        row['Reaction_direction'],
                                        row['Rule_relative_direction'],
                                        row['Rule_usage'],
                                        row['Score_normalized']])
                        except ValueError:
                            #TODO: consider changing this to warning and passing to the next row
                            logger.error('Cannot convert diameter to integer: '+str(row['Diameter']))
                            return False
        elif input_format=='csv':
            with open(rule_file, 'r') as rf:
                with open(outfile_path, 'w') as o:
                    rf_csv = csv.reader(rf)
                    o_csv = csv.writer(o, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
                    o_csv.writerow(next(rf_csv))
                    for row in rf_csv:
                        try:
                            if int(row[4]) in valid_diameters:
                                if rules_type=='all' or (rules_type=='retro' and (row[9]=='both' or row[9]=='retro')) or (rules_type=='forward' and (row[9]=='both' or row[9]=='forward')):
                                    o_csv.writerow(row)
                        except ValueError:
                            logger.error('Cannot convert diameter to integer: '+str(row[4]))
                            return False
        else:
            logger.error('Can only have input formats of TSV or CSV')
            return False
        ##### build the output #####
        if output_format=='tar':
            with tarfile.open(output, mode='w:gz') as ot:
                info = tarfile.TarInfo('Rules.csv')
                info.size = os.path.getsize(outfile_path)
                ot.addfile(tarinfo=info, fileobj=open(outfile_path, 'rb'))
        elif output_format=='csv':
            shutil.copy(outfile_path, output)
        else:
            logger.error('Cannot detect the output_format: '+str(output_format))
            return False
    return True


def main():
    parser = argparse.ArgumentParser('Parse reaction rules to user defined diameters')
    parser.add_argument('-rules_type', type=str, default='all', choices=['all', 'forward', 'retro'])
    parser.add_argument('-rules_file', type=str, default='None')
    parser.add_argument('-output', type=str)
    parser.add_argument('-diameters', type=str, default='2,4,6,8,10,12,14,16')
    parser.add_argument('-output_format', type=str, default='csv', choices=['csv', 'tar'])
    parser.add_argument('-input_format', type=str, default='csv', choices=['csv', 'tsv'])
    params = parser.parse_args()
    if params.rules_file=='None' or params.rules_file==None:
        passRules(params.output, 
                  params.rules_type, 
                  [int(i) for i in params.diameters.split(',')], 
                  params.output_format)
    else:
        parseRules(params.rules_file,
                   params.output, 
                   params.rules_type, 
                   [int(i) for i in params.diameters.split(',')], 
                   params.input_format, 
                   params.output_format)

if __name__ == "__main__":
    main()
