# Démo (5 minutes)

Avant : `py -m streamlit run dashboard/app.py` (ou ouvrir `dashboard/dashboard.html`, sans serveur).

| Min | Cas | À montrer | Message |
|---|---|---|---|
| 0:00 | Introduction | Schéma de la section 4 du rapport | Le LLM propose, une règle explicite sur des indicateurs observables décide. |
| 0:45 | Eclipse confirmée | Curseur de fenêtre : alerte ML → hypothèse (fiche citée) → indicateurs P2P + retard de synchronisation → CONFIRMÉE → recommandation | Preuves de sources différentes, décision déterministe. |
| 2:00 | DoS P2P confirmé | Messages entrants et CPU qui montent en parallèle ; indicateurs satisfaits | Même chaîne, autre hypothèse. |
| 3:00 | Faux positif écarté | Maintenance légitime / redémarrage : alerte ML, hypothèse « bénin », NON CONFIRMÉE | Le contexte réduit les fausses alertes (0,55 → 0,15 en simulation). |
| 4:00 | Résultats et limites | Tableau section 11, section 13.4 | Confirmation sans gain sur données simulées ; 0 fausse alerte sur traces réelles bénignes ; rappel réel non mesuré. |

Questions probables : pourquoi la confirmation n'améliore pas (13.1) ; ce que valent des données simulées (13.2) ; ce que montre un 0 % sur 3 runs (13.4) ; pourquoi ne pas laisser le LLM décider (eX-NIDS, 3.1).
