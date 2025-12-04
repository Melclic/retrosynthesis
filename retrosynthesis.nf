#!/usr/bin/env nextflow
nextflow.enable.dsl=2

/*
 * Minimal Nextflow pipeline: run RetroPath2 pipeline inside Docker
 */

// -------------------------------
// Parameters
// -------------------------------
params.sink_file    = null
params.source_inchi = null
params.rules_file = null

params.std_mode     = "H added + Aromatized"
params.max_steps    = 6
params.topx         = 1000
params.accept_partial_results = false
// --- rules
params.diameters    = "2,4,6,8,10,12,14,16"
params.rule_type    = "all"
params.ram_limit = 15

params.output_folder = "rp2"
params.help = false

process retrosynthesis {
    container "melclic/retrosynthesis:latest"

    publishDir (
        path: { "${params.output_folder}/" },
        mode: "copy", 
        pattern: "*.csv"
    )

    input:
        path sink_file
        val source_inchi
        val accept_partial_results
        path rules_file

    output:
        path "out_paths.csv", emit: out_paths
        path "out_compounds.csv", emit: out_compounds
        path "out_scope.csv", emit: out_scope

    script:
        def partial_flag = accept_partial_results ? "--accept-partial-results" : ""
        def rules_flag = rules_file.getName() == "NONE.rules" ? "" : "--rules-file ${rules_file}"
        """
        python /home/rp2/retropipeline.py \
            --sink-file ${sink_file} \
            --source-inchi "${source_inchi}" \
            --std-mode "${params.std_mode}" \
            --max-steps ${params.max_steps} \
            --topx ${params.topx} \
            --diameters "${params.diameters}" \
            --rule-type "${params.rule_type}" \
            --ram-limit "${params.ram_limit}" \
            ${partial_flag} \
            ${rules_flag} \
            --out-paths out_paths.csv \
            --out-compounds out_compounds.csv \
            --out-scope out_scope.csv
        """
}

def helpMessage() {
    log.info """
╭────────────────────────────────────────────────────────────────────────────╮
│                        RetroPath2 Nextflow Pipeline                        │
╰────────────────────────────────────────────────────────────────────────────╯

DESCRIPTION
    Run a RetroPath2 retrosynthesis pipeline inside a Docker container.

USAGE
    nextflow run main.nf --sink_file <file> --source_inchi <InChI> [options]

REQUIRED PARAMETERS
    --sink_file <path>             Path to sink file (target compounds)
    --source_inchi <string>        Source compound InChI string

OPTIONAL PARAMETERS
    --rules_file <path>            Path to SMARTS rules file (default: none)
    --std_mode <string>            Molecule standardization mode
                                   (default: "H added + Aromatized")
    --max_steps <int>              Maximum retrosynthesis steps (default: 6)
    --topx <int>                   Keep top X results per step (default: 1000)
    --accept_partial_results <bool>Accept incomplete results (default: false)
    --diameters <string>           Comma-separated diameters (default: "2,4,6,8,10,12,14,16")
    --rule_type <string>           Rule selection type (default: "all")
    --ram_limit <int>              Memory limit in GB (default: 15)
    --output_folder <path>         Output folder (default: "rp2")

EXAMPLE
    nextflow run main.nf \\
        --sink_file sinks.csv \\
        --source_inchi "InChI=1S/C7H6O3/c8-5-2-1-3-6(9)7(5)10/h1-3,9-10H" \\
        --rules_file rules.csv \\
        --max_steps 8 \\
        --topx 500

OUTPUTS
    out_paths.csv       Reaction paths between source and sink compounds
    out_compounds.csv   Intermediate and product compound structures
    out_scope.csv       Reachability and transformation scope data

NOTES
    • Runs inside Docker image: melclic/retrosynthesis:rp-0.1.0
    • Published results are saved in the directory specified by --output_folder.
""".stripIndent()
}

// -------------------------------
// Workflow
// -------------------------------
workflow {

    if (params.help || !params.sink_file || !params.source_inchi){
        helpMessage()
        exit 0
    }

    ch_sink_file = channel.fromPath(params.sink_file, checkIfExists: true)
    ch_source_inchi = channel.value(params.source_inchi)
    ch_partial_flag = channel.value(params.accept_partial_results as boolean)
    ch_rules = params.rules_file ? channel.fromPath(params.rules_file) : channel.fromPath("NONE.rules")
    retrosynthesis(ch_sink_file, ch_source_inchi, ch_partial_flag, ch_rules)
}
