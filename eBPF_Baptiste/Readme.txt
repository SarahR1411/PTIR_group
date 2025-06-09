Pour pouvoir lancer le code : 
Avoir deux VMs, avec deux interfaces réseau chacune (accès par pont sur VirtualBox pour que ça fonctionne, 
et mettre deux interfaces communes, interface 1 et interface deux même pont pour les deux VMs).
Mettre des IPs sur chacune des interfaces si ce n'est pas fait (la configuration de base est 10.10.4.1/24 et 10.10.3.52/24 pour la VM qui reçoit le trafic, 
et 10.10.4.2 et 10.10.3.53 pour la VM qui envoie et analyse le trafic)
_______Attention ! _________________
Remplacer les IPs dans chacun des codes par les IPs de la VM2 de votre machine (attention, pour al_interface_v2, il faut écrire l'IP en commençant par la fin)

Lancer un des scripts d'analyse (al_interfaces_v2.py ou test_user_space.py) ou/et les scripts de génération de trafic 
(ping l'une des IP de la VM2 génère aussi du trafic)
