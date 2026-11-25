---
id: devp2p_overview
label: reference
title: Référence — Couche P2P d'Ethereum (devp2p) et métriques utiles
---
La couche devp2p gère la découverte des pairs, les connexions chiffrées et l'échange de messages (annonces de transactions, requêtes de blocs et d'en-têtes). Les clients exposent des métriques de nombre de pairs, de trafic entrant et sortant et de messages par type. L'API RPC permet de lire le nombre de pairs, l'état de synchronisation et la liste des pairs connectés. Ces mesures, croisées avec les métriques système (CPU, mémoire, réseau), constituent les trois sources de preuves utilisées par EVA-Guard : P2P, système et RPC.
