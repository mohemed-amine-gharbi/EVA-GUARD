---
id: dos_p2p
label: dos_p2p
title: Fiche diagnostic — Déni de service par flooding de messages P2P
---
Un déni de service par flooding P2P épuise les ressources d'un nœud en lui faisant traiter un volume de messages bien supérieur à la normale. Le nœud devient lent puis indisponible.

Symptômes observables : flux de messages extrême, CPU saturé, mémoire en hausse continue, latence RPC extrême, erreurs RPC nombreuses, churn de pairs élevé, léger retard de synchronisation. Les signes s'aggravent pendant la durée de l'épisode et touchent plusieurs sources (P2P, système, RPC).
Diagnostic différentiel : une rafale légitime de transactions ou une synchronisation volontaire donne aussi un flux de messages élevé et du CPU élevé, mais l'effet reste modéré, la mémoire reste stable et il n'y a pas d'erreurs RPC.
Preuves à rechercher : messages entrants par seconde, CPU, mémoire, latence RPC, taux d'erreurs RPC, sur plusieurs fenêtres consécutives.
Réponse recommandée : limiter le débit par pair, déconnecter les pairs les plus bruyants, appliquer des quotas sur le nombre de messages, surveiller la mémoire, redémarrer proprement si le nœud est saturé.
