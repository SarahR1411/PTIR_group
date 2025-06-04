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
    echo -e "${YELLOW}[*] Arrêt de l'attaque en cours...${NC}"
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

# === Test 1 : Trafic normal (TCP ping) ===

echo -e "${YELLOW}[1/5] Test : Trafic normal (packets légitimes)${NC}"
for i in $(seq 1 $BOT_COUNT); do
    NS="${BASE_BOT_NS}${i}"
    ip netns exec "$NS" hping3 -c 5 -S -p "$TARGET_PORT" "$VICTIM_IP" 2>&1 | while read -r line; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line" | tee -a "$LOG_DIR/test1.log"
done
done
sleep 2

sleep "$TEST_DURATION"
stop_attack

echo -e "${GREEN}[✓] Le test 1 est terminé."
