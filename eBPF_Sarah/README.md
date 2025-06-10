# Mesures de performance et de détection de malware avec et sans eBPF

---

## Table des matières
1. [Présentation rapide](#1-présentation-rapide)
2. [Arborescence & rôle des fichiers](#2-arborescence--rôle-des-fichiers)
3. [Prérequis](#3-prérequis)
4. [Compilation des workloads](#4-compilation-des-workloads)
5. [Exécution des programmes Python](#5-exécution-des-programmes-Python)  
   5.1. Série 1 : traçage **exhaustif**  
   5.2. Série 2 : traçage **échantillonné**
6. [Personnalisation & extensions](#6-personnalisation--extensions)
7. [Dépannage](#7-dépannage)

---

## 1. Présentation rapide
Ces programmes permettent d’évaluer :

* **l’overhead** introduit par un traçage eBPF pour la détection de malware,
* et l’impact de différentes fréquences d’échantillonnage.

Deux campagnes sont fournies :

| Campagne | Script principal | Description |
|----------|-----------------|-------------|
| **Série 1 : traçage exhaustif** | `monitor_adv.py` | Instrumente **toutes** les entrées & sorties de syscalls ; mesure débit (ops/sec), distribution de latence et overhead.<br>Tests : accès mémoire soupçonneux, fork-bomb, opérations fichier &nbsp;×&nbsp; modes **séquentiel** / **concurrent**.<br>Chaque test : 5 000 itérations × 30 exécutions. |
| **Série 2 : traçage échantillonné** | `monitor2.py` | N’instrumente que `open`, `openat`, `clone`, `write` ; n’attache qu’**1 appel sur N** (N ∈ {1, 2, 5, 10, 20, 50, 100, 200}).<br>Workload varié (CPU, fichiers, fork, scénarios malveillants).<br>Chaque test : 1 000 itérations × 30 exécutions. |

---

## 2. Arborescence & rôle des fichiers
.
├── monitor_adv.py # Campagne « traçage exhaustif »
├── monitor2.py # Campagne « traçage échantillonné »
├── test_app.c # Workload générique multi-types
├── test_app2.c # Micro-tests ciblés (3 scénarios)
└── README.md # Ce document


| Fichier | Rôle détaillé |
|---------|---------------|
| **`monitor_adv.py`** | *Série 1* : trace la totalité des syscalls via un `TRACEPOINT_PROBE` entrée/sortie. Calcule :<br>• **Throughput** (ops/sec)<br>• **Distribution de latence** par syscall<br>• **Overhead** vs baseline.<br>Produit quatre graphes PNG : `throughput_{sequential,concurrent}.png` et `latency_{sequential,concurrent}.png`. |
| **`monitor2.py`** | *Série 2* : active des kprobes sur quatre syscalls clés. Pour chaque taux d’échantillonnage `SAMPLING_RATE`, calcule overhead puis trace un graphe de la surcharge en fonction du taux d'échantillonnage: `no_errorbars.png` (moyenne seule).<br>Variables importantes : `RUNS = 30`, `ITER = 1000`, `RATES = [1,2,5,10,20,50,100,200]`. |
| **`test_app.c`** | Charges CPU (`cpu`), accès fichiers (`file-read`, `file-write`), réseau (`net`), accès mémoire spécial (`suspicious-mem`), fork-flood (`fork`).|
| **`test_app2.c`** | Trois scénarios :<br>`suspicious-mem`, `fork-bomb`, `file-ops`. Peut tourner en mode **séquentiel** ou **concurrent** (processus multiples). |

---

## 3. Prérequis
1. **Linux ≥ 4.4** avec eBPF activé  
   (options : `CONFIG_BPF`, `CONFIG_BPF_SYSCALL`, `CONFIG_KPROBE_EVENTS`, etc.).
2. Paquets : `clang`, `llvm`, `make`, `gcc`.
3. **Python 3.8+** et **bcc** :
   ```bash
   sudo apt install bpfcc-tools python3-bpfcc   # Debian/Ubuntu
   pip install matplotlib
4. L’exécution des scripts nécessite les privilèges root (sudo) pour attacher les probes.

## 4. Compilation des workloads

```
gcc test_app.c  -o test_app
gcc test_app2.c -o test_app2
```

## 5. Exécution des programmes Python 

### 5.1. Série 1 : traçage exhaustif (monitor_adv.py)

```bash
sudo python3 monitor_adv.py
```

**Le script :**

- Lance successivement `./test_app2` en séquentiel puis concurrent pour chaque scénario (`suspicious-mem`, `fork-bomb`, `file-ops`).
- Mesure la baseline (aucune instrumentation) puis le run instrumenté, en collectant la latence via `raw_syscalls:sys_enter/exit`.
- Génère quatre fichiers PNG :
  - `throughput_sequential.png`
  - `throughput_concurrent.png`
  - `latency_sequential.png`
  - `latency_concurrent.png`
- **Throughput** : barres groupées (baseline ↔ instrumenté)
- **Latence** : boxplots (échelle log µs) des 15 syscalls les plus fréquents.

### 5.2. Série 2 : traçage échantillonné (monitor2.py)

```bash
sudo python3 monitor2.py
```

**Pour chaque taux N (1 → 200) :**

- Recompile la sonde eBPF avec `-DSAMPLING_RATE=N`.
- Exécute le workload général (`test_app`) 1 000 fois, répété 30 fois.
- Calcule :
  - **Overhead** : temps instrumenté / temps baseline
- Écrit deux graphes :
  - `with_errorbars.png`   # Moyenne de la surcharge + écart-type
  - `no_errorbars.png`     # Moyenne de la surcharge seule

## 6. Personnalisation & extensions

- **Augmenter la robustesse** : montez `RUNS` ou `ITER` en tête de script.
- **Ajouter un scénario** :
  - Implémentez-le dans `test_app.c` ou `test_app2.c`.
  - Référencez-le dans la liste `tests = [...]` de `monitor2.py` ou `TYPES = [...]` de `monitor_adv.py`.
- **Changer l’échantillonnage** : modifiez la liste `RATES` dans `monitor2.py`.

## 7. Dépannage

| **Symptôme**                          | **Correctif**                                                                 |
|---------------------------------------|-------------------------------------------------------------------------------|
| bcc introuvable                       | `sudo apt install bpfcc-tools python3-bpfcc`                                  |
| libbpf: permission denied             | Exécuter les scripts avec `sudo` (ou `CAP_SYS_ADMIN`).                        |
| Graphes vides / latence 0             | Vérifiez la présence de `raw_syscalls:sys_enter/exit` dans `/sys/kernel/tracing/events`. Activé par défaut depuis Linux 4.14. |
| Erreur unsupported BPF feature        | Le noyau est trop ancien ; recompilez avec un noyau ≥ 4.4 et eBPF activé.     |