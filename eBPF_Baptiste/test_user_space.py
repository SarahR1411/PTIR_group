#!/usr/bin/env python3
import time
import socket
import threading
from collections import defaultdict
from scapy.all import sniff, IP, Ether
from threading import Thread, Event
from datetime import datetime

# Configuration
INTERFACES = ["enp0s3", "enp0s8"]
ALERT_THRESHOLD = 0.5

# Structures de suivi
ip_history = defaultdict(lambda: {
    "last_machine": None,
    "last_timestamp": None
})

interface_labels = {
    "enp0s3": "interface 1",
    "enp0s8": "interface 2"
}

infected_ips = {
    "10.56.16.86": True,
    "10.10.4.1": True
}

class TrafficSniffer:
    def __init__(self, interface, stop_event):
        self.interface = interface
        self.stop_event = stop_event
        self.lock = threading.Lock() 


#Détermine si c'est un mouvement latéral ou pas
    def check_lateral_movement(self, ip, current_machine, current_ts):
        with self.lock:
            if ip == "10.10.4.1":
                ip = "10.56.16.86"
                
            history = ip_history[ip]
            
            if history["last_machine"] and history["last_machine"] != current_machine:
                time_diff = abs(current_ts - history["last_timestamp"])
                
                if time_diff <= ALERT_THRESHOLD:
                    alert = (
                        f"[ALERTE] Mouvement latéral détecté! {ip} a contacté "
                        f"{history['last_machine']} puis {current_machine} "
                        f"en {time_diff:.3f}s"
                    )
                    print(f"\n\033[91m{alert}\033[0m\n")
                    return True
            
            history["last_machine"] = current_machine
            history["last_timestamp"] = current_ts
            return False

# Imprime la liste des paquets qui sont relevés
    def packet_handler(self, packet):
        if IP in packet:
            src_ip = packet[IP].src
            timestamp = time.time()
            iface = self.interface
            
            machine_label = interface_labels.get(iface, iface)
            is_infected = "[machine infectée]" if src_ip in infected_ips else ""
            
            if is_infected:
                self.check_lateral_movement(src_ip, machine_label, timestamp)
            
            tstr = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"Paquet de {src_ip} {is_infected} reçu à {tstr} sur {machine_label}")

    def start(self):
        sniff(
            iface=self.interface,
            prn=self.packet_handler,
            store=False,
            stop_filter=lambda _: self.stop_event.is_set()
        )

def main():
    stop_event = Event()
    sniffers = []
    
    # Démarrer les sniffers sur chaque interface
    for iface in INTERFACES:
        sniffer = TrafficSniffer(iface, stop_event)
        thread = Thread(target=sniffer.start)
        thread.daemon = True
        thread.start()
        sniffers.append(thread)
    
    try:
        print("Surveillance active. Ctrl-C pour arrêter.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nArrêt demandé...")
        stop_event.set()
        
        for thread in sniffers:
            thread.join(timeout=5)
        
        print("Nettoyage terminé.")

if __name__ == "__main__":
    main()