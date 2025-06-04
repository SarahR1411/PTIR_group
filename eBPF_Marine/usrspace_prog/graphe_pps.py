from ddos_user_space import stats_queue, start_detection
import csv
import time

# Configuration
CSV_FILENAME = "var_pps.csv"

# Initialisation du fichier CSV
csv_file = open(CSV_FILENAME, mode='w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['timestamp', 'var'])

# Démarrage de la détection
start_detection()
start_time = time.time()

try:
    while True:
        total_pps, *_ = stats_queue.get()
        current_time = time.time()
        csv_writer.writerow([int(current_time), total_pps])
        csv_file.flush()
        #print(f"[INFO] {int(current_time)}: {total_pps} PPS")
except KeyboardInterrupt:
    csv_file.close()
    print(f"\n[✓] Monitoring arrêté. Données sauvegardées dans '{CSV_FILENAME}'.")
