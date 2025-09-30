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

// -------------------------------
// Validation
// -------------------------------
if( !params.sink_file )    exit 1, "ERROR: You must provide --sink_file"
if( !params.source_inchi ) exit 1, "ERROR: You must provide --source_inchi"


// -------------------------------
// Process
// -------------------------------
process RETROSYNTHESIS {
    container "melclic/retrosynthesis:rp-0.1.0"


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

// -------------------------------
// Workflow
// -------------------------------
workflow {
    Channel.fromPath(params.sink_file, checkIfExists: true).set { ch_sink_file }
    Channel.value(params.source_inchi).set { ch_source_inchi }
    Channel.value(params.accept_partial_results as boolean).set { ch_partial_flag }
    ch_rules = params.rules_file ? Channel.fromPath(params.rules_file) : Channel.fromPath("NONE.rules")
    retro_ch = RETROSYNTHESIS(ch_sink_file, ch_source_inchi, ch_partial_flag, ch_rules)
}
