#!/usr/bin/env python3
import os
import socket
import struct
import datetime
from collections import defaultdict
from bcc import BPF
from pyroute2 import IPRoute

interfaces = ["enp0s3", "enp0s8"]
ALERT_THRESHOLD = 0.5  # 500 ms en secondes

# Structure de suivi : {ip: {"last_machine": str, "last_timestamp": float}}
ip_history = defaultdict(lambda: {
    "last_machine": None,
    "last_timestamp": None
})

interface_labels = {
    "enp0s3": "interface 1",
    "enp0s8": "interface 2"
}

infected_ips = {
    "154.1.168.192": True,
    "47.11.168.192": True
}
"""
infected_ips = {
    "86.16.56.10": True,
    "1.4.10.10": True
}
"""
bpf_c = """
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/pkt_cls.h>

struct packet_info_t {
    u32 src_ip;
    u32 ifindex;
    u64 timestamp;
};

BPF_PERF_OUTPUT(events);

static void handle_packet(void *ctx, void *data, void *data_end, u32 ifindex) {
    struct ethhdr *eth = data;
    if ((void*)(eth + 1) > data_end) return;
    if (eth->h_proto != htons(ETH_P_IP)) return;

    struct iphdr *ip = (struct iphdr*)(eth + 1);
    if ((void*)(ip + 1) > data_end) return;

    struct packet_info_t pkt = {};
    pkt.src_ip = ip->saddr;
    pkt.ifindex = ifindex;
    pkt.timestamp = bpf_ktime_get_ns();
    events.perf_submit(ctx, &pkt, sizeof(pkt));
}

int xdp_prog(struct xdp_md *ctx) {
    handle_packet(ctx, (void*)(long)ctx->data, (void*)(long)ctx->data_end, ctx->ingress_ifindex);
    return XDP_PASS;
}

int tc_ingress(struct __sk_buff *skb) {
    handle_packet(skb, (void*)(long)skb->data, (void*)(long)skb->data_end, skb->ifindex);
    return TC_ACT_OK;
}
"""

b = BPF(text=bpf_c)
ipr = IPRoute()
idx2name = {link["index"]: link.get_attr("IFLA_IFNAME") for link in ipr.get_links()}

for iface in interfaces:
    if iface not in idx2name.values():
        print(f"[!] Interface {iface} introuvable, ignoree.")
        continue
    
    try:
        b.attach_xdp(iface, b.load_func("xdp_prog", BPF.XDP), 0)
        print(f"[+] XDP attache sur {iface}")
    except:
        b.attach_tc(iface, fn=b.load_func("tc_ingress", BPF.SCHED_CLS), priority=1, direction="ingress")
        print(f"[+] TC attache sur {iface}")

print("Surveillance active. Ctrl-C pour arreter.")

def check_lateral_movement(ip, current_machine, current_ts):
    if ip == "47.11.168.192":
        ip = "154.1.168.192"
    #print ("C'est quoi ip history ? ", ip_history)
    history = ip_history[ip]
    #print ("machine courante : ", ip, current_machine, current_ts)
    #print ("ancienne machine", history)

    
    if history["last_machine"] and history["last_machine"] != current_machine:
        #print ("Coucou")
        time_diff = abs(current_ts - history["last_timestamp"])
        
        if time_diff <= ALERT_THRESHOLD:
            alert = (
                f"[ALERTE] Mouvement latéral detecté! {ip} a contacté "
                f"{history['last_machine']} puis {current_machine} "
                f"en {time_diff:.3f}s"
            )
            print(f"\n\033[91m{alert}\033[0m\n")
            return True
    
    # Mise à jour de l'historique
    history["last_machine"] = current_machine
    history["last_timestamp"] = current_ts
    #print ("Nouveau history : ", history)
    return False

def handle_event(cpu, data, size):
    evt = b["events"].event(data)
    ip = socket.inet_ntoa(struct.pack("!I", evt.src_ip))
    ts = evt.timestamp / 1e9  # Conversion en secondes
    tstr = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    iface_name = idx2name.get(evt.ifindex, str(evt.ifindex))
    machine_label = interface_labels.get(iface_name, iface_name)
    
    # Vérification et alerte
    is_infected = "[machine infectée]" if ip in infected_ips else ""
    
    if is_infected == "[machine infectée]":    # Vérification mouvement latéral
        #print ("Je checke le latéral")
        #print (ip_history)
        check_lateral_movement(ip, machine_label, ts)
    
    print(f"Paquet de {ip} {is_infected} reçu à {tstr} sur {machine_label}")

b["events"].open_perf_buffer(handle_event)

try:
    while True:
        b.perf_buffer_poll()
except KeyboardInterrupt:
    print("\nArret demande, nettoyage...")
    for iface in interfaces:
        try:
            b.remove_xdp(iface, 0)
        except:
            b.detach_tc(iface, direction="ingress")
    print("Nettoyage termine.")