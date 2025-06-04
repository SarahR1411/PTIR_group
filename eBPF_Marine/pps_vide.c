#include <uapi/linux/bpf.h>
#include <linux/in.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <asm/byteorder.h> // Pour ntohl()

// Maps pour traquer les IPs, timestamps, blacklists et ports bloqués
BPF_HASH(ip_flood_count_map, u32, u64); // valeur = nombre de paquets reçus en l'espace d'une seconde
BPF_HASH(ip_count_map, u32, u64); // valeur = nombre total de paquets envoyés par cette ip
BPF_HASH(ip_timestamp_map, u32, u64);
BPF_HASH(ip_blacklist_map, u32, u8);
BPF_HASH(port_blacklist_map, u16, u8);
BPF_PERCPU_ARRAY(pps, u64, 1);


int xdp_pps_vide(struct xdp_md *ctx) {
    // Mesure pps (=paquets traités par seconde)
    u32 key = 0;
    u64 *value = pps.lookup(&key);
    if (value) {
        __sync_fetch_and_add(value, 1);
    }

    return XDP_PASS;
}
