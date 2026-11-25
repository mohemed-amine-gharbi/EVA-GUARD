# Étape C — traces d'attaque : option retenue

**Option retenue : obtenir les traces ou la méthode auprès de l'encadrant (jeu de données autorisé ou protocole validé
dans un environnement isolé), et ne rien produire de notre côté sans son accord écrit.**

Pourquoi c'est le meilleur choix :
- C'est la seule qui donne un rappel mesuré sur de vraies données sans risque juridique ni technique (un réseau privé isolé reste de la responsabilité de l'encadrant).
- Elle est rapide à demander (un courriel) et ne bloque pas le reste du travail.
- Si la réponse est « non », le rapport reste valable : il indique déjà que le rappel n'est mesuré que sur données simulées (sections 13.2 et 13.4).

Options écartées : générer nous-mêmes des attaques (hors cadre sans validation) ; chercher des jeux de données publics d'attaques Eclipse/DoS sur Ethereum
(à demander aussi à l'encadrant : il saura s'il en existe d'exploitables ; je n'en ai pas vérifié l'existence).

## Ce qu'on fait des traces quand elles arrivent
1. Les mettre en CSV avec les 12 colonnes du collecteur (`t, peer_count, …, sync_lag`), une ligne par fenêtre de 10 s. Si le format diffère, le convertisseur est à écrire (envoyez-moi un extrait).
2. Ajouter une ligne par run dans `results/runs/manifest.csv` : `run_type` = `eclipse` ou `dos_p2p`, `onset` et `event_end` = fenêtres de début et de fin de l'épisode.
3. `py -m eva_guard.real_check --manifest results/runs/manifest.csv` : pour ces types, la colonne « classes_attaque / taux » se lit comme un **rappel** (part des runs d'attaque détectés),
   alors que pour normal / bénin elle se lit comme un taux de **fausses alertes**.
4. Insérer le tableau dans la section 13.4 du rapport (`py report/build_report.py`).
