#include <uapi/linux/bpf.h>
#include <linux/in.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <asm/byteorder.h>
#include <linux/smp.h> // Pour bpf_get_smp_processor_id()

// Déclaration de structure pour l'export d'IP
struct ip_log_t {
    u32 src_ip;
    u32 dst_ip;
};

// Maps dynamiques
BPF_HASH(ip_flood_count_map, u32, u64); // Compteur de flood par IP
BPF_HASH(ip_count_map, u32, u64);       // Compteur total par IP
BPF_HASH(ip_timestamp_map, u32, u64);   // Timestamps par IP
BPF_HASH(ip_blacklist_map, u32, u8);    // Blacklist IP
BPF_HASH(port_blacklist_map, u16, u8);  // Blacklist ports
BPF_HASH(pps_map, u32, u64);            // Compteur dynamique par CPU

// Canal pour exporter les événements IP
BPF_PERF_OUTPUT(events);

// Seuils de configuration
#define MAX_PACKETS 100
#define TIME_WINDOW_NS 5000000000ULL // 5 secondes

int xdp_cpu(struct xdp_md *ctx) {
    u32 cpu = bpf_get_smp_processor_id();
    pps_map.increment(cpu);

    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    if (eth->h_proto != bpf_htons(ETH_P_IP))
        return XDP_PASS;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_PASS;

    u32 src_ip = bpf_ntohl(ip->saddr);
    u32 dst_ip = bpf_ntohl(ip->daddr);

    // Export vers l’espace utilisateur
    struct ip_log_t log_entry = {};
    log_entry.src_ip = src_ip;
    log_entry.dst_ip = dst_ip;
    events.perf_submit(ctx, &log_entry, sizeof(log_entry));

    // Vérification blacklist
    u8 *blacklisted = ip_blacklist_map.lookup(&src_ip);
    if (blacklisted && *blacklisted)
        return XDP_DROP;

    // Détection de flood
    u64 now = bpf_ktime_get_ns();
    u64 *last_seen = ip_timestamp_map.lookup(&src_ip);
    u64 *flood_count = ip_flood_count_map.lookup(&src_ip);

    if (!flood_count) {
        u64 init_count = 1;
        ip_flood_count_map.update(&src_ip, &init_count);
        ip_timestamp_map.update(&src_ip, &now);
        return XDP_PASS;
    }

    u64 new_count = *flood_count + 1;
    ip_flood_count_map.update(&src_ip, &new_count);

    if (last_seen && (now - *last_seen) < TIME_WINDOW_NS) {
        if (new_count > MAX_PACKETS) {
            u8 one = 1;
            ip_blacklist_map.update(&src_ip, &one);
            return XDP_DROP;
        }
    } else {
        new_count = 1;
        ip_flood_count_map.update(&src_ip, &new_count);
        ip_timestamp_map.update(&src_ip, &now);
    }

    // Analyse couche 4
    void *l4_hdr = (void *)ip + ip->ihl * 4;
    if (l4_hdr > data_end)
        return XDP_PASS;

    u16 dport = 0;
    if (ip->protocol == IPPROTO_TCP) {
        struct tcphdr *tcp = l4_hdr;
        if ((void *)(tcp + 1) > data_end)
            return XDP_PASS;
        dport = bpf_ntohs(tcp->dest);
    } else if (ip->protocol == IPPROTO_UDP) {
        struct udphdr *udp = l4_hdr;
        if ((void *)(udp + 1) > data_end)
            return XDP_PASS;
        dport = bpf_ntohs(udp->dest);
    }

    if (dport) {
        u8 *blocked = port_blacklist_map.lookup(&dport);
        if (blocked && *blocked)
            return XDP_DROP;
    }

    return XDP_PASS;
}
