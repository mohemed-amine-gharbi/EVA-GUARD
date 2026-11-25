---
id: restart_resync
label: benign_restart
title: Fiche — Redémarrage du nœud et resynchronisation (comportement légitime)
---
Après un redémarrage, un nœud reconstruit sa liste de pairs puis rattrape les blocs manquants. C'est un comportement normal et attendu.

Symptômes observables : très peu de pairs au début puis remontée progressive, churn de pairs élevé, retard de synchronisation qui décroît, blocs reçus d'un seul pair au début, diversité des pairs très faible ou instable (mesure peu fiable quand il y a peu de pairs), flux de messages élevé et CPU élevé pendant le rattrapage, aucune erreur RPC, mémoire stable.
Signe distinctif : tous les indicateurs reviennent à la normale en quelques dizaines de secondes à quelques minutes, sans intervention.
Conclusion habituelle : pas d'attaque. Vérifier les journaux de démarrage pour confirmer le redémarrage.
