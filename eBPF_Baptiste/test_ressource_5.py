#!/usr/bin/env python3
import subprocess
import re
import time
import csv
import psutil
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from threading import Thread, Event

# Configuration
IP = ["10.56.16.86", "10.10.4.1"]
CONDITIONS = ["Avant programme", "Après kernel", "Après userspace"]
PING_COUNT = 200
INTERVAL = 0.1
PAUSE = 40
RESOURCE_INTERVAL = 0.5

# Fichiers de sortie
CSV_LAT_FILE = "latence_data_3.csv"
CSV_RES_FILE = "ressources_data_3.csv"
IMG_FILE = "performance_analysis_3.png"

class ResourceMonitor:
    def __init__(self):
        self.stop_event = Event()
        self.data = []
        
    def collect(self, condition):
        while not self.stop_event.wait(RESOURCE_INTERVAL):
            self.data.append({
                "timestamp": time.time(),
                "condition": condition,
                "cpu": psutil.cpu_percent(),
                "mem": psutil.virtual_memory().percent
            })
    
    def start(self, condition):
        self.stop_event.clear()
        self.thread = Thread(target=self.collect, args=(condition,))
        self.thread.start()
        
    def stop(self):
        self.stop_event.set()
        self.thread.join()

def ping(ip):
    try:
        output = subprocess.run(
            ["ping", "-c", "1", ip], 
            capture_output=True, text=True, timeout=1
        ).stdout
        return float(re.search(r"time=(\d+\.?\d*)", output).group(1))
    except:
        return None

def run_test_phase(condition, resource_monitor):
    print(f"\n=== Début phase {condition} ===")
    resource_monitor.start(condition)
    
    lat_data = {ip: [] for ip in IP}
    for ip in IP:
        print(f"Test IP {ip}")
        for _ in range(PING_COUNT):
            if latency := ping(ip):
                lat_data[ip].append(latency)
                print(f"  {latency:.2f} ms", end='\r')
            time.sleep(INTERVAL)
    
    resource_monitor.stop()
    return lat_data

def save_data(lat_data, res_data):
    with open(CSV_LAT_FILE, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["Condition", "IP", "Latence"])
        for cond, data in lat_data.items():
            for ip in IP:
                for val in data[ip]:
                    writer.writerow([cond, ip, val])
    
    with open(CSV_RES_FILE, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Condition", "CPU", "Mémoire"])
        for entry in res_data:
            writer.writerow(entry.values())

def plot_results(lat_data, res_data):
    plt.figure(figsize=(20, 15))
    
    # Boxplot des latences
    plt.subplot(3, 1, 1)
    positions = [1,2, 4,5, 7,8]
    labels = [f"{ip}\n{cond}" for cond in CONDITIONS for ip in IP]
    
    box_data = []
    for cond in CONDITIONS:
        box_data.extend([lat_data[cond][ip] for ip in IP])
    
    box = plt.boxplot(
        box_data,
        positions=positions,
        patch_artist=True,
        widths=0.6,
        showmeans=True
    )
    
    colors = ['#1f77b480', '#1f77b480', '#ff7f0e80', '#ff7f0e80', '#2ca02c80', '#2ca02c80']
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
    
    plt.title("Distribution des latences par condition")
    plt.xticks(positions, labels)
    plt.ylabel("Latence (ms)")
    plt.grid(axis='y')

    # CPU superposé
    plt.subplot(3, 1, 2)
    for cond in CONDITIONS:
        cond_data = [d for d in res_data if d["condition"] == cond]
        times = [d["timestamp"] - cond_data[0]["timestamp"] for d in cond_data]
        plt.plot(times, [d["cpu"] for d in cond_data], label=cond)
    
    plt.title("Utilisation CPU comparée")
    plt.xlabel("Temps depuis début phase (s)")
    plt.ylabel("CPU (%)")
    plt.legend()
    plt.grid(True)

    # Mémoire
    plt.subplot(3, 1, 3)
    for cond in CONDITIONS:
        cond_data = [d for d in res_data if d["condition"] == cond]
        times = [d["timestamp"] - cond_data[0]["timestamp"] for d in cond_data]
        plt.plot(times, [d["mem"] for d in cond_data], label=cond)
    
    plt.title("Utilisation mémoire")
    plt.xlabel("Temps depuis début phase (s)")
    plt.ylabel("Mémoire (%)")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.savefig(IMG_FILE, dpi=150)
    print(f"\nRapport généré : {IMG_FILE}")

def main():
    resource_monitor = ResourceMonitor()
    lat_data = {}
    
    input("Prêt pour la phase initiale ? Appuyez sur Entrée...")
    lat_data[CONDITIONS[0]] = run_test_phase(CONDITIONS[0], resource_monitor)
    
    print(f"\n=== Pause ({PAUSE}s) - Lancez le programme kernel ===")
    time.sleep(PAUSE)
    
    input("\nPrêt pour la phase kernel ? Appuyez sur Entrée...")
    lat_data[CONDITIONS[1]] = run_test_phase(CONDITIONS[1], resource_monitor)
    
    print(f"\n=== Pause ({PAUSE}s) - Lancez le programme userspace ===")
    time.sleep(PAUSE)
    
    input("\nPrêt pour la phase userspace ? Appuyez sur Entrée...")
    lat_data[CONDITIONS[2]] = run_test_phase(CONDITIONS[2], resource_monitor)
    
    save_data(lat_data, resource_monitor.data)
    plot_results(lat_data, resource_monitor.data)

if __name__ == "__main__":
    main()