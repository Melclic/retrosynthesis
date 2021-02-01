import requests
import json
import tarfile
import io

### rp2paths
with open('sanity_test/rp_pathways.csv', 'rb') as r_f:
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


with open('sanity_test/sinkfile.csv', 'rb') as s_f:
    with open('sanity_test/rules.tar', 'rb') as r_f:
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
            with open('sanity_test/rp2paths_pathways_out.csv', 'wb') as rpp:
                rpp.write(tf.extractfile(tf.getmember('rp2paths_pathways')).read())
            with open('sanity_test/rp2paths_compounds_out.csv', 'wb') as rpc:
                rpc.write(tf.extractfile(tf.getmember('rp2paths_compounds')).read())


### rr




### pipeline

with open('sanity_test/sinkfile.csv', 'rb') as s_f:
    data = {'source_inchi': 'InChI=1S/C10H16/c1-7-4-5-8-6-9(7)10(8,2)3/h4,8-9H,5-6H2,1-3H3/t8-,9-/m1/s1',
            'max_steps': 6}
    files = {'sink_file': s_f,
             'data': ('data.json', json.dumps(data))}
    try:
        r = requests.post('http://0.0.0.0:8888/pipeline', files=files)
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(r.text)
    return_content = r.content
    filelike = io.BytesIO(return_content)
    with tarfile.open(fileobj=filelike, mode='r:xz') as tf:
        with open('sanity_test/rp2paths_pathways_out.csv', 'wb') as rpp:
            rpp.write(tf.extractfile(tf.getmember('rp2paths_pathways')).read())
        with open('sanity_test/rp2paths_compounds_out.csv', 'wb') as rpc:
            rpc.write(tf.extractfile(tf.getmember('rp2paths_compounds')).read())
        with open('sanity_test/rp2_pathways_out.csv', 'wb') as rpc:
            rpc.write(tf.extractfile(tf.getmember('rp2paths_pathways')).read())
