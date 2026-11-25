---
id: eclipse
label: eclipse
title: Fiche diagnostic — Eclipse Attack (isolement P2P d'un nœud)
---
Une Eclipse Attack désigne la situation où un nœud Ethereum se retrouve entouré presque uniquement de pairs contrôlés par un même acteur. Le nœud perd sa vue indépendante du réseau.

Symptômes observables : diversité des pairs très faible, blocs reçus d'un seul pair, churn de pairs élevé au début de l'épisode, nombre de pairs normal (toutes les connexions restent occupées, mais par les mêmes acteurs), retard de synchronisation qui augmente avec le temps.
Indicateurs qui ne bougent presque pas : CPU normal, mémoire stable, latence RPC normale, aucune erreur RPC, flux de messages normal.

Diagnostic différentiel : un redémarrage du nœud donne aussi un churn élevé et un retard de synchronisation, mais le nombre de pairs est alors très faible au début et remonte progressivement ; dans une Eclipse le nombre de pairs reste normal.
Preuves à rechercher : diversité des pairs, part des blocs provenant d'un même pair, churn, retard de synchronisation, nombre de pairs.
Réponse recommandée : isoler le nœud, ajouter des pairs de confiance (bootnodes/static peers), vérifier la hauteur de chaîne auprès d'une source indépendante, ne pas valider de transactions tant que la vue réseau n'est pas rétablie.
