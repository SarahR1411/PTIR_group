#!/usr/bin/env python3
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
os.makedirs("./latency_data", exist_ok=True)

csv_file = open("./latency_data/latency_log.csv", mode='w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["timestamp", "latency_us"])

def cleanup(signum=None, frame=None):
    print("\n[!] Nettoyage...")
    try:
        if b:
            b.remove_xdp(device)
            print(f"[✓] XDP détaché de {device}")
    except Exception as e:
        print(f"[!] Erreur nettoyage: {e}")
    csv_file.close()
    print("Données enregistrées dans './latency_data/latency_log.csv'")
    sys.exit(0)

def clear_maps():
    b["ip_count_map"].clear()
    b["ip_flood_count_map"].clear()
    b["ip_timestamp_map"].clear()
    b["ip_blacklist_map"].clear()
    b["port_blacklist_map"].clear()
    b["pps"].clear()
    b["latency_map"].clear()
    print("[INFO] Maps eBPF nettoyées")

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    global b
    parser = argparse.ArgumentParser(description="Mesure de la latence réseau en CSV")
    args = parser.parse_args()

    b = BPF(src_file="latency.c")
    fn = b.load_func("xdp_latency", BPF.XDP)
    b.attach_xdp(device, fn, 0)
    clear_maps()
    print(f"XDP attaché à {device}")

    latency_map = b.get_table("latency_map")

    while True:
        time.sleep(1)
        total_latency_ns = 0
        count = 0
        for _, val in latency_map.items():
            total_latency_ns += sum(val)
            count += len(val)
        latency_map.clear()

        # conversion en microsecondes
        latency_us = (total_latency_ns / count) / 1000 if count else 0
        print(f"[INFO] Latence moyenne : {latency_us:.2f} µs")

        ts = int(time.time())
        csv_writer.writerow([ts, f"{latency_us:.2f}"])
        csv_file.flush()

if __name__ == "__main__":
    main()
