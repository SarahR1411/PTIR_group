import threading
import time
import psutil
import signal
from bcc import BPF
import sys
import csv
import ctypes as ct
import os

# Configuration
UPDATE_INTERVAL = 1  # Intervalle de mise à jour (secondes)
DEVICE = "veth-main"
LOG_DIR = "./cpu_data"
SIMPLE_CSV = os.path.join(LOG_DIR, "cpu_log.csv")

# Préparation du répertoire
os.makedirs(LOG_DIR, exist_ok=True)

# Initialisation BPF
bpf = BPF(src_file="cpu_monitor.c")
fn = bpf.load_func("xdp_cpu", BPF.XDP)
bpf.attach_xdp(DEVICE, fn, 0)

# Structures pour la communication BPF
class IPLog(ct.Structure):
    _fields_ = [("src_ip", ct.c_uint32),
                ("dst_ip", ct.c_uint32)]

# Variables globales
running = True
start_time = time.time()

# Initialisation des deux CSV
simple_file = open(SIMPLE_CSV, mode='w', newline='')
simple_writer = csv.writer(simple_file)

cpu_count = psutil.cpu_count()
# En‑têtes
simple_writer.writerow(["timestamp", "var"])

def process_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(IPLog)).contents
    #print(f"IP Source: {event.src_ip}, IP Dest: {event.dst_ip}")

def monitor_cpu_usage():
    """Boucle d'échantillonnage CPU every second."""
    global start_time
    start_time = time.time()

    while running:
        cpu_percpu = psutil.cpu_percent(interval=1, percpu=True)
        total_cpu  = sum(cpu_percpu) / len(cpu_percpu)
        ts = int(time.time())

        simple_writer.writerow([ts, total_cpu])

def cleanup(signum=None, frame=None):
    global running
    running = False

    print("\n[!] Nettoyage en cours…")
    bpf.remove_xdp(DEVICE)

    simple_file.close()

    print(f"XDP détaché de {DEVICE}")
    print("Données sauvegardées dans :")
    print("   -", SIMPLE_CSV)
    sys.exit(0)

# Signaux pour CTRL+C
signal.signal(signal.SIGINT,  cleanup)
signal.signal(signal.SIGTERM, cleanup)

# Lancement de la boucle BPF
bpf["events"].open_perf_buffer(process_event)

# Thread de monitoring CPU
cpu_thread = threading.Thread(target=monitor_cpu_usage, daemon=True)
cpu_thread.start()

print(f"[*] Monitoring XDP sur {DEVICE}… Ctrl+C pour arrêter")

try:
    while running:
        bpf.perf_buffer_poll()
except KeyboardInterrupt:
    pass
finally:
    cleanup()
