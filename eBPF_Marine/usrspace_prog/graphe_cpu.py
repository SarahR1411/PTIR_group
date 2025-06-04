from ddos_user_space import stats_queue, start_detection
import matplotlib.pyplot as plt
import numpy as np
import time

# Configuration
RECENT_STATS_WINDOW = 5    # Fenêtre pour max/min (s)

# Données historiques (conservent tout depuis le début)
timestamps = []
raw_data = []

# --- Configuration du graphique ---
plt.style.use('ggplot')
fig, ax = plt.subplots(figsize=(10, 5))
fig.canvas.manager.set_window_title('CPU Usage Monitor')

# Courbe CPU brute
cpu_line, = ax.plot([], [],
                    color='crimson',
                    linewidth=2.5,
                    alpha=0.9,
                    marker='o',
                    markersize=4,
                    markerfacecolor='white',
                    markeredgecolor='crimson',
                    label='CPU (%)')

# Titres et labels
ax.set_title("Utilisation CPU (%)", pad=15)
ax.set_xlabel("Temps écoulé (s)", labelpad=10)
ax.set_ylabel("CPU (%)", labelpad=10)

# Fixer l'axe Y entre 0 et 120
ax.set_ylim(0, 120)

# Grilles
ax.grid(True, alpha=0.4)                    # grille principale
ax.minorticks_on()
ax.grid(which='minor', linestyle=':', linewidth=0.5, alpha=0.5)

# Légende
ax.legend(loc='upper right', framealpha=1)

# Zone de texte pour stats
stats_text = ax.text(0.02, 0.95, "",
                     transform=ax.transAxes,
                     ha='left', va='top',
                     bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                     fontsize=9)

plt.tight_layout()
plt.ion()

# Démarrage de la détection
start_detection()
start_time = time.time()
last_save = time.time()

def update_axes_limits():
    """Ajuste dynamiquement les bornes X."""
    if not timestamps:
        return

    # Axe X : de 0 au temps courant (au moins 30 s)
    rel = [t - timestamps[0] for t in timestamps]
    max_t = rel[-1]
    ax.set_xlim(0, max(30, max_t))

def update_stats_text():
    """Met à jour le contenu du textbox."""
    if not raw_data:
        return
    now = timestamps[-1]
    # Dernière valeur
    last = raw_data[-1]
    # Max/Min sur la fenêtre récente
    recent_vals = [raw_data[i] for i, t in enumerate(timestamps) if now - t <= RECENT_STATS_WINDOW]
    mx = max(recent_vals) if recent_vals else last
    mn = min(recent_vals) if recent_vals else last

    stats_text.set_text(
        f"Actuel : {last:.2f}%\n"
        f"Max ({RECENT_STATS_WINDOW}s) : {mx:.2f}%\n"
        f"Min ({RECENT_STATS_WINDOW}s) : {mn:.2f}%"
    )

try:
    while True:
        # 1s de pause
        time.sleep(1)

        # Récupération CPU
        *_, cpu = stats_queue.get()
        now = time.time()

        # Historique
        timestamps.append(now)
        raw_data.append(cpu)

        # Mise à jour des courbes
        rel_time = [t - timestamps[0] for t in timestamps]
        cpu_line.set_data(rel_time, raw_data)

        # Ajustement des axes et stats
        update_axes_limits()
        update_stats_text()

        # Redessin et sauvegarde périodique
        fig.canvas.draw_idle()
        if now - last_save > 10:
            plt.tight_layout()
            fig.savefig("cpu_monitor.png", dpi=100, bbox_inches='tight')
            last_save = now

        plt.pause(0.01)

except KeyboardInterrupt:
    plt.tight_layout()
    fig.savefig("cpu_monitor_final.png", dpi=100, bbox_inches='tight')
    print("\nArrêt demandé, graphique final sauvegardé.")
