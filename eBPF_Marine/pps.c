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


// Seuil de flood
#define MAX_PACKETS 100
#define TIME_WINDOW_NS 5000000000ULL  // 5 seconde

// Fonction helper pour afficher une IP en 2 parties
static __always_inline void log_ip(u32 ip) {
    // Première partie (2 octets)
    bpf_trace_printk("%d.%d", (ip >> 24) & 0xFF, (ip >> 16) & 0xFF);
    // Seconde partie (2 octets)
    bpf_trace_printk(".%d.%d", (ip >> 8) & 0xFF, ip & 0xFF);
}

int xdp_pps(struct xdp_md *ctx) {
    // Mesure pps (=paquets traités par seconde)
    u32 key = 0;
    u64 *value = pps.lookup(&key);
    if (value) {
        __sync_fetch_and_add(value, 1);
    }

    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    // === Analyse Ethernet ===
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return XDP_PASS;

    // === Analyse IP ===
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_PASS;

    // ATTENTION ADDRESSES SOURCES ET DESTINATIONS INVERSEES MAIS JE SAIS PAS POURQUOI !
    u32 src_ip = bpf_ntohl(ip->daddr);
    u32 dest_ip = bpf_ntohl(ip->saddr);

    // Affichage avec séparation claire
    bpf_trace_printk("SRC: ");
    log_ip(src_ip);
    bpf_trace_printk(" DST: ");
    log_ip(dest_ip);
    bpf_trace_printk("\n");


    // === Blacklist IP ===
    u8 *blacklisted = ip_blacklist_map.lookup(&src_ip);
    if (blacklisted && *blacklisted)
        return XDP_DROP;

    // === Compteur et détection flood ===
    u64 *count = ip_count_map.lookup(&src_ip);
    u64 new_count = 1;
    if (count) new_count = *count + 1;
    ip_count_map.update(&src_ip, &new_count);

    u64 *flood_count = ip_flood_count_map.lookup(&src_ip);
    u64 new_flood_count = 1;
    if (flood_count) new_flood_count = *flood_count + 1;
    ip_flood_count_map.update(&src_ip, &new_flood_count);

    u64 now = bpf_ktime_get_ns();
    u64 *last_seen = ip_timestamp_map.lookup(&src_ip);
    if (last_seen) {
        u64 delta = now - *last_seen;
        if (delta < TIME_WINDOW_NS && new_flood_count > MAX_PACKETS) {
            u8 one = 1;
            ip_blacklist_map.update(&src_ip, &one);
            return XDP_DROP;
        } else if (delta >= TIME_WINDOW_NS) {
            // Reset flood_count
            new_flood_count = 1;
            ip_flood_count_map.update(&src_ip, &new_flood_count);
            ip_timestamp_map.update(&src_ip, &now);
        }
    } else {
        ip_timestamp_map.update(&src_ip, &now);
    }

    // === Analyse TCP / UDP ===
    void *l4_hdr = (void *)ip + ip->ihl * 4;
    if (l4_hdr > data_end)
        return XDP_PASS;

    if (ip->protocol == IPPROTO_TCP) {
        struct tcphdr *tcp = l4_hdr;
        if ((void *)(tcp + 1) > data_end)
            return XDP_PASS;

        u16 dport = ntohs(tcp->dest);
        u8 *blocked = port_blacklist_map.lookup(&dport);
        if (blocked && *blocked)
            return XDP_DROP;
    } else if (ip->protocol == IPPROTO_UDP) {
        struct udphdr *udp = l4_hdr;
        if ((void *)(udp + 1) > data_end)
            return XDP_PASS;

        u16 dport = ntohs(udp->dest);
        u8 *blocked = port_blacklist_map.lookup(&dport);
        if (blocked && *blocked)
            return XDP_DROP;
    }

    return XDP_PASS;
}
