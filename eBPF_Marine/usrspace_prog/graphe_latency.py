from ddos_user_space import stats_queue, start_detection
import time
import csv

# Configuration
CSV_FILENAME = "var_latency.csv"

# Préparation du fichier CSV
csv_file = open(CSV_FILENAME, mode='w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['timestamp', 'var'])

# Démarrage de la détection
start_detection()
start_time = time.time()

try:
    while True:
        *_, latency_ms = stats_queue.get()
        latency_us = latency_ms * 1000
        current_time = time.time()

        # Écriture dans le fichier CSV
        csv_writer.writerow([int(current_time), latency_us])
        csv_file.flush()

        #print(f"[INFO] {int(current_time)} : {latency_us:.2f} µs")

except KeyboardInterrupt:
    csv_file.close()
    print(f"\n[✓] Monitoring arrêté. Fichier CSV '{CSV_FILENAME}' sauvegardé.")
