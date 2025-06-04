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

static __always_inline void log_ip(u32 ip) {
    bpf_trace_printk("%d.%d", (ip >> 24) & 0xFF, (ip >> 16) & 0xFF);
    bpf_trace_printk(".%d.%d", (ip >> 8) & 0xFF, ip & 0xFF);
}

int xdp_latency_vide(struct xdp_md *ctx) {
    u64 start = bpf_ktime_get_ns();  // Marquer le temps d'entrée

    u32 key = 0;
    u64 *value = pps.lookup(&key);
    if (value) {
        __sync_fetch_and_add(value, 1);
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

}