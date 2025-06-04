# Protocole à suivre pour générer les graphiques


Pendant les mesures, **3 onglets de terminal** doivent être ouverts :
- Un pour le **script de configuration** de la topologie réseau
- Un pour le **script Python** qui attache le programme eBPF et recueille les données
- Un pour le **script d'attaque** générant le trafic

---

## Étapes pour mesurer et tracer l'évolution des indicateurs : latency, pps ou cpu

### 1. Lancer la configuration réseau

Dans le dossier principal, exécutez :

```bash
sudo ./setup_topology.sh
```

---

### 2. Choisir un indicateur à mesurer

#### a) Lancer le script Python correspondant

Par exemple, pour la latence :

```bash
sudo python3 latency_vide.py
```

#### b) Lancer l'attaque dans un nouvel onglet

```bash
cd traffic_generation
sudo ./variation_debit.sh
```

#### c) À la fin du script d'attaque (environ 20 minutes)

Arrêter le script Python de collecte des données avec :

```bash
Ctrl + C
```

#### d) Fusionner les timestamps des 10 séries de mesures

Toujours dans le dossier 'traffic_generation' :

```bash
sudo ./merge_debit.sh
```

#### e) Renommer et déplacer le fichier CSV généré

Renommez le fichier en fonction du programme utilisé :
- 'merged_rates_vide.csv'
- 'merged_rates_xdp.csv'
- 'merged_rates_usr.csv'

Puis déplacez-le dans le bon dossier :

```bash
mv merged_rates_<...>.csv traffic_generation/logs/courbes_<variable>/
```

Remplacez '<variable>' par 'latency', 'cpu', ou 'pps'.

---

### 3. Répéter les étapes pour les autres scripts Python

Vous devez exécuter les 3 scripts pour l'indicateur choisi :

Exemple pour la **latence** :

```bash
sudo python3 latency.py
# puis dans un autre onglet :
cd traffic_generation
sudo ./variation_debit.sh
```

```bash
cd usrspace_prog
sudo python3 graphe_latency.py
# puis dans un autre onglet :
cd traffic_generation
sudo ./variation_debit.sh
```

Répétez les étapes **d)** et **e)** à chaque fois.

---

## Génération de la courbe finale

Une fois les trois séries de données collectées et fusionnées :

```bash
sudo python3 plot_courbes.py <variable>
```

Remplacez '<variable>' par latency, pps ou cpu.

Le graphique sera alors **enregistré dans le dossier graphs/** et affiché automatiquement.

---

## Résumé

- 3 scripts de collecte à exécuter pour chaque indicateur
- Fusion et renommage des timestamps après chaque collecte
- Génération finale du graphique avec 'plot_courbes.py'