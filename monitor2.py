#!/usr/bin/env python3
import subprocess, time, ctypes, statistics
from bcc import BPF
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ——— PARAMETERS —————
RUNS = 30
ITER = 1000
RATES = [1, 2, 5, 10, 20, 50, 100, 200]

# ——— EMBEDDED eBPF C ————

c_source = r"""
#include <uapi/linux/ptrace.h>
#ifndef SAMPLING_RATE
#define SAMPLING_RATE 1
#endif
BPF_HASH(open_counter_map,   u32, u64);
BPF_HASH(openat_counter_map, u32, u64);
BPF_HASH(clone_counter_map,  u32, u64);
BPF_HASH(detections,         u32, u8);

static inline int is_malicious(const char *f) {
    const char target[] = "/proc/self/mem";
    #pragma unroll
    for (int i = 0; i < sizeof(target)-1; i++)
        if (f[i] != target[i]) return 0;
    return 1;
}

// hook for plain open()
int trace_sys_open(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    const char __user *fn = (const char __user*)PT_REGS_PARM1(ctx);
    u64 *c = open_counter_map.lookup(&pid);
    u64 nc = c ? *c + 1 : 1;
    open_counter_map.update(&pid, &nc);
    if (nc % SAMPLING_RATE == 0) {
        char buf[256];
        if (bpf_probe_read_user_str(buf, sizeof(buf), fn) > 0
            && is_malicious(buf))
            detections.update(&pid, (u8[]){1});
    }
    return 0;
}

// hook for openat()
int trace_openat(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    const char __user *fn = (const char __user*)PT_REGS_PARM2(ctx);
    u64 *c = openat_counter_map.lookup(&pid);
    u64 nc = c ? *c + 1 : 1;
    openat_counter_map.update(&pid, &nc);
    if (nc % SAMPLING_RATE == 0) {
        char buf[256];
        if (bpf_probe_read_user_str(buf, sizeof(buf), fn) > 0
            && is_malicious(buf))
            detections.update(&pid, (u8[]){1});
    }
    return 0;
}

// hook for clone()
int trace_clone(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 *c = clone_counter_map.lookup(&pid);
    u64 nc = c ? *c + 1 : 1;
    clone_counter_map.update(&pid, &nc);
    if (nc % SAMPLING_RATE == 0 && nc > 5)
        detections.update(&pid, (u8[]){1});
    return 0;
}

// no-op for write
int trace_write(struct pt_regs *ctx) {
    return 0;
}
"""

# ——— TEST SUITE ——————
tests = [
    {"type":"cpu",             "malicious":False},
    {"type":"file-read",       "malicious":False},
    {"type":"net",             "malicious":False},
    {"type":"suspicious-mem",  "malicious":True},
    {"type":"fork-flood",      "malicious":True},
    {"type":"mixed",           "malicious":False},
    {"type":"benign-mixed",    "malicious":False},
    {"type":"malicious-mixed", "malicious":True},
]

# map syscall -> probe function
probe_funcs = {
    "open":   "trace_sys_open",
    "openat": "trace_openat",
    "clone":  "trace_clone",
    "write":  "trace_write",
}

# ——— COMPUTE BASELINES (no eBPF) —————
baseline = {}
for t in tests:
    times = []
    for _ in range(RUNS):
        t0 = time.time()
        subprocess.run(
            ["./test_app", t["type"], str(ITER)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        times.append(time.time() - t0)
    baseline[t["type"]] = statistics.mean(times)

# ——— COLLECT RAW RESULTS ———————
raw = []
for rate in RATES:
    # compile & attach all probes
    bpf = BPF(text=c_source,
              cflags=[f"-DSAMPLING_RATE={rate}", "-Wno-macro-redefined"])
    for evt, fn in probe_funcs.items():
        sym = bpf.get_syscall_fnname(evt)
        bpf.attach_kprobe(event=sym, fn_name=fn)

    # run each test RUNS times
    for t in tests:
        for _ in range(RUNS):
            t0 = time.time()
            p = subprocess.Popen(
                ["./test_app", t["type"], str(ITER)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            p.wait()
            dt = time.time() - t0

            m = bpf["detections"]
            key = ctypes.c_uint32(p.pid)
            detected = (key in m and m[key].value != 0)

            # clear maps before next run
            bpf["open_counter_map"].clear()
            bpf["openat_counter_map"].clear()
            bpf["clone_counter_map"].clear()
            m.clear()

            raw.append({
                "rate":      rate,
                "test":      t["type"],
                "malicious": t["malicious"],
                "time":      dt,
                "detected":  detected,
            })

    # detach all probes
    for evt in probe_funcs:
        bpf.detach_kprobe(event=bpf.get_syscall_fnname(evt))

# ——— COMPUTE METRICS ————————
stats = {}
for rate in RATES:
    recs = [r for r in raw if r["rate"] == rate]
    # overheads vs own baseline
    ov = [r["time"] / baseline[r["test"]] for r in recs]
    tp = sum(1 for r in recs if r["malicious"] and   r["detected"])
    fn = sum(1 for r in recs if r["malicious"] and  not r["detected"])
    fp = sum(1 for r in recs if not r["malicious"] and r["detected"])
    tn = sum(1 for r in recs if not r["malicious"] and not r["detected"])
    total = len(recs)

    stats[rate] = {
        "ov_mean":  statistics.mean(ov),
        "ov_std":   statistics.stdev(ov),
        "tp_rate":  tp / (tp + fn) if tp + fn else 0,
        "fp_rate":  fp / (fp + tn) if fp + tn else 0,
        "err_mean": (fn + fp) / total,
        "err_std":  statistics.pstdev([1 if (r["detected"] != r["malicious"]) else 0 for r in recs])
    }

# ——— PRINT TABLE ———————————
print(f"{'Rate':>4}   {'Ovhd±σ':>12}   {'TP%':>5}   {'FP%':>5}   {'Err%±σ':>10}")
for rate in RATES:
    s = stats[rate]
    print(f"{rate:>4}   "
          f"{s['ov_mean']:.2f}±{s['ov_std']:.2f}   "
          f"{100*s['tp_rate']:>4.0f}%   {100*s['fp_rate']:>4.0f}%   "
          f"{100*s['err_mean']:>4.0f}±{100*s['err_std']:>4.0f}%")

# ——— PLOT WITH & WITHOUT ERROR BARS —————————————
rates_x   = RATES
ov_means  = [stats[r]["ov_mean"] for r in rates_x]
ov_stds   = [stats[r]["ov_std"]  for r in rates_x]
err_means = [stats[r]["err_mean"] for r in rates_x]
err_stds  = [stats[r]["err_std"]  for r in rates_x]

# with error bars
plt.figure(figsize=(10,4))
plt.subplot(1,2,1)
plt.errorbar(rates_x, ov_means, yerr=ov_stds, fmt='o-', capsize=5)
plt.title("Overhead vs Sampling Rate (±σ)")
plt.xlabel("Sampling rate (1 in N calls)")
plt.ylabel("Avg overhead ×")
plt.grid(True)

plt.subplot(1,2,2)
plt.errorbar(rates_x, err_means, yerr=err_stds, fmt='o-', capsize=5)
plt.title("Error Rate vs Sampling Rate (±σ)")
plt.xlabel("Sampling rate")
plt.ylabel("Error rate")
plt.grid(True)

plt.tight_layout()
plt.savefig("with_errorbars.png")
print("Saved with_errorbars.png")

# without error bars
plt.figure(figsize=(10,4))
plt.subplot(1,2,1)
plt.plot(rates_x, ov_means, 'o-')
plt.title("Overhead vs Sampling Rate")
plt.xlabel("Sampling rate")
plt.ylabel("Avg overhead ×")
plt.grid(True)

plt.subplot(1,2,2)
plt.plot(rates_x, err_means, 'o-')
plt.title("Error Rate vs Sampling Rate")
plt.xlabel("Sampling rate")
plt.ylabel("Error rate")
plt.grid(True)

plt.tight_layout()
plt.savefig("no_errorbars.png")
print("Saved no_errorbars.png")
