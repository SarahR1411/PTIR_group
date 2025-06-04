import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# Vérification des arguments
if len(sys.argv) != 2:
    print("Usage: python script.py [cpu|latency|pps]")
    sys.exit(1)

variable = sys.argv[1].lower()
if variable not in ["cpu", "latency", "pps"]:
    print("Erreur : variable invalide. Choisir entre 'cpu', 'latency' ou 'pps'.")
    sys.exit(1)

# Définition des chemins selon la variable
if variable == "cpu":
    targets = {
        'usr_space': {
            'rates': 'traffic_generation/logs/courbes_cpu/merged_rates_usr.csv',
            'var':   'usrspace_prog/var_cpu.csv'
        },
        'xdp': {
            'rates': 'traffic_generation/logs/courbes_cpu/merged_rates_xdp.csv',
            'var':   'cpu_data/cpu_log.csv'
        },
        'xdp_vide': {
            'rates': 'traffic_generation/logs/courbes_cpu/merged_rates_vide.csv',
            'var':   'cpu_vide_data/cpu_vide_log.csv'
        }
    }

elif variable == "latency":
    targets = {
        'usr_space': {
            'rates': 'traffic_generation/logs/courbes_latency/merged_rates_usr.csv',
            'var':   'usrspace_prog/var_latency.csv'
        },
        'xdp': {
            'rates': 'traffic_generation/logs/courbes_latency/merged_rates_xdp.csv',
            'var':   'latency_data/latency_log.csv'
        },
        'xdp_vide': {
            'rates': 'traffic_generation/logs/courbes_latency/merged_rates_vide.csv',
            'var':   'latency_vide_data/latency_vide_log.csv'
        }
    }

elif variable == "pps":
    targets = {
        'usr_space': {
            'rates': 'traffic_generation/logs/courbes_pps/merged_rates_usr.csv',
            'var':   'usrspace_prog/var_pps.csv'
        },
        'xdp': {
            'rates': 'traffic_generation/logs/courbes_pps/merged_rates_xdp.csv',
            'var':   'pps_data/pps_log.csv'
        },
        'xdp_vide': {
            'rates': 'traffic_generation/logs/courbes_pps/merged_rates_vide.csv',
            'var':   'pps_vide_data/pps_vide_log.csv'
        }
    }

# Fusion et chargement des données
df_list = []
for name, paths in targets.items():
    rates_df = pd.read_csv(paths['rates'])
    var_df = pd.read_csv(paths['var'])
    merged = pd.merge(rates_df, var_df, on='timestamp', how='inner')
    merged['target'] = name
    df_list.append(merged)

df_all = pd.concat(df_list, ignore_index=True)

output_csv = f"merged_data_{variable}.csv"
df_all.to_csv(output_csv, index=False)
print(f"Merged data saved to {output_csv}")

# Moyenne et écart-type
agg = (
    df_all
    .groupby(['target', 'total_rate'])['var']
    .agg(['mean', 'std'])
    .reset_index()
)
agg.rename(columns={'mean': 'var_mean', 'std': 'var_std'}, inplace=True)
agg['var_std'] = agg['var_std'].fillna(0)

# Tracé
plt.figure(figsize=(8, 6))
for target in agg['target'].unique():
    subset = agg[agg['target'] == target]
    plt.errorbar(
        subset['total_rate'],
        subset['var_mean'],
        yerr=subset['var_std'],
        marker='o',
        capsize=5,
        label=target
    )

plt.xlabel("Débit d'envoi de paquets")
plt.ylabel(f'Utilisation {variable} (%)')
plt.title(f"Évolution de l'utilisation {variable} (%) en fonction du débit de paquets")
plt.legend()
plt.grid(True)
plt.tight_layout()

os.makedirs("graphs", exist_ok=True)
output_plot = os.path.join("graphs", f"{variable}.png")
plt.savefig(output_plot)
print(f"Plot saved to {output_plot}")
plt.show()
