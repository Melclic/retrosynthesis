#!/usr/bin/env python3

"""
Created on December 7 2020

@author: Melchior du Lac
@description:

"""
import json
import os
import tempfile
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_file, abort, Response, make_response
from flask_restful import Resource, Api

from metaxime import rpCache
from metaxime import rpGraph
from metaxime import rpReader
from metaxime import rpFBA
from metaxime import rpSBML
from metaxime import rpEquilibrator
from metaxime import rpSelenzyme
from metaxime import rpGlobalScore

logger = logging.getLogger(__name__)

app = Flask(__name__)

GLOBAL_RPCACHE = rpCache()
GLOBAL_RPCACHE.populateCache()
SELENZYME_CACHE_PATH = '/home/metaxime/input_cache/rpselenzyme_data.tar.xz'
SELENZYME_OBJ = rpSelenzyme()
SELENZYME_PC, SELENZYME_UNIPROT_AA_LENGTH, SELENZYNE_DATA_DIR = SELENZYME_OBJ.loadCache(SELENZYME_CACHE_PATH)

#######################################################
##################### HELPER ##########################
#######################################################


def stamp(data, status=1):
    """Default message to return

    :param data: The data to be passes
    :param status: The int value of the status

    :type data: dict
    :type status: int

    :rtype: dict
    :return: The dict of the stamp
    """
    appinfo = {'app': 'Metaxime', 'version': '0.1',
               'author': 'Melchior du Lac',
               'time': datetime.now().isoformat(),
               'status': status}
    out = appinfo.copy()
    out['data'] = data
    return out


#######################################################
############## api ###################################
#######################################################


@app.route("/api", methods=["GET", "POST"])
@app.route("/", methods=["GET", "POST"])
def RestApp():
    """The Flask methods that we support, post and get
    """
    return jsonify(stamp(None))


@app.route("/api/rpReader", methods=["GET", "POST"])
def rpReader():
    with tempfile.TemporaryDirectory() as tmpdir:
        rp2_file = os.path.join(tmpdir, 'rp2.csv')
        with open(rp2_file, 'wb') as fo:
            fo.write(request.files['rp2_file'].read())
        rp2paths_compounds_file = os.path.join(tmpdir, 'rp2paths_compounds.csv')
        with open(rp2paths_compounds_file, 'wb') as fo:
            fo.write(request.files['rp2paths_compounds_file'].read())
        rp2paths_pathways_file = os.path.join(tmpdir, 'rp2paths_pathways.csv')
        with open(rp2paths_pathways_file, 'wb') as fo:
            fo.write(request.files['rp2paths_pathways_file'].read())
        rpcollection_file = os.path.join(tmpdir, 'rpcollection.tar.xz')
        status = rpReader.rp2ToCollection(rp2_file,
                                          rp2paths_compounds_file,
                                          rp2paths_pathways_file,
                                          rpcollection_file,
                                          rpcache=GLOBAL_RPCACHE)
        rpcollection_file.seek(0)
        return send_file(rpcollection_file,
                         as_attachment=True,
                         attachment_filename='rpcollection.tar.xz',
                         mimetype='application/x-tar')


@app.route("/api/rpEquilibrator", methods=["GET", "POST"])
def rpEquilibrator():
    with tempfile.TemporaryDirectory() as tmpdir:
        rpcollection_file = os.path.join(tmpdir, 'rpcollection.tar.xz')
        with open(rpcollection_file, 'wb') as fo:
            fo.write(request.files['rpcollection_file'].read())
        status = rpEquilibrator.runCollection(rpcollection_file,
                                              rpcollection_file,
                                              ph=params['ph'],
                                              ionic_strength=params['ionic_strength'],
                                              temp_k=params['temp_k'],
                                              rpcache=GLOBAL_RPCACHE)
        rpcollection_file.seek(0)
        return send_file(rpcollection_file,
                         as_attachment=True,
                         attachment_filename='rpcollection.tar.xz',
                         mimetype='application/x-tar')


@app.route("/api/rpFBA", methods=["GET", "POST"])
def rpFBA():
    with tempfile.TemporaryDirectory() as tmpdir:
        params = json.load(request.files['params'])
        rpcollection_file = os.path.join(tmpdir, 'rpcollection.tar.xz')
        with open(rpcollection_file, 'wb') as fo:
            fo.write(request.files['rpcollection_file'].read())
        gem_file = os.path.join(tmpdir, 'gem_file.sbml')
        with open(gem_file, 'wb') as fo:
            fo.write(request.files['gem_file'].read())
        status = rpFBA.runCollection(rpcollection_file,
                                     gem_file,
                                     rpcollection_file,
                                     num_workers=params['num_workers'],
                                     keep_merged=params['keep_merged'],
                                     del_sp_pro=params['del_sp_pro'],
                                     del_sp_react=params['del_sp_react'],
                                     rpcache=GLOBAL_RPCACHE)
        rpcollection_file.seek(0)
        return send_file(rpcollection_file,
                         as_attachment=True,
                         attachment_filename='rpcollection.tar.xz',
                         mimetype='application/x-tar')


@app.route("/api/rpSelenzyme", methods=["GET", "POST"])
def rpSelenzyme():
    with tempfile.TemporaryDirectory() as tmpdir:
        rpcollection_file = os.path.join(tmpdir, 'rpcollection.tar.xz')
        with open(rpcollection_file, 'wb') as fo:
            fo.write(request.files['rpcollection_file'].read())
        status = rpSelenzyme.runCollection(rpcollection_file,
                                           params['taxo_id'],
                                           rpcollection_file,
                                           uniprot_aa_length=SELENZYME_UNIPROT_AA_LENGTH,
                                           data_dir=SELENZYNE_DATA_DIR,
                                           pc=SELENZYME_PC,
                                           rpcache=GLOBAL_RPCACHE)
        rpcollection_file.seek(0)
        return send_file(rpcollection_file,
                         as_attachment=True,
                         attachment_filename='rpcollection.tar.xz',
                         mimetype='application/x-tar')


@app.route("/api/rpGlobalScore", methods=["GET", "POST"])
def rpGlobalScore():
    with tempfile.TemporaryDirectory() as tmpdir:
        rpcollection_file = os.path.join(tmpdir, 'rpcollection.tar.xz')
        with open(rpcollection_file, 'wb') as fo:
            fo.write(request.files['rpcollection_file'].read())
        status = rpGlobalScore.runCollection(rpcollection_file,
                                             rpcollection_file,
                                             rpcache=GLOBAL_RPCACHE)
        rpcollection_file.seek(0)
        return send_file(rpcollection_file,
                         as_attachment=True,
                         attachment_filename='rpcollection.tar.xz',
                         mimetype='application/x-tar')


@app.route("/api/rpPipeline", methods=["GET", "POST"])
def rpPipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        params = json.load(request.files['params'])
        rp2_file = os.path.join(tmpdir, 'rp2_file.csv')
        with open(rp2_file, 'wb') as fo:
            fo.write(request.files['rp2_file'].read())
        rp2paths_compounds_file = os.path.join(tmpdir, 'rp2paths_compounds_file.csv')
        with open(rp2paths_compounds_file, 'wb') as fo:
            fo.write(request.files['rp2paths_compounds_file'].read())
        rp2paths_pathways_file = os.path.join(tmpdir, 'rp2paths_pathways_file')
        with open(rp2paths_pathways_file, 'wb') as fo:
            fo.write(request.files['rp2paths_pathways_file'].read())
        gem_file = os.path.join(tmpdir, 'gem_file.sbml')
        with open(gem_file, 'wb') as fo:
            fo.write(request.files['gem_file'].read())
        rpcollection_file = os.path.join(tmpdir, 'rpcollection.tar.xz')
        rpre_status = rpReader.rp2ToCollection(rp2_file,
                                               rp2paths_compounds_file,
                                               rp2paths_pathways_file,
                                               rpcollection_file,
                                               rpcache=GLOBAL_RPCACHE)
        rpeq_status = rpEquilibrator.runCollection(rpcollection_file,
                                                   rpcollection_file,
                                                   ph=float(params['ph']),
                                                   ionic_strength=float(params['ionic_strength']),
                                                   temp_k=float(params['temp_k']),
                                                   rpcache=GLOBAL_RPCACHE)
        rpfba_status = rpFBA.runCollection(rpcollection_file,
                                           gem_file,
                                           rpcollection_file,
                                           num_workers=params['num_workers'],
                                           keep_merged=params['keep_merged'],
                                           del_sp_pro=params['del_sp_pro'],
                                           del_sp_react=params['del_sp_react'],
                                           rpcache=GLOBAL_RPCACHE)
        if params['taxo_id']==None:
            #if you cannot find the annotation then try to recover it from the GEM file
            rpsbml_gem = rpSBML(model_name='tmp', path=gem_file)
            params['taxo_id'] = rpsbml_gem.readTaxonomy()
        rpsel_status = rpSelenzyme.runCollection(rpcollection_file,
                                                 params['taxo_id'],
                                                 rpcollection_file,
                                                 uniprot_aa_length=SELENZYME_UNIPROT_AA_LENGTH,
                                                 data_dir=SELENZYNE_DATA_DIR,
                                                 pc=SELENZYME_PC,
                                                 rpcache=GLOBAL_RPCACHE)
        rpglo_status = rpGlobalScore.runCollection(rpcollection_file,
                                                   rpcollection_file,
                                                   rpcache=GLOBAL_RPCACHE)
        rpcollection_file.seek(0)
        return send_file(rpcollection_file,
                         as_attachment=True,
                         attachment_filename='rpcollection.tar.xz',
                         mimetype='application/x-tar')

if __name__== "__main__":
    #handler = RotatingFileHandler('metaxime.log', maxBytes=10000, backupCount=1)
    #handler.setLevel(logging.DEBUG)
    #logger.addHandler(handler)
    app.run(host="0.0.0.0", port=7777, debug=True, threaded=False)
