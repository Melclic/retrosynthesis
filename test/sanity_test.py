########### test rp2paths ################

import runRP2paths

rp2_pathways_bytes = b''
with open('test/rp_pathways.csv', 'rb') as biout:
 rp2_pathways_bytes = biout.read()

runRP2paths.run_rp2paths(rp2_pathways_bytes, 120)

############ test retropath2 ##############


