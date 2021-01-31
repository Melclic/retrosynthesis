
import requests
import json
import tarfile
import io

### rp2paths
with open('rp_pathways.csv', 'rb') as r_f:
    data = {'ram_limit': 20,
            'timeout': 120}
    files = {'rp2_pathways': r_f,
             'data': ('data.json', json.dumps(data))}
    try:
        r = requests.post('http://0.0.0.0:8888/rp2paths', files=files)
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(r.text)
    return_content = r.content
    filelike = io.BytesIO(return_content)
    with tarfile.open(fileobj=filelike, mode='r:xz') as tf:
        with open('rp2paths_pathways_out.csv', 'wb') as rpp:
            rpp.write(tf.extractfile(tf.getmember('rp2paths_pathways')).read())
        with open('rp2paths_compounds_out.csv', 'wb') as rpc:
            rpc.write(tf.extractfile(tf.getmember('rp2paths_compounds')).read())

### rp2


import requests
import json
import tarfile
import io
with open('sinkfile.csv', 'rb') as s_f:
    with open('rules.tar', 'rb') as r_f:
        data = {'ram_limit': 30,
                'source_inchi': 'InChI=1S/C10H16/c1-7-4-5-8-6-9(7)10(8,2)3/h4,8-9H,5-6H2,1-3H3/t8-,9-/m1/s1',
                'rules_format': 'tar',
                'max_steps': 6}
        files = {'rules_file': r_f,
                 'sink_file': s_f,
                 'data': ('data.json', json.dumps(data))}
        try:
            r = requests.post('http://0.0.0.0:8888/retropath2', files=files)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(r.text)
        return_content = r.content
        filelike = io.BytesIO(return_content)
        with tarfile.open(fileobj=filelike, mode='r:xz') as tf:
            with open('rp2paths_pathways_out.csv', 'wb') as rpp:
                rpp.write(tf.extractfile(tf.getmember('rp2paths_pathways')).read())
            with open('rp2paths_compounds_out.csv', 'wb') as rpc:
                rpc.write(tf.extractfile(tf.getmember('rp2paths_compounds')).read())


### pipeline

import requests
import json
import tarfile
import io
with open('sinkfile.csv', 'rb') as s_f:
    with open('rules.tar', 'rb') as r_f:
        data = {'ram_limit': 30,
                'source_inchi': 'InChI=1S/C10H16/c1-7-4-5-8-6-9(7)10(8,2)3/h4,8-9H,5-6H2,1-3H3/t8-,9-/m1/s1',
                'rules_format': 'tar',
                'max_steps': 6}
        files = {'rules_file': r_f,
                 'sink_file': s_f,
                 'data': ('data.json', json.dumps(data))}
        try:
            r = requests.post('http://0.0.0.0:8888/pipeline', files=files)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(r.text)
        return_content = r.content
        filelike = io.BytesIO(return_content)
        with tarfile.open(fileobj=filelike, mode='r:xz') as tf:
            with open('rp2paths_pathways_out.csv', 'wb') as rpp:
                rpp.write(tf.extractfile(tf.getmember('rp2paths_pathways')).read())
            with open('rp2paths_compounds_out.csv', 'wb') as rpc:
                rpc.write(tf.extractfile(tf.getmember('rp2paths_compounds')).read())
            with open('rp2_pathways_out.csv', 'wb') as rpc:
                rpc.write(tf.extractfile(tf.getmember('rp2paths_pathways')).read())




########### test rp2paths ################

import runRP2paths

rp2_pathways_bytes = b''
with open('test/rp_pathways.csv', 'rb') as biout:
 rp2_pathways_bytes = biout.read()


rp2paths_res = runRP2paths.run_rp2paths(rp2_pathways_bytes, 120)



import runRP2

rules_bytes = b''
with open('test/Rules.csv', 'rb') as biout:
 rules_bytes = biout.read()


sink_bytes = b''
with open('test/sinkfile.csv', 'rb') as biout:
 sink_bytes = biout.read()


rp2_res = runRP2.run_rp2(sink_bytes, rules_bytes, 'InChI=1S/C10H16/c1-7-4-5-8-6-9(7)10(8,2)3/h4,8-9H,5-6H2,1-3H3/t8-,9-/m1/s1', 6)

from rq import Connection, Queue
from redis import Redis

conn = Redis()
q = Queue('default', connection=conn, default_timeout='24h')

registry = q.failed_job_registry
registry = q.started_job_registry
registry = q.finished_job_registry


job_ids = registry.get_job_ids()


registry = queue.finished_job_registry
[i for i in registry.get_job_ids()]


from rq.job import Job

redis = Redis()
job = Job.fetch('my_job_id', connection=redis)
print('Status: %s' % job.get_status())

