#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import subprocess
import statistics
from bcc import BPF
from bcc.syscall import syscall_name
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ————————————————————————————————————————————————
# PARAMÈTRES
# ————————————————————————————————————————————————
RUNS   = 10
ITER   = 5000
BINARY = "./test_app2"
MODES  = ["sequential", "concurrent"]
TYPES  = ["suspicious-mem", "fork-bomb", "file-ops"]

TYPE_COLORS = {
    "suspicious-mem": "#e41a1c",  # rouge
    "fork-bomb":      "#984ea3",  # violet
    "file-ops":       "#4daf4a",  # vert
}
BASELINE_COLOR = "#999999"       # gris pour la baseline
# ————————————————————————————————————————————————

# Programme eBPF : trace toutes les entrées et sorties de syscall

BPF_PROGRAM = r"""
#include <uapi/linux/ptrace.h>
#include <linux/ptrace.h>
struct data_t { u32 id; u64 delta; };
BPF_HASH(start, u64, u64);
BPF_PERF_OUTPUT(events);

TRACEPOINT_PROBE(raw_syscalls, sys_enter) {
    u64 key = bpf_get_current_pid_tgid();
    u64 ts  = bpf_ktime_get_ns();
    start.update(&key, &ts);
    return 0;
}

TRACEPOINT_PROBE(raw_syscalls, sys_exit) {
    u64 key = bpf_get_current_pid_tgid();
    u64 *tsp = start.lookup(&key);
    if (!tsp) return 0;
    u64 delta = bpf_ktime_get_ns() - *tsp;
    struct data_t d = {};
    d.id    = args->id;
    d.delta = delta;
    events.perf_submit(args, &d, sizeof(d));
    start.delete(&key);
    return 0;
}
"""

def measure_baseline():
    """
    Mesure du throughput (ops/sec) sans instrumentation eBPF
    Retourne baseline[mode][type] = ops/sec
    """
    baseline = {m: {} for m in MODES}

    for mode in MODES:
        for t in TYPES:
            times = []
            for _ in range(RUNS):
                t0 = time.time()
                subprocess.call([BINARY, mode, t, str(ITER)])
                times.append(time.time() - t0)
            # ops/sec = ITER / durée moyenne
            baseline[mode][t] = ITER / statistics.mean(times)
            print(f"[baseline] {mode}/{t}: {baseline[mode][t]:.1f} ops/sec")
    return baseline

def measure_instrumented():
    """
    Mesure du throughput instrumenté ET collecte des latences par test type
    Retourne :
      instr[mode][type] = ops/sec
      lats[mode][type]  = { syscall_id: [lat_ms, ...], … }
    """
    instr = {m: {} for m in MODES}
    lats  = {m: {} for m in MODES}

    for mode in MODES:
        for t in TYPES:
            latencies = {}

            # callback pour collecter les latences
            def cb(cpu, data, size):
                d = b["events"].event(data)
                latencies.setdefault(d.id, []).append(d.delta // 1000)

            b = BPF(text=BPF_PROGRAM)
            b["events"].open_perf_buffer(cb)

            times = []
            for _ in range(RUNS):
                p = subprocess.Popen([BINARY, mode, t, str(ITER)])
                start = time.time()
                # on poll tant que le process tourne
                while p.poll() is None:
                    b.perf_buffer_poll(timeout=100)
                # flush final
                b.perf_buffer_poll(timeout=100)
                times.append(time.time() - start)

            instr[mode][t] = ITER / statistics.mean(times)
            lats[mode][t]  = latencies
            print(f"[instr]     {mode}/{t}: {instr[mode][t]:.1f} ops/sec")

    return instr, lats

def plot_throughput(baseline, instr):
    """Génère deux fichiers PNG : throughput_sequential.png et throughput_concurrent.png"""
    for mode in MODES:
        fig, ax = plt.subplots(figsize=(6,4))
        x     = np.arange(len(TYPES))
        width = 0.35

        base_vals  = [baseline[mode][t] for t in TYPES]
        instr_vals = [instr   [mode][t] for t in TYPES]

        # Baseline (gris)
        bars_base = ax.bar(x - width/2, base_vals,
                           width, color=BASELINE_COLOR, label="baseline")

        # Instrumenté (couleur par test type)
        bars_instr = []
        for i, t in enumerate(TYPES):
            b = ax.bar(i + width/2, instr_vals[i],
                       width, color=TYPE_COLORS[t], label=t if i == 0 else "")
            bars_instr.append(b[0])

        # Ajouter les valeurs au-dessus de chaque barre
        def annotate(bars):
            for bar in bars:
                h = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width()/2,  # position X = centre de la barre
                    h + h*0.01,                        # un petit offset au-dessus
                    f"{h:.0f}",                       # format “12345”
                    ha="center", va="bottom", fontsize=8
                )

        annotate(bars_base)
        annotate(bars_instr)

        ax.set_xticks(x)
        ax.set_xticklabels(TYPES, rotation=15)
        ax.set_ylabel("Ops/sec")
        ax.set_title(f"Ops/sec par type de test ({mode})")
        ax.grid(axis='y', linestyle='--', linewidth=0.5, alpha=0.7)

        # Légende
        patches = [mpatches.Patch(color=BASELINE_COLOR, label="baseline")]
        for t in TYPES:
            patches.append(mpatches.Patch(color=TYPE_COLORS[t], label=t))
        ax.legend(handles=patches, loc="upper right")

        plt.tight_layout()
        fn = f"throughput_{mode}.png"
        plt.savefig(fn)
        print(f"→ {fn}")
        plt.clf()


def plot_latencies(lats):
    """Génère deux fichiers PNG : latency_sequential.png et latency_concurrent.png"""
    for mode in MODES:
        # compter la fréquence de chaque syscall par test type
        combined = {}
        counts_by_type = {t: {} for t in TYPES}
        for t in TYPES:
            for sid, lst in lats[mode][t].items():
                counts_by_type[t][sid] = len(lst)
                combined[sid] = combined.get(sid, 0) + len(lst)

        # top 15 syscalls les plus fréquents
        top_sids = [sid for sid,_ in 
                    sorted(combined.items(), key=lambda kv: kv[1], reverse=True)[:15]]

        data   = []
        colors = []
        labels = []
        for sid in top_sids:
            # concaténer toutes les latences de ce sid sur tous les tests
            lst = []
            for t in TYPES:
                lst.extend(lats[mode][t].get(sid, []))
            data.append(lst)
            # attribuer la couleur du test qui a le plus appelé ce sid
            best = max(TYPES, key=lambda t: counts_by_type[t].get(sid, 0))
            colors.append(TYPE_COLORS[best])
            labels.append(syscall_name(sid) or str(sid))

        fig, ax = plt.subplots(figsize=(8,6))
        bplot = ax.boxplot(data, vert=False, patch_artist=True)
        for patch, c in zip(bplot['boxes'], colors):
            patch.set_facecolor(c)
            patch.set_edgecolor('black')

        ax.set_yticklabels(labels)
        ax.set_xscale('log')
        ax.set_xlabel("Latence (µs, log)")
        ax.set_title(f"Distribution des latences (top 15 syscalls) — {mode}")
        ax.grid(axis='x', which='both', linestyle='--', linewidth=0.5, alpha=0.7)

        patches = [mpatches.Patch(color=TYPE_COLORS[t], label=t) for t in TYPES]
        ax.legend(handles=patches, loc="upper right")

        plt.tight_layout()
        fn = f"latency_{mode}.png"
        plt.savefig(fn)
        print(f"→ {fn}")
        plt.clf()

def main():
    baseline, instr, lats = None, None, None

    print("[1/3] Mesure baseline…")
    baseline = measure_baseline()

    print("[2/3] Mesure instrumentée…")
    instr, lats = measure_instrumented()

    print("[3/3] Génération des graphes…")
    plot_throughput(baseline, instr)
    plot_latencies(lats)

    print("\n✓ Tous les graphes ont été générés :")
    print("  • throughput_sequential.png")
    print("  • throughput_concurrent.png")
    print("  • latency_sequential.png")
    print("  • latency_concurrent.png")

if __name__ == "__main__":
    main()
