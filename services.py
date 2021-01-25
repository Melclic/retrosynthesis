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
api = Api(app)

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
    appinfo = {'app': 'RetroPath2.0', 'version': '8.0',
               'author': 'Melchior du Lac, Joan Herisson, Thomas Duigou',
               'organization': 'BRS',
               'time': datetime.now().isoformat(),
               'status': status}
    out = appinfo.copy()
    out['data'] = data
    return out


class RestApp(Resource):
    """The Flask methods that we support, post and get
    """
    def post(self):
        return jsonify(stamp(None))
    def get(self):
        return jsonify(stamp(None))


# NOTE: Avoid returning numpy or pandas object in order to keep the client lighter.
class RestQuery(Resource):
    """Class containing the REST requests for RP2
    """
    def post(self):
        """Make the REST request using the POST method

        :rtype: Response
        :return: Flask Response object 
        """
        source_file_bytes = request.files['source_file'].read()
        sink_file_bytes = request.files['sink_file'].read()
        rules_file_bytes = request.files['rules_file'].read()
        params = json.load(request.files['data'])
        ##### REDIS ##############
        conn = Redis()
        q = Queue('default', connection=conn, default_time_out='24h')
        #pass the cache parameters to the rpCofactors object
        if params['partial_retro']=='True' or params['partial_retro']=='T' or params['partial_retro']=='true' or params['partial_retro']==True:
            partial_retro = True
        elif params['partial_retro']=='True' or params['partial_retro']=='F' or params['partial_retro']=='false' or params['partial_retro']==False:
            partial_retro = False
        else:
            app.logger.warning('Cannot interpret partial_retro: '+str(params['partial_retro']))
            app.logger.warning('Setting to False')
            partial_retro = False
        app.logger.debug('max_steps: '+str(params['max_steps']))
        app.logger.debug('topx: '+str(params['topx']))
        app.logger.debug('dmin: '+str(params['dmin']))
        app.logger.debug('dmax: '+str(params['dmax']))
        app.logger.debug('mwmax_source: '+str(params['mwmax_source']))
        app.logger.debug('mwmax_cof: '+str(params['mwmax_cof']))
        app.logger.debug('time_out: '+str(params['time_out']))
        app.logger.debug('ram_limit: '+str(params['ram_limit']))
        app.logger.debug('partial_retro: '+str(params['partial_retro']))
        async_results = q.enqueue(rpTool.run_rp2,
                                  source_file_bytes,
                                  sink_file_bytes,
                                  rules_file_bytes,
                                  int(params['max_steps']),
                                  int(params['topx']),
                                  int(params['dmin']),
                                  int(params['dmax']),
                                  int(params['mwmax_source']),
                                  int(params['mwmax_cof']),
                                  int(params['time_out']),
                                  int(params['ram_limit']),
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



api.add_resource(RestApp, '/REST')
api.add_resource(RestQuery, '/REST/Query')


if __name__== "__main__":
    handler = RotatingFileHandler('retropath2.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
    app.run(host="0.0.0.0", port=8888, debug=True, threaded=True)
