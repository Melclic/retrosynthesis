import requests
import json
import tarfile
import io

#################### rp2paths ######################

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

