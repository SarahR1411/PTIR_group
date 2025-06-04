# base_detection.py
from scapy.all import sniff, IP, TCP, UDP
from collections import defaultdict
import time
import threading
import queue
import csv
import os
import psutil
import datetime

MAX_PACKETS = 100
TIME_WINDOW = 5

ip_count = defaultdict(int)
ip_flood_count = defaultdict(int)
ip_last_seen = defaultdict(float)
ip_blacklist = set()
port_blacklist = set()

packet_counter = 0
drop_counter = 0
latencies = []
lock = threading.Lock()
stats_queue = queue.Queue()

PER_CPU = False  # ➜ Par défaut, on retourne le CPU global
csv_file = open("userspace_ddos_stats.csv", mode='w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["Timestamp", "PPS", "DropRate", "Latency_ms", "CPU_%"])

def log_ip(ip):
    print(ip, end='')

def packet_handler(pkt):
    global packet_counter, drop_counter

    if not IP in pkt:
        return

    start_time = time.perf_counter()
    src_ip = pkt[IP].src
    if src_ip == "10.0.0.1": # Parce qu'on ne veut pas capturer les réponses de la victime 
        return
    now = time.time()

    #print("SRC: ", end=''); log_ip(src_ip)
    #print()

    with lock:
        packet_counter += 1

    if src_ip in ip_blacklist:
        with lock:
            drop_counter += 1
            latencies.append(time.perf_counter() - start_time)
        return

    ip_count[src_ip] += 1
    ip_flood_count[src_ip] += 1

    if src_ip in ip_last_seen:
        delta = now - ip_last_seen[src_ip]
        if delta < TIME_WINDOW and ip_flood_count[src_ip] > MAX_PACKETS:
            ip_blacklist.add(src_ip)
            with lock:
                drop_counter += 1
                latencies.append(time.perf_counter() - start_time)
            return
        elif delta >= TIME_WINDOW:
            ip_flood_count[src_ip] = 1
            ip_last_seen[src_ip] = now
    else:
        ip_last_seen[src_ip] = now

    dport = None
    if TCP in pkt:
        dport = pkt[TCP].dport
    elif UDP in pkt:
        dport = pkt[UDP].dport

    if dport is not None and dport in port_blacklist:
        with lock:
            drop_counter += 1
            latencies.append(time.perf_counter() - start_time)
        return

    with lock:
        latencies.append(time.perf_counter() - start_time)

def monitor():
    global packet_counter, drop_counter, latencies
    pid = os.getpid()
    p = psutil.Process(pid)

    # Initialise le CPU percent correctement
    psutil.cpu_percent(percpu=True)  # Reset CPU counters

    while True:
        time.sleep(1)
        with lock:
            total = packet_counter
            drops = drop_counter
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            drop_rate = (drops / total * 100) if total else 0

            cpu = psutil.cpu_percent(percpu=True) if PER_CPU else psutil.cpu_percent()
            stats_queue.put((total, drop_rate, avg_latency * 1000, cpu))

            if isinstance(cpu, list):
                csv_writer.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total, drop_rate, avg_latency * 1000] + cpu)
            else:
                csv_writer.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total, drop_rate, avg_latency * 1000, cpu])

            packet_counter = 0
            drop_counter = 0
            latencies = []

def start_detection(per_cpu=False):
    global PER_CPU
    PER_CPU = per_cpu  # Définit si on veut des stats par cœur
    threading.Thread(target=monitor, daemon=True).start()
    threading.Thread(target=lambda: sniff(iface="veth-main", prn=packet_handler, store=0), daemon=True).start()
