# Retrosynthesis docker

Perform retrosynthesis search of possible metabolic routes between a source molecule and a collection of sink molecules. Docker implementation of the KNIME retropath2.0 workflow. Takes for input the minimal (dmin) and maximal (dmax) diameter for the reaction rules and the maximal path length (maxSteps). The docker mounts a local folder and expects the following files: rules.csv, sink.csv and source.csv. We only support a single source molecule at this time. 

## Input

Required:
* **-sinkfile**: (string) Path to the sink file
* **-sourcefile**: (string) Path to the source file
* **-max_steps**: (integer) Maximal number of steps 
* **-rulesfile**: (string) Path to the rules file
* **-rulesfile_format**: (string) Valid Options: tar, csv. Format of the rules file

Advanced options:
* **-topx**: (integer, default: 100) For each iteration, number of rules
* **-dmin**: (integer, default: 0)
* **-dmax**: (integer, default: 1000)
* **-mwmax_source**: (integer, default: 1000)
* **-mwmax_cof**: (integer, default: 1000)
* **-timeout**: (integer, default: 30) Timeout in minutes
* **-server_url**: (string, default: http://0.0.0.0:8888/REST) IP address of the REST service

## Output

* **-scope_csv**: (string) Path to the output scope csv file

## Dependencies

* Base docker image: [ubuntu:18.04](https://hub.docker.com/layers/ubuntu/library/ubuntu/18.04/images/sha256-60a99a670b980963e4a9d882f631cba5d26ba5d14ccba2aa82a4e1f4d084fb1f?context=explore)

## Building the docker

Compile the docker image if it hasen't already been done:

```
docker build -t melclic/retrosynthesis-redis .
```

To run the service on a localhost as the Galaxy interface, after creating the image run the REST service using the following command:

```
docker run -p 8888:8888 melclic/retrosynthesis-redis
```

### Running the test

To test the docker, untar the test.tar.xz file and run the following command:

```
python tool_RetroPath2.py -sinkfile test/sink.csv -sourcefile test/source.csv -rulesfile test/rules.tar -rulesfile_format tar -max_steps 3 -scope_csv test_scope.csv
```

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
