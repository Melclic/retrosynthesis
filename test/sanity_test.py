
########### test rp2paths ################

import runRP2paths

rp2_pathways_bytes = b''
with open('/home/sanity_test/rp_pathways.csv', 'rb') as biout:
 rp2_pathways_bytes = biout.read()


rp2paths_res = runRP2paths.run_rp2paths(rp2_pathways_bytes, 120)


########## test rp2 #####################

import runRP2

rules_bytes = b''
with open('/home/sanity_test/Rules.csv', 'rb') as biout:
 rules_bytes = biout.read()


sink_bytes = b''
with open('/home/sanity_test/sinkfile.csv', 'rb') as biout:
 sink_bytes = biout.read()


rp2_res = runRP2.run_rp2(sink_bytes, rules_bytes, 'InChI=1S/C10H16/c1-7-4-5-8-6-9(7)10(8,2)3/h4,8-9H,5-6H2,1-3H3/t8-,9-/m1/s1', 6)


########### test rr #######################

import runRR

runRR.passRules('/home/sanity_test/test_rules.csv')
runRR.parseRules('/home/sanity_test/Rules.csv', '/home/sanity_test/test_rules.csv', input_format='csv', diameters=[2,4])

########### test pipeline #################


import retroPipeline

sink_bytes = b''
with open('/home/sanity_test/sinkfile.csv', 'rb') as biout:
 sink_bytes = biout.read()


retroPipeline.run(sink_bytes, 'InChI=1S/C10H16/c1-7-4-5-8-6-9(7)10(8,2)3/h4,8-9H,5-6H2,1-3H3/t8-,9-/m1/s1', 6)



