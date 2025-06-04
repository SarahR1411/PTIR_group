# graphe_cpu_2.py
from ddos_user_space import stats_queue, start_detection
import csv
import time

CSV_FILENAME = "var_cpu.csv"
SAMPLE_INTERVAL = 1  # en secondes

def main():
    # Démarrage de la collecte CPU en mode global
    start_detection(per_cpu=False)

    # Initialisation du CSV
    with open(CSV_FILENAME, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['timestamp', 'var'])

        print("Collecte de l'utilisation CPU globale. Appuyez sur Ctrl+C pour arrêter.")
        try:
            while True:
                # Récupère la dernière valeur CPU globale (float)
                *_, cpu_value = stats_queue.get()
                ts = int(time.time())
                # Écriture dans le CSV
                writer.writerow([ts, f"{cpu_value:.2f}"])
                csv_file.flush()

                # Pause avant le prochain échantillon
                time.sleep(SAMPLE_INTERVAL)

        except KeyboardInterrupt:
            print(f"\nArrêt demandé. CSV sauvegardé dans : {CSV_FILENAME}")

if __name__ == "__main__":
    main()
