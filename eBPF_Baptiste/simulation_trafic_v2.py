#!/usr/bin/env python3
from scapy.all import send, IP, ICMP, Raw
import time
import random
import threading
import psutil

# Configuration
IP1 = "10.56.16.86"
IP2 = "10.10.4.1"
INTERFACES = ["enp0s3", "enp0s8"]
NORMAL_TRAFFIC_DURATION = 20
ATTACK_DURATION = 5
FLOW_INTERVAL = 0.0001
ATTACK_INTERVAL = 0.1
STATS_INTERVAL = 5

# Statistiques
stats = {
    'ip1_sent': 0,
    'ip2_sent': 0,
    'attacks': 0,
    'current_interface': 0,  # 0 pour enp0s3, 1 pour enp0s8
    'start_time': time.time()
}

def generate_traffic(dest_ip, iface, duration):
    """Génère un flux intense de paquets sur une interface"""
    end_time = time.time() + duration
    
    while time.time() < end_time:
        send(
            IP(dst=dest_ip)/ICMP()/Raw(load=str(time.time()).encode()),
            verbose=0,
            iface=iface
        )
        if dest_ip == IP1:
            stats['ip1_sent'] += 1
        else:
            stats['ip2_sent'] += 1
        time.sleep(FLOW_INTERVAL)

def lateral_movement_attack():
    """Simule une attaque avec trafic simultané sur les deux interfaces"""
    print("\n\033[91m[ATTACK] Début d'une attaque latérale!\033[0m")
    stats['attacks'] += 1
    
    threads = [
        threading.Thread(target=generate_traffic, args=(IP1, INTERFACES[0], ATTACK_DURATION)),
        threading.Thread(target=generate_traffic, args=(IP2, INTERFACES[1], ATTACK_DURATION))
    ]
    
    for t in threads:
        t.start()
    for t in threads:
        t.join()

def monitor_resources():
    """Affiche les statistiques système"""
    while True:
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        elapsed = time.time() - stats['start_time']
        
        print(f"\n[STATS] Temps écoulé: {elapsed:.1f}s")
        print(f"CPU: {cpu}% | Mémoire: {mem}%")
        print(f"Paquets envoyés - IP1: {stats['ip1_sent']} | IP2: {stats['ip2_sent']}")
        print(f"Attaques détectées: {stats['attacks']}")
        time.sleep(STATS_INTERVAL)

def main():
    threading.Thread(target=monitor_resources, daemon=True).start()
    
    try:
        while True:
            # Déterminer l'interface courante
            interface_index = stats['current_interface']
            target_ip = IP1 if interface_index == 0 else IP2
            iface = INTERFACES[interface_index]
            
            print(f"\n\033[92m[PHASE NORMALE] Trafic intense sur {iface}\033[0m")
            
            # Générer le trafic sur une seule interface
            t = threading.Thread(target=generate_traffic, args=(target_ip, iface, NORMAL_TRAFFIC_DURATION))
            t.start()
            
            # 30% de chance de déclencher une attaque pendant la phase normale
            if random.random() < 0.3:
                lateral_movement_attack()
            
            t.join()
            
            # Alterner l'interface pour la prochaine phase
            stats['current_interface'] = (interface_index + 1) % 2
            
    except KeyboardInterrupt:
        print("\nArrêt du générateur de trafic.")
        total_time = time.time() - stats['start_time']
        print(f"\nRécapitulatif final:")
        print(f"Durée totale: {total_time:.1f}s")
        print(f"Total paquets IP1: {stats['ip1_sent']}")
        print(f"Total paquets IP2: {stats['ip2_sent']}")
        print(f"Total attaques: {stats['attacks']}")

if __name__ == "__main__":
    main()