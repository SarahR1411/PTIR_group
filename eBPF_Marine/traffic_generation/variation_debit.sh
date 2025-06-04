#!/bin/bash

# Script de génération de trafic à débit variable
# Ce script envoie des paquets TCP SYN à une cible (victime)
# Le script effectue 10 répétitions de tests avec la même variation de débit pour chacune

# Paramètres
VICTIM_NS="victim"
VICTIM_IP="10.0.0.1"
BOT_COUNT=3
BASE_BOT_NS="bot"
TARGET_PORT=80
LOG_ROOT="./logs"
REPEAT_COUNT=10
TEST_DURATION=10
SLEEP_BETWEEN=30

RATES=(0 1000 2000 3000 4000 5000 6000 7000 8000 9000 10000)

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

for cmd in ip hping3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}[!] Erreur : $cmd est requis.${NC}"
        exit 1
    fi
done

cleanup() {
    echo -e "${YELLOW}[*] Nettoyage final...${NC}"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null
    done
    exit 0
}
trap cleanup SIGINT SIGTERM

stop_attack() {
    echo -e "${YELLOW}[*] Arrêt de l'envoi en cours...${NC}"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null
    done
    PIDS=()
}

for run in $(seq 1 $REPEAT_COUNT); do
    echo -e "${YELLOW}[RUN $run/$REPEAT_COUNT] Début d'une nouvelle répétition...${NC}"

    RUN_DIR="$LOG_ROOT/run_$(printf '%02d' $run)"
    mkdir -p "$RUN_DIR"
    CSV_FILE="$RUN_DIR/rates.csv"

    echo "timestamp,total_rate" > "$CSV_FILE"

    for RATE in "${RATES[@]}"; do
        TOTAL_RATE=$((BOT_COUNT * RATE))
        echo -e "${GREEN}[*] Envoi à $TOTAL_RATE pps total (${BOT_COUNT} bots à $RATE pps)${NC}"
        PIDS=()

        if [ "$RATE" -eq 0 ]; then
            echo -e "${YELLOW}[*] Pause sans envoi pendant $TEST_DURATION s${NC}"
            START_TIME=$(date +%s)
            for ((i=0; i<TEST_DURATION; i++)); do
                CURRENT_TIME=$((START_TIME + i))
                echo "$CURRENT_TIME,0" >> "$CSV_FILE"
                sleep 1
            done
            continue
        fi

        INTERVAL_US=$((1000000 / RATE))
        TOTAL_PKTS=$((RATE * TEST_DURATION))

        for i in $(seq 1 $BOT_COUNT); do
            NS="${BASE_BOT_NS}${i}"
            ip netns exec "$NS" hping3 -S -p "$TARGET_PORT" --count "$TOTAL_PKTS" --interval "u${INTERVAL_US}" "$VICTIM_IP" > /dev/null 2>&1 &
            PIDS+=($!)
        done

        START_TIME=$(date +%s)
        for ((i=0; i<TEST_DURATION; i++)); do
            CURRENT_TIME=$((START_TIME + i))
            echo "$CURRENT_TIME,$TOTAL_RATE" >> "$CSV_FILE"
            sleep 1
        done

        stop_attack
    done

    echo -e "${YELLOW}[RUN $run] Terminé. Pause de $SLEEP_BETWEEN s avant le prochain run.${NC}"
    sleep "$SLEEP_BETWEEN"
done

echo -e "${GREEN}[✓] Tous les tests ont été effectués.${NC}"
