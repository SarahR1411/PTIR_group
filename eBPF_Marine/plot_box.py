import pandas as pd
import matplotlib.pyplot as plt
import os

# Choix de la variable à tracer
variable = "latency"   # peut être "cpu", "latency" ou "pps"

# Débit constant (en pps) appliqué à tous les targets
RATE = 3000

# Définition des fichiers de mesure de la variable pour chaque cible
if variable == "cpu":
    targets = {
        'usr_space': 'usrspace_prog/var_cpu.csv',
        'xdp':       'cpu_data/cpu_log_simple.csv',
        'xdp_vide':  'cpu_vide_data/cpu_vide_log_simple.csv'
    }
elif variable == "latency":
    targets = {
        'usr_space': 'usrspace_prog/var_latency.csv',
        'xdp':       'latency_data/latency_log.csv',
        'xdp_vide':  'latency_vide_data/latency_vide_log.csv'
    }
elif variable == "pps":
    targets = {
        'usr_space': 'usrspace_prog/var_pps.csv',
        'xdp':       'pps_data/pps_log.csv',
        'xdp_vide':  'pps_vide_data/pps_vide_log.csv'
    }
else:
    raise ValueError(f"Variable inattendue : {variable!r}")

# Chargement de toutes les séries de 'var' en filtrant les zéros
data = []
labels = []
for name, var_path in targets.items():
    df = pd.read_csv(var_path)  # colonnes : timestamp, var
    if 'var' not in df.columns:
        raise KeyError(f"Le fichier {var_path} ne contient pas la colonne 'var'")
    
    # Filtrage : ne garder que les valeurs non nulles
    filtered = df[df['var'] != 0]['var']
    if filtered.empty:
        print(f"[!] Avertissement : aucune valeur non nulle pour '{name}' dans {var_path}")
    data.append(filtered)
    labels.append(name)

# Création du répertoire de sortie
graphs_dir = "graphs"
os.makedirs(graphs_dir, exist_ok=True)

# Tracé en boxplot
plt.figure(figsize=(8, 6))
plt.boxplot(data, labels=labels, showfliers=True, notch=True)
plt.xlabel('Cible')
plt.ylabel(variable)
plt.title(f'Distribution de {variable} à débit constant de {RATE} pps')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()

# Sauvegarde et affichage
output_plot = os.path.join(graphs_dir, f"{variable}_boxplot.png")
plt.savefig(output_plot)
print(f"Box-plot sauvé dans : {output_plot}")
plt.show()
