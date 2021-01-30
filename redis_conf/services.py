"""
Created on March 5 2019

@author: Melchior du Lac
@description: REST+RQ version of RetroPath2.0

"""
from datetime import datetime
from flask import Flask, request, jsonify, send_file, abort, Response, make_response
from flask_restful import Resource, Api
import io
import json
import time
import sys

import logging
from logging.handlers import RotatingFileHandler

from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'DEBUG',
        'handlers': ['wsgi']
    }
})


from rq import Connection, Queue
from redis import Redis

import runRR
import runRP2
import runRP2paths

#######################################################
############## REST ###################################
#######################################################

app = Flask(__name__)

#app.logger.setLevel(logging.WARNING)

def stamp(data, status=1):
    """Default message to return

    :param data: The data to be passes
    :param status: The int value of the status
    
    :type data: dict
    :type status: int

    :rtype: dict
    :return: The dict of the stamp
    """
    appinfo = {'app': 'Retrosynthesis', 'version': '0.1.0',
               'author': 'Melchior du Lac',
               'time': datetime.now().isoformat(),
               'status': status}
    out = appinfo.copy()
    out['data'] = data
    return out


#######################################################
############### API ###################################
#######################################################


@app.route("/api", methods=["GET", "POST"])
@app.route("/", methods=["GET", "POST"])
def RestApp():
    """The Flask methods that we support, post and get
    """
    return jsonify(stamp(None))


@app.route("/retropath2", methods=["POST"])
def retropath2():
    #parse the input request
    try:
        sink_file_bytes = request.files['sink_file'].read()
        rules_file_bytes = request.files['rules_file'].read()
    except KeyError as e:
        return Response('A required file is missing: '+str(e), status=400)
    try:
        rules_format = str(params['rules_format'])
        max_steps = int(params['max_steps'])
        source_inchi = str(params['source_inchi'])
        source_name = str(params['source_name'])
        topx = int(params['topx'])
        dmin = int(params['dmin'])
        dmax = int(params['dmax'])
        mwmax_source = int(params['mwmax_source'])
        mwmax_cof = int(params['mwmax_cof'])
        time_out = float(params['time_out'])
        ram_limit = float(params['ram_limit'])
        if params['partial_retro']=='True' or params['partial_retro']=='T' or params['partial_retro']=='true' or params['partial_retro']==True:
            partial_retro = True
        elif params['partial_retro']=='True' or params['partial_retro']=='F' or params['partial_retro']=='false' or params['partial_retro']==False:
            partial_retro = False
        else:
            app.logger.warning('Cannot interpret partial_retro: '+str(params['partial_retro']))
            app.logger.warning('Setting to False')
            partial_retro = False 
    except ValueError as e:
        return Response('One or more parameters are malformed: '+str(e), status=400)
    except KeyError as e:
        return Response('One or more of the parameters are missing: '+str(e), status=400)
    #make a directory with the tmp files that have been passed
    """ only for standalone version not REDIS
    with tempfile.TemporaryDirectory() as tmp_dir:
        source_file_path = os.path.join(tmp_dir, 'source.csv')
        with open(source_file_path, 'wb') as outfi:
            outfi.write(sink_file_bytes)
        source_file_bytes = None
        sink_file_path = os.path.join(tmp_dir, 'sink.csv')
        with open(sink_file_path, 'wb') as outfi:
            outfi.write(sink_file_bytes)
        sink_file_bytes = None
        rules_file_path = os.path.join(tmp_dir, 'rules.csv')
        if rules_format=='csv':
            with open(rules_file_path, 'wb') as outfi:
                outfi.write(rules_file_bytes)
        elif rules_format=='tar':
            #handle if the rules are tar
            with tempfile.TemporaryDirectory() as tmp_rules_dir:
                rules_tar_path = os.path.join(tmp_rules_dir, 'rules.tar')
                with open(rules_tar_path, 'wb') as outfi:
                    outfi.write(rules_file_bytes)
                with tarfile.open(rules_tar_path) as rf:
                    rf.extractall(tmp_rules_dir)
                out_file = glob.glob(os.path.join(tmp_rules_dir, '*.csv'))
                if len(out_file)>1:
                    app.logger.error('Cannot detect file: '+str(out_file))
                    return Responce('Cannot detect file: '+str(out_file), status=400)
                elif len(out_file)==0:
                    app.logger.error('The rules tar input is empty')
                    return Response('The rules tar input is empty', status=400)
                shutil.copy2(out_file[0], rules_file_path)
        else:
            app.logger.error('Cannot detect the rules_format: '+str(rules_format))
            return Response('Cannot detect the rules_format: '+str(rules_format), status=400)
        """
    #handle if the rules are tar
    if rules_format=='tar':
        with tempfile.TemporaryDirectory() as tmp_rules_dir:
            rules_tar_path = os.path.join(tmp_rules_dir, 'rules.tar')
            with open(rules_tar_path, 'wb') as outfi:
                outfi.write(rules_file_bytes)
            with tarfile.open(rules_tar_path) as rf:
                rf.extractall(tmp_rules_dir)
            out_file = glob.glob(os.path.join(tmp_rules_dir, '*.csv'))
            if len(out_file)>1:
                app.logger.error('Cannot detect file: '+str(out_file))
                return Responce('Cannot detect file: '+str(out_file), status=400)
            elif len(out_file)==0:
                app.logger.error('The rules tar input is empty')
                return Response('The rules tar input is empty', status=400)
            with open(out_file[0], 'rb') as outfi:
                rules_file_bytes = outfi.read()
    ##### run RetroPath2 ######
    async_results = q.enqueue(runRP2.run,
                              sink_file_bytes,
                              rules_file_bytes,
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
    result = None
    while result is None:
        result = async_results.return_value
        if async_results.get_status()=='failed':
            return Response('Redis job failed \n '+str(result), status=500)
        time.sleep(2.0)
    ###########################
    if result[1]==b'timeouterror' or result[1]==b'timeoutwarning':
        #for debugging
        app.logger.warning(result[2])
        if not partial_retro:
            app.logger.error('Timeout of RetroPath2.0 -- Try increasing the time_out limit of the tool')
            return Response('Timeout of RetroPath2.0--Try increasing the time_out limit of the tool', status=408)
        else:
            if result[0]==b'':
                return Response('Timeout caused RetroPath2.0 to not find any solutions', status=404)
            else:
                app.logger.warning('Timeout of RetroPath2.0 -- Try increasing the time_out limit of the tool')
                app.logger.warning('Returning partial results') 
                status_message = 'WARNING: Timeout of RetroPath2.0--Try increasing the time_out limit of the tool--Returning partial results'
                scope_csv = io.BytesIO()
                scope_csv.write(result[0])
                ###### IMPORTANT ######
                scope_csv.seek(0)
                #######################
                response = make_response(send_file(scope_csv, as_attachment=True, attachment_filename='rp2_pathways.csv', mimetype='text/csv'))
                response.headers['status_message'] = status_message
                return response
    elif result[1]==b'memwarning' or result[1]==b'memerror':
        #for debugging
        app.logger.warning(result[2])
        if not partial_retro:
            app.logger.error('RetroPath2.0 has exceeded its memory limit')
            return Response('RetroPath2.0 has exceeded its memory limit', status=403)
        else:
            if result[0]==b'':
                return Response('Memory limit reached by RetroPath2.0 caused it to not find any solutions', status=404)
            else:
                app.logger.warning('RetroPath2.0 has exceeded its memory limit')
                app.logger.warning('Returning partial results') 
                status_message = 'WARNING: RetroPath2.0 has exceeded its memory limit--Returning partial results'
                scope_csv = io.BytesIO()
                scope_csv.write(result[0])
                ###### IMPORTANT ######
                scope_csv.seek(0)
                #######################
                response = make_response(send_file(scope_csv, as_attachment=True, attachment_filename='rp2_pathways.csv', mimetype='text/csv'))
                response.headers['status_message'] = status_message
                return response
    elif result[1]==b'sourceinsinkerror':
        app.logger.error('Source exists in the sink')
        return Response('Source exists in the sink', status=403)
    elif result[1]==b'sourceinsinknotfounderror':
        app.logger.error('Cannot find the sink-in-source file')
        return Response('Cannot find the sink-in-source file', status=500)
    elif result[1]==b'ramerror' or result[1]==b'ramwarning':
        app.logger.error('Memory allocation error')
        return Response('Memory allocation error', status=500)
    elif result[1]==b'oserror' or result[1]==b'oswarning':
        app.logger.error('RetroPath2.0 has generated an OS error')
        return Response('RetroPath2.0 returned an OS error', status=500)
    elif result[1]==b'noresultwarning':
        if partial_retro:
            if result[0]==b'':
                return Response('No results warning caused it to return no results', status=404)
            else:
                app.logger.warning('RetroPath2.0 did not complete successfully')
                app.logger.warning('Returning partial results') 
                status_message = 'WARNING: RetroPath2.0 did not complete successfully--Returning partial results'
                scope_csv = io.BytesIO()
                scope_csv.write(result[0])
                ###### IMPORTANT ######
                scope_csv.seek(0)
                #######################
                response = make_response(send_file(scope_csv, as_attachment=True, attachment_filename='rp2_pathways.csv', mimetype='text/csv'))
                response.headers['status_message'] = status_message
                return response
        else:
            return Response('RetroPath2.0 could not complete successfully', status=404)
    elif result[1]==b'noresulterror':
        app.logger.error('Empty results')
        return Response('RetroPath2.0 cannot not find any solutions--Try reducing the complexity of the problem', status=404)
    elif result[1]==b'noerror':
        status_message = 'Successfull execution'
        scope_csv = io.BytesIO()
        scope_csv.write(result[0])
        ###### IMPORTANT ######
        scope_csv.seek(0)
        #######################
        response = make_response(send_file(scope_csv, as_attachment=True, attachment_filename='rp2_pathways.csv', mimetype='text/csv'))
        response.headers['status_message'] = status_message
        return response
    else:
        app.logger.error('Could not recognise the status message returned: '+str(results[1]))
        return Response('Could not recognise the status message returned: '+str(results[1]), status=500)


@app.route("/rp2paths", methods=["POST"])
def rp2paths():
    outtar = None
    rp2_pathways_bytes = request.files['rp2_pathways'].read()
    params = json.load(request.files['data'])
    try:
        timeout = float(params['timeout'])
    except KeyError:
        app.logger.warning('No timeout error')
        timeout = None
    except ValueError:
        app.logger.warning('Error parsing the timeout: '+str(timeout)+'. Setting default of 120min')
        timeout = None
    try:
        ram_limit = int(params['ram_lmit'])
    except KeyError:
        app.logger.warning('No ram limit value passed. Setting default of 20GB')
        ram_limit = None
    except ValueError:
        app.logger.warning('Error parsing the ram limit: '+str(ram_limit)+'. Setting default of 20GB')
        ram_limit = None
    ##### REDIS ##############
    conn = Redis()
    q = Queue('default', connection=conn, default_timeout='24h')
    #pass the cache parameters to the rpCofactors object
    async_results = q.enqueue(rpTool.run_rp2paths, rp2_pathways_bytes, timeout, ram_limit)
    result = None
    while result is None:
        result = async_results.return_value
        app.logger.info(async_results.return_value)
        app.logger.info(async_results.get_status())
        if async_results.get_status()=='failed':
            return Response('Job failed \n '+str(result), status=400)
        time.sleep(2.0)
    ########################### 
    if result[2]==b'filenotfounderror':
        app.logger.error("FileNotFound Error from rp2paths \n "+str(result[3]))
        return Response("FileNotFound Error from rp2paths \n "+str(result[3]), status=500)
    elif result[2]==b'oserror':
        app.logger.error("rp2paths has generated an OS error \n"+str(result[3]))
        return Response("rp2paths has generated an OS error \n"+str(result[3]), status=500)
    elif result[2]==b'memoryerror':
        app.logger.error("rp2paths does not have sufficient memory to continue \n"+str(result[3]))
        return Response("rp2paths does not have sufficient memory to continue \n"+str(result[3]), status=403)
    elif result[2]==b'ramerror':
        app.logger.error("Could not setup a RAM limit \n"+str(result[3]))
        return Response("Could not setup a RAM limit \n"+str(result[3]), status=500)
    elif result[2]==b'timeout':
        app.logger.error("rp2paths has reached its timeout limit, try to increase it \n"+str(result[3]))
        return Response("rp2paths has reached its timeout limit \n"+str(result[3]), status=408)
    if result[0]==b'' and result[1]==b'':
        app.logger.error("rp2paths has not found any results and returns empty files \n"+str(result[3]))
        return Response("rp2paths has not found any results and returns empty files \n"+str(result[3]), status=400)
    outtar = io.BytesIO()
    with tarfile.open(fileobj=outtar, mode='w:xz') as tf:
        #make a tar to pass back to the rp2path flask service
        out_paths = io.BytesIO(result[0])
        out_compounds = io.BytesIO(result[1])
        info = tarfile.TarInfo(name='rp2paths_pathways')
        info.size = len(result[0])
        tf.addfile(tarinfo=info, fileobj=out_paths)
        info = tarfile.TarInfo(name='rp2paths_compounds')
        info.size = len(result[1])
        tf.addfile(tarinfo=info, fileobj=out_compounds)
    ###### IMPORTANT ######
    outtar.seek(0)
    #######################
    return send_file(outtar, as_attachment=True, attachment_filename='rp2paths_result.tar', mimetype='application/x-tar')


@app.route("/retrorules", methods=["POST"])
def retrorules():
    #parse the input request
    if not 'rules_file' in request.files:
        rules_file_bytes = None
    else:
        rules_file_bytes = request.files['rules_file'].read()
    params = json.load(request.files['data'])
    try:
        diameters = [int(i) for i in params['diameters']split(',')]
        valid_diameters = []
        for i in diameters:
            if i not in [2,4,6,8,10,12,14,16]:
                app.logger.warning('Diameters must be either 2,4,6,8,10,12,14,16. Ignoring entry: '+str(i))
            else:
                valid_diameters.append(i)
        rules_type = str(params['rules_type']) 
        output_format = str(parans['output_format'])
        intput_format = str(parans['intput_format'])
    except ValueError:
        app.logger.error('Invalid diamter entry. Must be int of either 2,4,6,8,10,12,14,16')
        return Response('Invalid diamter entry. Must be int of either 2,4,6,8,10,12,14,16', status=400)
    except KeyError as e:
        app.logger.error('One of the parameters required is missing: '+str(e))
        return Response('One of the parameters required is missing: '+str(e), status=400)
    if output_format not in ['csv', 'tar']: 
        return Response('output_format must be either csv or tar', status=400)
    if rules_file_bytes:
        if input_format not in ['csv', 'tar']: 
            return Response('intput_format must be either csv or tar', status=400)
    if rules_format not in ['all', 'forward', 'retro']: 
        return Response('rules_format must be all, forward or retro', status=400)
    #parse the stuff
    with tempfile.TemporaryDirectory() as tmp_dir: 
        if output_format=='csv':
            out_file_path = os.path.join(tmp_dir, 'rr.csv')
        elif output_format=='tar':
            out_file_path = os.path.join(tmp_dir, 'rr.tar')
        else:
            app.logger.critical('output format should always be cav or tar')
            return Response('output_format must be either csv or tar', status=400)
        if not rules_file_bytes:
            rr_status = runRR.passRules(out_file_path, rules_type, valid_diameters, output_format)
        else:
            rules_file_path = os.path.join(tmp_dir, 'in_rules.csv')
            with open(rules_file_path, 'wb') as outbi:
                outbi.write(rules_file_bytes)
            rr_status = runRR.parseRules(rules_file_path, out_file_path, rules_type, valid_diameters, input_format, output_format)
        if rr_status:
            status_message = 'Successfull execution'
            rr_res = io.BytesIO()
            with open(out_file_path, 'rb') as biout:
                rr_res.write(biout.read())
            ###### IMPORTANT ######
            rr_res.seek(0)
            #######################
            if output_format=='csv':
                response = make_response(send_file(rr_res, as_attachment=True, attachment_filename='retrorules.csv', mimetype='text/csv'))
                response.headers['status_message'] = status_message
                return response
            elif output_format=='tar':
                response = make_response(send_file(rr_res, as_attachment=True, attachment_filename='retrorules.tar', mimetype='application/x-tar'))
                response.headers['status_message'] = status_message
                return response
        else:
            app.logger.error('There is a problem with RetroRules')
            return Response('There is a problem with RetroRules', status=400)
    

@app.route("/pipeline", methods=["POST"])
def pipeline():
    #parse the input request
    params = json.load(request.files['data'])
    if 'rules_file' in request.files:
        rr_input_file_bytes = request.files['rules_file'].read()
        rr_input_file_format = str(params['rules_format'])
    else:
        rr_input_file_bytes = None
        rr_input_file_format = None
    try:
        sink_file_bytes = request.files['sink_file'].read()
    except KeyError as e:
        return Response('Required sink file is missing: '+str(e), status=400)
    try:
        ram_limit = int(params['ram_limit'])
        timeout = float(params['timeout'])
        max_steps = int(params['max_steps'])
        source_inchi = str(params['source_inchi'])
        source_name = str(params['source_name'])
        topx = int(params['topx'])
        dmin = int(params['dmin'])
        dmax = int(params['dmax'])
        mwmax_source = int(params['mwmax_source'])
        mwmax_cof = int(params['mwmax_cof'])
        if params['partial_retro']=='True' or params['partial_retro']=='T' or params['partial_retro']=='true' or params['partial_retro']==True:
            partial_retro = True
        elif params['partial_retro']=='True' or params['partial_retro']=='F' or params['partial_retro']=='false' or params['partial_retro']==False:
            partial_retro = False
        else:
            app.logger.warning('Cannot interpret partial_retro: '+str(params['partial_retro']))
            app.logger.warning('Setting to False')
            partial_retro = False 
    except ValueError as e:
        return Response('One or more parameters are malformed: '+str(e), status=400)
    except KeyError as e:
        return Response('One or more of the parameters are missing: '+str(e), status=400)
    try:
        rr_diameters = [int(i) for i in params['rr_diameters'].split(',')]
        valid_diameters = []
        for i in diameters:
            if i not in [2,4,6,8,10,12,14,16]:
                app.logger.warning('Diameters must be either 2,4,6,8,10,12,14,16. Ignoring entry: '+str(i))
            else:
                valid_diameters.append(i)
        rules_type = str(params['rules_type']) 
        rr_input_file_format = str(parans['rr_input_file_format'])
    except ValueError:
        app.logger.error('Invalid diamter entry. Must be int of either 2,4,6,8,10,12,14,16')
        return Response('Invalid diamter entry. Must be int of either 2,4,6,8,10,12,14,16', status=400)
    except KeyError as e:
        app.logger.error('rr diamters are missing: '+str(e))
        return Response('One of the parameters required is missing: '+str(e), status=400)
    if output_format not in ['csv', 'tar']: 
        return Response('output_format must be either csv or tar', status=400)
    if rules_file_bytes:
        if input_format not in ['csv', 'tar']: 
            return Response('intput_format must be either csv or tar', status=400)
    if rules_format not in ['all', 'forward', 'retro']: 
        return Response('rules_format must be all, forward or retro', status=400)
    ##### REDIS ##############
    conn = Redis()
    q = Queue('default', connection=conn, default_timeout='24h')
    #pass the cache parameters to the rpCofactors object
    async_results = q.enqueue(pipeline.run,
                              rr_type,
                              valid_diameters,
                              sink_bytes,
                              source_inchi,
                              max_steps
                              rr_input_file_bytes,
                              rr_input_file_format,
                              source_name,
                              topx,
                              dmin,
                              dmax,
                              mwmax_source,
                              mwmax_cof,
                              timeout,
                              ram_limit,
                              partial_retro)
    result = None
    while result is None:
        result = async_results.return_value
        app.logger.info(async_results.return_value)
        app.logger.info(async_results.get_status())
        if async_results.get_status()=='failed':
            return Response('Job failed \n '+str(result), status=400)
        time.sleep(2.0)
    ########################### 
    if result[3]==b'rp2paths_empty':
        app.logger.error('rp2paths returned empty results')
        return Response('rp2paths returned empty results', status=500)
    elif result[3]==b'rp2paths_timeout':
        app.logger.error('rp2paths timed out')
        return Response('rp2paths timed out', status=500)
    elif result[3]==b'rp2paths_timeout':
        app.logger.error('rp2paths timed out')
        return Response('rp2paths timed out', status=500)
    elif result[3]==b'rp2paths_ram':
        app.logger.error('rp2paths cannot setup ram limit')
        return Response('rp2paths cannot set ram limit', status=500)
    elif result[3]==b'rp2paths_mem':
        app.logger.error('rp2paths has reached its memory limit')
        return Response('rp2paths has reached its memory limit', status=500)
    elif result[3]==b'rp2paths_os':
        app.logger.error('rp2paths has an OS error')
        return Response('rp2paths has an OS error', status=500)
    elif result[3]==b'rp2paths_filenotfound':
        app.logger.error('rp2paths has a FileNotFound error')
        return Response('rp2paths has a FileNotFound error', status=500)
    elif result[3]==b'rp2_status':
        app.logger.error('rp2 unknown error')
        return Response('rp2paths unknown error', status=500)
    elif result[3]==b'rp2_no_rp2_results':
        app.logger.error('rp2 has not found any solutions')
        return Response('rp2paths has not found any solutions', status=500)
    elif result[3]==b'rp2_status':
        app.logger.error('rp2 unknown error')
        return Response('rp2paths unknown error', status=500)
    elif result[3]==b'rp2_os':
        app.logger.error('rp2 has an OS error')
        return Response('rp2 has an OS error', status=500)
    elif result[3]==b'rp2_timeout':
        app.logger.error('rp2 timed out')
        return Response('rp2 timed out', status=500)
    elif result[3]==b'rp2_timeout':
        app.logger.error('rp2 timed out')
        return Response('rp2 timed out', status=500)
    elif result[3]==b'rp2_ram':
        app.logger.error('rp2 cannot setup ram limit')
        return Response('rp2 cannot set ram limit', status=500)
    elif result[3]==b'rp2_mem':
        app.logger.error('rp2 has reached its memory limit')
        return Response('rp2 has reached its memory limit', status=500)
    elif result[3]==b'rp2_knime':
        app.logger.error('rp2 has a KNIME error')
        return Response('rp2 has a KNIME error', status=500)
    elif result[3]==b'rr_input_format':
        app.logger.error('rr input error')
        return Response('rr input error', status=500)
    elif result[3]==b'rr_status':
        app.logger.error('rr status error')
        return Response('rr status error', status=500)
    elif result[3]==b'rr_status':
        app.logger.error('rr status error')
        return Response('rr status error', status=500)
    else:
        app.logger.error('Cannot recognise the pipeline status message: '+str(result[3]))
        return Response('Cannot recognise the pipeline status message: '+str(result[3]), status=500)
    ########## make the output ############
    outtar = io.BytesIO()
    with tarfile.open(fileobj=outtar, mode='w:xz') as tf:
        #make a tar to pass back to the rp2path flask service
        rp2_pathways = io.BytesIO(result[0])
        rp2paths_pathways = io.BytesIO(result[1])
        rp2paths_compounds = io.BytesIO(result[2])
        info = tarfile.TarInfo(name='rp2_pathways')
        info.size = len(result[0])
        tf.addfile(tarinfo=info, fileobj=rp2_pathways)
        info = tarfile.TarInfo(name='rp2paths_pathways')
        info.size = len(result[1])
        tf.addfile(tarinfo=info, fileobj=rp2paths_pathways)
        info = tarfile.TarInfo(name='rp2paths_compounds')
        info.size = len(result[2])
        tf.addfile(tarinfo=info, fileobj=rp2paths_compounds)
    ###### IMPORTANT ######
    outtar.seek(0)
    #######################
    return send_file(outtar, as_attachment=True, attachment_filename='retrosynthesis.tar', mimetype='application/x-tar')



if __name__== "__main__":
    handler = RotatingFileHandler('retrosynthesis.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
    app.run(host="0.0.0.0", port=8888, debug=True, threaded=True)
