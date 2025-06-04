#!/bin/bash

# Paramètres
VICTIM_NS="victim"
VICTIM_VETH="veth-victim"
VICTIM_PEER="veth-main"
VICTIM_IP="10.0.0.1"
VICTIM_GW="10.0.0.254"

BOT_COUNT=3
BASE_BOT_NS="bot"
BOT_PREFIX="veth"
TARGET_PORT=80

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# Nettoyage à la fin
cleanup() {
    echo -e "${YELLOW}[*] Nettoyage...${NC}"
    ip netns del "$VICTIM_NS" 2>/dev/null
    ip link del "$VICTIM_PEER" 2>/dev/null

    for i in $(seq 1 $BOT_COUNT); do
        ip netns del "${BASE_BOT_NS}${i}" 2>/dev/null
        ip link del "veth${i}-host" 2>/dev/null
    done
    exit 0
}
trap cleanup SIGINT SIGTERM

# Vérification des dépendances
for cmd in ip hping3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}[!] Erreur : $cmd est requis.${NC}"
        exit 1
    fi
done

# Activer le forwarding IP sur le host
echo 1 > /proc/sys/net/ipv4/ip_forward

# Création namespace victime
echo -e "${YELLOW}[*] Création namespace victime...${NC}"
ip netns add "$VICTIM_NS"

# Création de l'interface veth
ip link add "$VICTIM_VETH" type veth peer name "$VICTIM_PEER"

# Déplacer veth-victim dans le namespace victime
ip link set "$VICTIM_VETH" netns "$VICTIM_NS"

# Configurer la victime
ip netns exec "$VICTIM_NS" ip addr add "$VICTIM_IP/24" dev "$VICTIM_VETH"
ip netns exec "$VICTIM_NS" ip link set "$VICTIM_VETH" up
ip netns exec "$VICTIM_NS" ip link set lo up
ip addr add "$VICTIM_GW/24" dev "$VICTIM_PEER"
ip link set "$VICTIM_PEER" up

# Ajout des routes retour vers chaque bot dans le namespace victim
for i in $(seq 1 $BOT_COUNT); do
    SUBNET="10.0.${i}.0/24"
    ip netns exec "$VICTIM_NS" ip route add "$SUBNET" via "$VICTIM_GW" dev "$VICTIM_VETH"
done

# Désactiver rp_filter dans le namespace victim (évite le drop des réponses)
for iface in all lo veth-victim; do
    ip netns exec "$VICTIM_NS" bash -c "echo 0 > /proc/sys/net/ipv4/conf/$iface/rp_filter"
done

echo -e "${GREEN}[+] Namespace victime prêt (${VICTIM_IP})${NC}"

# Création des namespaces bots
for i in $(seq 1 $BOT_COUNT); do
    NS="${BASE_BOT_NS}${i}"
    VETH_NS="${BOT_PREFIX}${i}"
    VETH_PEER="${BOT_PREFIX}${i}-host"
    BOT_IP="10.0.${i}.2"
    HOST_IP="10.0.${i}.1"

    echo -e "${YELLOW}[*] Création bot $NS...${NC}"
    ip netns add "$NS"
    ip link add "$VETH_NS" type veth peer name "$VETH_PEER"
    ip link set "$VETH_NS" netns "$NS"

    ip netns exec "$NS" ip addr add "$BOT_IP/24" dev "$VETH_NS"
    ip netns exec "$NS" ip link set "$VETH_NS" up
    ip netns exec "$NS" ip link set lo up

    ip addr add "$HOST_IP/24" dev "$VETH_PEER"
    ip link set "$VETH_PEER" up

    ip netns exec "$NS" ip route add 10.0.0.0/24 via "$HOST_IP" dev "$VETH_NS"

    echo -e "${GREEN}[+] Bot $NS prêt (${BOT_IP})${NC}"
done

echo -e "${YELLOW}[✓] Topologie réseau prête. Faire Ctrl+C pour nettoyer. ${NC}"

# Boucle infinie pour garder le script actif jusqu'à Ctrl+C
while true; do
    sleep 1
done
