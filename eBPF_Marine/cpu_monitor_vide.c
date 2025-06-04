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


int xdp_cpu_vide(struct xdp_md *ctx) {
    u32 cpu = bpf_get_smp_processor_id();
    pps_map.increment(cpu);
    return XDP_PASS;
}
