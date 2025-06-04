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


# === Test 3 : UDP Flood ===

# POUR VERIFIER PAQUETS : DANS TERMINAL : sudo ip netns exec victim tcpdump -i veth-victim udp port 53

#UDP est un protocole sans connexion (ne répond jamais) → il n’y a aucune réponse attendue.
#hping3 n’affiche pas les paquets envoyés, seulement les réponses.
#Donc pas de "paquet reçu" ≠ échec, c’est simplement silencieux.
#A regarder avec programme python et maps xdp

echo -e "${YELLOW}[3/5] Test : DDoS UDP flood (port 53)${NC}"
PIDS=()
for i in $(seq 1 $BOT_COUNT); do
    NS="${BASE_BOT_NS}${i}"
    ip netns exec "$NS" hping3 --udp --flood -p 53 "$VICTIM_IP" > "$LOG_DIR/udp_flood_${NS}.log" 2>&1 &
    PIDS+=($!)
done
sleep "$TEST_DURATION"
stop_attack



echo -e "${GREEN}[✓] Test 3 terminé."
