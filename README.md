# Retrosynthesis

Perform retrosynthesis search of possible metabolic routes between a source molecule and a collection of sink molecules. Docker implementation of the KNIME retropath2.0 workflow. Takes for input the minimal (dmin) and maximal (dmax) diameter for the reaction rules and the maximal path length (maxSteps). The docker mounts a local folder and expects the following files: rules.csv, sink.csv and source.csv. We only support a single source molecule at this time. 

## Running the tools

To run the tool, we recommend that you use the CWL executors to run the tools. To issue a command manually, you will need to mount a local directory on docker and issue an appropriate bash command to run your tool of interest. For example, to generate the reaction rules:

```
docker run -v path/to/your/directory:/home/results/ -it melclic/retrosynthesis:latest retrorules -output /home/results/rules.csv -diameters 4,6,8,10,12
```

### RetroPath2.0

```bash
usage: Run RP2 [-h] -sink_path SINK_PATH -rules_path RULES_PATH -source_inchi
               SOURCE_INCHI -results_csv RESULTS_CSV [-max_steps MAX_STEPS]
               [-source_name SOURCE_NAME] [-topx TOPX] [-dmin DMIN]
               [-dmax DMAX] [-mwmax_source MWMAX_SOURCE]
               [-mwmax_cof MWMAX_COF] [-timeout TIMEOUT]
               [-ram_limit RAM_LIMIT] [-partial_retro PARTIAL_RETRO]

optional arguments:
  -h, --help            show this help message and exit
  -sink_path SINK_PATH
  -rules_path RULES_PATH
  -source_inchi SOURCE_INCHI
  -results_csv RESULTS_CSV
  -max_steps MAX_STEPS
  -source_name SOURCE_NAME
  -topx TOPX
  -dmin DMIN
  -dmax DMAX
  -mwmax_source MWMAX_SOURCE
  -mwmax_cof MWMAX_COF
  -timeout TIMEOUT
  -ram_limit RAM_LIMIT
  -partial_retro PARTIAL_RETRO
```

Example usage:


### rp2paths

Run the rp2paths tool on the different 

```bash
usage: Run RP2paths [-h] -rp2_pathways RP2_PATHWAYS [-out_paths OUT_PATHS]
                    [-out_compounds OUT_COMPOUNDS] [-timeout TIMEOUT]
                    [-ram_limit RAM_LIMIT]

optional arguments:
  -h, --help            show this help message and exit
  -rp2_pathways RP2_PATHWAYS
  -out_paths OUT_PATHS
  -out_compounds OUT_COMPOUNDS
  -timeout TIMEOUT
  -ram_limit RAM_LIMIT
```

Example usage:

```
runRP2paths -rp2_pathways sanity_test/results.csv -out_paths sanity_test/rp2_paths.csv -out_compounds sanity_test/rp2_cmps.csv
```

### RetroRules

```bash
usage: Parse reaction rules to user defined diameters [-h]
                                                      [-rules_type {all,forward,retro}]
                                                      [-rules_file RULES_FILE]
                                                      [-output OUTPUT]
                                                      [-diameters DIAMETERS]
                                                      [-output_format {csv,tar}]
                                                      [-input_format {csv,tsv}]

optional arguments:
  -h, --help            show this help message and exit
  -rules_type {all,forward,retro}
  -rules_file RULES_FILE
  -output OUTPUT
  -diameters DIAMETERS
  -output_format {csv,tar}
  -input_format {csv,tsv}
```

### Retro Pipeline

This runs all three tools and returns the 

```bash
usage: rppipeline [-h] -sink SINK_PATH -source SOURCE_INCHI [-orp RP2_OUTPUT]
                  [-orp2p RP2_PATHS] [-orp2pc RP2_CMPS]
                  [-co COMPRESSED_RESULTS] [-s MAX_STEPS] [-d RR_DIAMETERS]
                  [-rt RR_TYPE] [-rri RR_INPUT_FILE] [-rrf RR_INPUT_FORMAT]
                  [-sn SOURCE_NAME] [-t TOPX] [-dmin MIN_DIMENSION]
                  [-dmax MAX_DIMENSION] [-ms MWMAX_SOURCE] [-mc MWMAX_COF]
                  [-to TIME_OUT] [-r RAM_LIMIT] [-p PARTIAL_RETRO]

Run the retrosynthesis pipeline

optional arguments:
  -h, --help            show this help message and exit
  -sink SINK_PATH, --sink_path SINK_PATH
                        Input sink (organims) molecule
  -source SOURCE_INCHI, --source_inchi SOURCE_INCHI
                        Input (target) Inchi
  -orp RP2_OUTPUT, --rp2_output RP2_OUTPUT
                        RP2 results file
  -orp2p RP2_PATHS, --rp2_paths RP2_PATHS
                        RP2paths pathway results file
  -orp2pc RP2_CMPS, --rp2_cmps RP2_CMPS
                        RP2paths compounds results file
  -co COMPRESSED_RESULTS, --compressed_results COMPRESSED_RESULTS
                        Output TAR with all the intermediate files
  -s MAX_STEPS, --max_steps MAX_STEPS
                        Maximum heterologous pathway length
  -d RR_DIAMETERS, --rr_diameters RR_DIAMETERS
                        Diameters of the reaction rules
  -rt RR_TYPE, --rr_type RR_TYPE
                        The type of retrorules
  -rri RR_INPUT_FILE, --rr_input_file RR_INPUT_FILE
                        RetroRules input file
  -rrf RR_INPUT_FORMAT, --rr_input_format RR_INPUT_FORMAT
                        RetroRules input format
  -sn SOURCE_NAME, --source_name SOURCE_NAME
                        The name of the source
  -t TOPX, --topx TOPX  TopX reaction rule at each iteration
  -dmin MIN_DIMENSION, --min_dimension MIN_DIMENSION
                        Minimal reaction rule dimension
  -dmax MAX_DIMENSION, --max_dimension MAX_DIMENSION
                        Maximal reaction rule dimension
  -ms MWMAX_SOURCE, --mwmax_source MWMAX_SOURCE
                        Max source iteraction
  -mc MWMAX_COF, --mwmax_cof MWMAX_COF
                        Max source coefficient
  -to TIME_OUT, --time_out TIME_OUT
                        Time out
  -r RAM_LIMIT, --ram_limit RAM_LIMIT
                        Ram limit of the execution
  -p PARTIAL_RETRO, --partial_retro PARTIAL_RETRO
                        Ram limit of the execution
```

Example usage:

```
rppipeline -sink sanity_test/sinkfile.csv -source 'InChI=1S/C10H16/c1-7-4-5-8-6-9(7)10(8,2)3/h4,8-9H,5-6H2,1-3H3/t8-,9-/m1/s1' -orp sanity_test/rp2.csv -orp2p sanity_test/rp2paths_p.csv -orp2pc sanity_test/rp2paths_c.csv
```

## Dependencies

* Base docker image: [ubuntu:18.04](https://hub.docker.com/layers/ubuntu/library/ubuntu/18.04/images/sha256-60a99a670b980963e4a9d882f631cba5d26ba5d14ccba2aa82a4e1f4d084fb1f?context=explore)
* [RetroPath2.0](https://www.myexperiment.org/workflows/4987.html)
* [rp2paths](https://github.com/brsynth/rp2paths)
* [RetroRules](https://retrorules.org/)
* [RDKit](https://github.com/rdkit/rdkit)
* [Marvin](https://chemaxon.com/products/marvin)

## Building the docker

Compile the docker image if it hasen't already been done:

```
docker build -t melclic/retrosynthesis:latest .
```

> Note: You need to download the .deb linux version of Marvin as well as a ChemAxon license to be able to run the tool. Please place those at the root of the project folder before building the docker.

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Version

v8.0

## Authors

* **Melchior du Lac**

## License

This project is licensed under the GPL2 License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Thomas Duigou
* Joan Hérisson

### How to cite RetroPath2.0?
Please cite:

Delépine B, Duigou T, Carbonell P, Faulon JL. RetroPath2.0: A retrosynthesis workflow for metabolic engineers. Metabolic Engineering, 45: 158-170, 2018. DOI: https://doi.org/10.1016/j.ymben.2017.12.002

