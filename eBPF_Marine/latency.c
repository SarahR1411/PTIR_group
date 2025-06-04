#include <uapi/linux/bpf.h>
#include <linux/in.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <asm/byteorder.h> // Pour ntohl()

BPF_HASH(ip_flood_count_map, u32, u64);
BPF_HASH(ip_count_map, u32, u64);
BPF_HASH(ip_timestamp_map, u32, u64);
BPF_HASH(ip_blacklist_map, u32, u8);
BPF_HASH(port_blacklist_map, u16, u8);
BPF_PERCPU_ARRAY(pps, u64, 1);

// Nouvelle map pour mesurer la latence
BPF_PERCPU_ARRAY(latency_map, u64, 2);  // clé 0 : somme latence, clé 1 : compteur

#define MAX_PACKETS 100
#define TIME_WINDOW_NS 5000000000ULL  // 5 secondes

static __always_inline void log_ip(u32 ip) {
    bpf_trace_printk("%d.%d", (ip >> 24) & 0xFF, (ip >> 16) & 0xFF);
    bpf_trace_printk(".%d.%d", (ip >> 8) & 0xFF, ip & 0xFF);
}

int xdp_latency(struct xdp_md *ctx) {
    u64 start = bpf_ktime_get_ns();  // Marquer le temps d'entrée

    u32 key = 0;
    u64 *value = pps.lookup(&key);
    if (value) {
        __sync_fetch_and_add(value, 1);
    }

    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        goto end;

    if (eth->h_proto != bpf_htons(ETH_P_IP))
        goto end;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        goto end;

    u32 src_ip = bpf_ntohl(ip->daddr);
    u32 dest_ip = bpf_ntohl(ip->saddr);

    bpf_trace_printk("SRC: ");
    log_ip(src_ip);
    bpf_trace_printk(" DST: ");
    log_ip(dest_ip);
    bpf_trace_printk("\n");

    u8 *blacklisted = ip_blacklist_map.lookup(&src_ip);
    if (blacklisted && *blacklisted)
        goto drop;

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
            goto drop;
        } else if (delta >= TIME_WINDOW_NS) {
            new_flood_count = 1;
            ip_flood_count_map.update(&src_ip, &new_flood_count);
            ip_timestamp_map.update(&src_ip, &now);
        }
    } else {
        ip_timestamp_map.update(&src_ip, &now);
    }

    void *l4_hdr = (void *)ip + ip->ihl * 4;
    if (l4_hdr > data_end)
        goto end;

    if (ip->protocol == IPPROTO_TCP) {
        struct tcphdr *tcp = l4_hdr;
        if ((void *)(tcp + 1) > data_end)
            goto end;

        u16 dport = ntohs(tcp->dest);
        u8 *blocked = port_blacklist_map.lookup(&dport);
        if (blocked && *blocked)
            goto drop;
    } else if (ip->protocol == IPPROTO_UDP) {
        struct udphdr *udp = l4_hdr;
        if ((void *)(udp + 1) > data_end)
            goto end;

        u16 dport = ntohs(udp->dest);
        u8 *blocked = port_blacklist_map.lookup(&dport);
        if (blocked && *blocked)
            goto drop;
    }

end:
    {
        u64 end = bpf_ktime_get_ns();
        u64 latency = end - start;

        u32 sum_key = 0;
        u32 count_key = 1;

        u64 *sum = latency_map.lookup(&sum_key);
        u64 *cnt = latency_map.lookup(&count_key);
        if (sum && cnt) {
            __sync_fetch_and_add(sum, latency);
            __sync_fetch_and_add(cnt, 1);
        }
    }

    return XDP_PASS;

drop:
    {
        u64 end = bpf_ktime_get_ns();
        u64 latency = end - start;

        u32 sum_key = 0;
        u32 count_key = 1;

        u64 *sum = latency_map.lookup(&sum_key);
        u64 *cnt = latency_map.lookup(&count_key);
        if (sum && cnt) {
            __sync_fetch_and_add(sum, latency);
            __sync_fetch_and_add(cnt, 1);
        }
    }

    return XDP_DROP;
}
