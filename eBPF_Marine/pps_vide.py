from bcc import BPF
import time
import signal
import sys
import argparse
import csv
import os

device = "veth-main"
b = None

# Création du dossier pour les logs CSV
os.makedirs("./pps_vide_data", exist_ok=True)

csv_file = open("./pps_vide_data/pps_vide_log.csv", mode='w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["timestamp", "var"])

def cleanup(signum=None, frame=None):
    print("\n[!] Nettoyage...")
    try:
        if b:
            b.remove_xdp(device)
            print(f"[✓] XDP détaché de {device}")
    except Exception as e:
        print(f"[!] Erreur nettoyage: {e}")
    csv_file.close()
    print("Données enregistrées dans './pps_vide_data/pps_vide_log.csv'")
    sys.exit(0)

def clear_maps():
    b["ip_count_map"].clear()
    b["ip_flood_count_map"].clear()
    b["ip_timestamp_map"].clear()
    b["ip_blacklist_map"].clear()
    b["port_blacklist_map"].clear()
    b["pps"].clear()
    print("[INFO] Maps eBPF nettoyées")

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    global b

    parser = argparse.ArgumentParser(description="Mesure PPS XDP")
    parser.add_argument("--avg", type=int, default=5, help="")
    args = parser.parse_args()

    b = BPF(src_file="pps.c")
    fn = b.load_func("xdp_pps", BPF.XDP)
    b.attach_xdp(device, fn, 0)
    clear_maps()
    print(f"Programme XDP attaché à {device}")

    counter = b.get_table("pps")
    key = 0

    print("Mesure du nombre de paquets traités par seconde :\n")

    while True:
        time.sleep(1)
        total = 0
        for cpu_val in counter[key]:
            total += cpu_val
        #print(f"{total} paquets/s")
        del counter[key]

        ts = int(time.time())
        csv_writer.writerow([ts, total])

if __name__ == "__main__":
    main()
