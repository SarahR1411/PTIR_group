from scapy.all import ICMP, IP, sr1, Raw
import time

#ip1 = "10.56.16.86"  # enp0s3 de VM2
#ip2 = "10.10.4.1"    # enp0s8 de VM2

ip1 = "192.168.1.154"  # enp0s3 de VM2
ip2 = "192.168.11.47"    # enp0s8 de VM2

def send_ping(dest_ip, iface):
    timestamp = time.time()
    # Spécifier l'interface d'émission avec 'iface'
    pkt = IP(dst=dest_ip)/ICMP()/Raw(load=str(timestamp).encode())
    resp = sr1(pkt, timeout=2, verbose=0, iface=iface)
    if resp:
        print(f"Réponse reçue de {dest_ip} via {iface}: time={resp.time - pkt.sent_time:.3f}s")
    else:
        print(f"Aucune réponse de {dest_ip} via {iface}")

def main():
    while True:
        send_ping(ip1, 'enp0s3')  # Utilise enp0s3 pour VM2.enp0s3
        send_ping(ip2, 'enp0s8')  # Utilise enp0s8 pour VM2.enp0s8
        time.sleep(10)

if __name__ == "__main__":
    main()