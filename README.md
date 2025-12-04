# Retrosynthesis

<img width="1438" height="655" alt="image" src="https://github.com/user-attachments/assets/bb968f1e-6158-4044-8a5a-2dbee6dab178" />

This project provides an easier way to run retrosynthetic workflow to search for possible metabolic 
routes between a list of starting molecules (sink) and a target molecule (source).

---

## Dependencies

The pipeline uses the following projects:

- **[rp2paths](https://github.com/brsynth/rp2paths)**: for pathway enumeration.
- **KNIME base image**: [knime/knime:r-4.7.8-738](https://hub.docker.com/layers/knime/knime/r-4.7.8-738/images/sha256-aafd39556d1ed2911f8105aaa71fdcb3e748c575fe70045ac62dd5ff0ba1de69)

---

## Running

The easiest way to run is to install [nextflow](https://www.nextflow.io/) and using the following example command:

```bash
nextflow run retrosynthesis.nf --sink_file test/sinkfile.csv --source_inchi "InChI=1S/C10H16/c1-7-4-5-8-6-9(7)10(8,2)3/h4,8-9H,5-6H2,1-3H3/t8-,9-/m1/s1" -profile docker
```

## Installation

### Using Docker (recommended)

The easiest way to run this pipeline is to pull the prebuilt Docker image:

```bash
docker pull melclic/retrosynthesis:rp-0.1.0
```

### Build Docker locally

Clone this repository and build the Docker image locally:

```bash
docker build -t retrosynthesis:local .
```

---

## Usage

Within the docker you can run the script with:

```bash
python retropipeline.py --sink-file sink.csv --source-inchi "InChI=1S/..." --out-path out_paths.csv
```

Or within your terminal:

```bash
docker run --rm -v $PWD:/data melclic/retrosynthesis:rp-0.1.0 \
  --sink-file /data/sink.csv \
  --source-inchi "InChI=..." \
  --out-path /data/out_paths.csv
```

The simples however is using the nextflow workflow:

```bash
nextflow run retrosynthesis.nf --sink_file ./notebooks/test_rp2/sinkfile.csv --source_inchi "InChI=1S/C6H6O2/c7-5-3-1-2-4-6(5)8/h1-4,7-8H" --max_steps 3
```

---

## Parameters of the retropipeline script

Below is the full list of supported parameters.

- **--sink-file** *(required)*  
  Path to the sink CSV file. The sink defines the target compounds.

- **--source-inchi** *(required)*  
  InChI string of the source compound.

- **--out-path** *(required)*  
  Path where the final `out_paths.csv` file will be written.  

- **--rules-file** *(optional)*  
  Path to a pre-computed rules file.  
  If not given, rules are generated automatically using RRParser.

- **--std-mode** *(default: `H added + Aromatized`)*  
  Standardization mode for molecules. Options:  
  - `H added + Kekulized`  
  - `H added + Aromatized`  
  - `Aromatized (no Hs added)` (not supported; raises error)

- **--max-steps** *(default: `6`)*  
  Maximum number of retrosynthesis steps.

- **--topx** *(default: `1000`)*  
  Top number of rules to retain per iteration.

- **--kexec** *(default: `/usr/local/knime/knime`)*  
  Path to the KNIME executable. Do not change if running in docker.

- **--kinstall** *(default: `/usr/local/knime`)*  
  Path to the KNIME installation directory. Do not change if running in docker.

- **--kver** *(default: `4.7.8`)*  
  KNIME version string. Do not change if running in docker.

- **--diameters** *(default: `2,4,6,8,10,12,14,16`)*  
  Reaction rule diameters used by RRParser (comma-separated string). Use if
  you do not provide a rules file

- **--rule-type** *(default: `all`)*  
  Type of rules to generate. Options:  
  - `all`  
  - `retro`  
  - `forward`
  Use if you do not provide a rules file.

- **--dmin** *(default: `0`)*  
  Minimum rule diameter.

- **--dmax** *(default: `1000`)*  
  Maximum rule diameter.

- **--mwmax-source** *(default: `1000`)*  
  Maximum molecular weight allowed for intermediate compounds.

- **--mwmax-cof** *(default: `1000`)*  
  Molecular weight scaling coefficient.

- **--timeout** *(default: `60`)*  
  Timeout for KNIME execution (minutes).

- **--ram-limit** *(default: `30`)*  
  Virtual memory limit for KNIME (GB).

- **--partial-retro** *(default: `False`)*  
  If enabled, partial results are returned when execution is interrupted or if
  the execution does not complete successfully.

---

## Output

The pipeline produces:

- **out_paths.csv**: final enumerated pathways (main output).

---

## Example

```bash
python retropipeline.py \
  --sink-file sink.csv \
  --source-inchi "InChI=1S/C7H6O2/c8-7(9)6-4-2-1-3-5-6/h1-5H,(H,8,9)" \
  --out-path out_paths.csv \
  --max-steps 8 \
  --topx 1000 \
  --rule-type all
```

---
