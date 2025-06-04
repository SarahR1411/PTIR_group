#!/bin/bash

LOG_ROOT="./logs"
OUTPUT_FILE="$LOG_ROOT/merged_rates.csv"

# Initialiser le fichier de sortie
echo "run_id,timestamp,total_rate" > "$OUTPUT_FILE"

# Fusion des fichiers rates.csv
for run_dir in "$LOG_ROOT"/run_*; do
    [ -d "$run_dir" ] || continue

    run_id=$(basename "$run_dir" | cut -d'_' -f2)
    csv_file="$run_dir/rates.csv"

    if [ -f "$csv_file" ]; then
        tail -n +2 "$csv_file" | while IFS=',' read -r timestamp total_rate; do
            echo "$run_id,$timestamp,$total_rate" >> "$OUTPUT_FILE"
        done

        # Supprimer le fichier rates.csv après fusion
        rm -f "$csv_file"
    fi
done

echo "Fichier fusionné créé : $OUTPUT_FILE"
echo "Tous les fichiers rates.csv ont été supprimés."
