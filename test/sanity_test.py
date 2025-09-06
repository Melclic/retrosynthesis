
########### test rp2paths ################

import runRP2paths

rp2paths_res = runRP2paths.run_rp2paths('/home/sanity_test/rp_pathways.csv', 120)


########## test rp2 #####################

import runRP2

rp2_res = runRP2.run_rp2('/home/sanity_test/sinkfile.csv', '/home/sanity_test/Rules.csv', 'InChI=1S/C10H16/c1-7-4-5-8-6-9(7)10(8,2)3/h4,8-9H,5-6H2,1-3H3/t8-,9-/m1/s1', 6)


########### test rr #######################

import runRR

runRR.passRules('/home/sanity_test/test_rules.csv')
runRR.parseRules('/home/sanity_test/Rules.csv', '/home/sanity_test/test_rules.csv', input_format='csv', diameters=[2,4])

########### test pipeline #################


import retroPipeline

retroPipeline.run('/home/sanity_test/sinkfile.csv', 'InChI=1S/C10H16/c1-7-4-5-8-6-9(7)10(8,2)3/h4,8-9H,5-6H2,1-3H3/t8-,9-/m1/s1', 6)



