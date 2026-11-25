# EVA-Guard — Guide complet (Windows 10/11 · PowerShell · Docker)

Toutes les commandes se tapent dans **PowerShell**, dans le dossier du projet (celui qui contient `docker-compose.yml`).
Convention : `py` = Python sous Windows ; `docker compose` = Docker Compose v2.
Les passages marqués **(non vérifié)** n'ont pas pu être testés par l'auteur : signalez toute différence.

---------------------------------------------------------------------------------------------------

## 0. Carte des scénarios

| # | Je veux… | Section |
|---|---|---|
| 1 | Installer et vérifier que tout fonctionne | 1, 2 |
| 2 | Lancer les tests | 3 |
| 3 | Relancer l'évaluation complète (résultats, figures, rapports) | 4 |
| 4 | Ouvrir le dashboard (rejeu, analyse de ma trace, résultats) | 5 |
| 5 | Regénérer les deux rapports PDF | 6 |
| 6 | Mesurer la sensibilité à l'intensité des épisodes simulés | 7 |
| 7 | Démarrer un nœud Geth local et collecter des données réelles | 8 |
| 8 | Enregistrer les runs étiquetés (repos, charge, redémarrage, rafale) | 9 |
| 9 | Contrôler les fausses alertes sur mes runs réels | 10 |
| 10 | Analyser une trace CSV (la mienne, ou fournie par l'encadrant) | 11 |
| 11 | Générer des traces simulées pour une démo | 12 |
| 12 | Utiliser l'interprète Mistral | 13 |
| 13 | Réseau multi-nœuds (Kurtosis) | 14 |
| 14 | Référence des commandes Docker · dépannage · remise à zéro | 15, 16, 17 |

---------------------------------------------------------------------------------------------------

## 1. Prérequis et installation

1. **Docker Desktop** (mode WSL 2) : lancez-le et attendez « Engine running ».
2. *(Optionnel, sans Docker)* **Python 3.12** depuis python.org. Python 3.14 peut manquer de roues scikit-learn : préférez 3.12 ou Docker.
3. Dézippez `eva-guard.zip` dans un dossier **sans parenthèses ni accents** si possible (par ex. `C:\Projets\eva-guard`), puis :

```powershell
cd C:\Projets\eva-guard
docker --version ; docker compose version ; py --version
```

**Deux manières de travailler** (au choix, les résultats sont identiques) :

| | Docker | Python local |
|---|---|---|
| Installation | `docker compose build` (3 min, une fois) | `py -m pip install -r requirements.txt` |
| Exécuter | `docker compose run --rm <service>` | `py <script>` |
| Quand reconstruire | après toute modification du code : `docker compose build` | jamais |

Les dossiers `results/`, `report/` et `dashboard/` sont partagés avec le conteneur : les fichiers produits apparaissent chez vous.

```powershell
# Python local : environnement isolé (recommandé)
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # si "exécution de scripts désactivée" : Set-ExecutionPolicy -Scope Process Bypass
py -m pip install -r requirements.txt
```

## 2. Vérification rapide

```powershell
docker compose build
docker compose run --rm tests         # attendu : 19 passed
```

## 3. Tests

```powershell
docker compose run --rm tests         # Docker
py -m pytest -q tests                 # Python local
```
Les tests couvrent : simulateur, détecteur, RAG, règle de confirmation, collecteur (contre un RPC simulé), générateur de charge, chargeur de runs réels, `real_check`, analyse de traces, chemin observé, import de traces.

## 4. Évaluation complète (≈ 20 min)

```powershell
docker compose run --rm evaluate      # Docker : évaluation 5 graines + figures + dashboard.html + PDF
py run_all.py                         # Python local
py run_all.py --figures               # rapide : régénère figures, cas du dashboard, dashboard.html et rapport principal (sans réévaluer)
```
Sorties : `results/summary.json`, `results/ablation_summary.json`, `results/selected_params.csv`, `results/cases.json`, `results/figures/*.png`,
`dashboard/dashboard.html`, `report/EVA-Guard_Rapport.pdf`. Si `results/sensitivity.csv` n'existe pas, l'étude de sensibilité est lancée automatiquement.

## 5. Dashboard

```powershell
docker compose up dashboard           # puis ouvrir http://localhost:8501   (Ctrl+C pour arrêter)
py -m streamlit run dashboard/app.py  # Python local
start dashboard\dashboard.html        # version statique, sans serveur
```
Le dashboard a quatre onglets :
- **Rejeu des scénarios** : choisissez un cas ; faites glisser la *fenêtre courante* pour rejouer l'incident. Six sous-onglets : détection ML, hypothèse LLM + RAG (avec les fiches citées), preuves et décision (matrice des indicateurs), **chemin observé**, comparaison des trois systèmes, rapport téléchargeable.
- **Analyser une trace (CSV)** : section 11.
- **Résultats** : tableaux et figures de l'évaluation, sensibilité, contrôle sur vos traces réelles.
- **Aide et architecture** : glossaire des métriques et des verdicts.

*Si le cas ne s'affiche pas* : `results/cases.json` manque → `py run_all.py --figures`.

## 6. Rapports PDF

```powershell
py run_all.py --figures                       # rapport principal : report\EVA-Guard_Rapport.pdf
py report/make_diagrams.py                    # schémas du rapport technique
py report/build_tech_report.py                # rapport technique : report\EVA-Guard_Rapport_Technique.pdf
```
Nom de l'encadrant sur les deux couvertures : écrivez-le (une ligne) dans `report\encadrant.txt`, puis relancez les deux scripts.
Section « données réelles » : lue dans `results\runs\real_check.csv` (produit à la section 10).

## 7. Sensibilité à l'intensité (simulée)

```powershell
py -m eva_guard.sensitivity --n 12          # ≈ 1 min ; écrit results\sensitivity.csv et results\figures\sensitivity.png
```
Rappel de chaque système en fonction de l'intensité (0,1 faible → 1,0 forte) d'un épisode **simulé** (niveau métriques, aucun trafic).

## 8. Nœud Geth local + collecte

Le profil `node` démarre : `geth` (mode `--dev`, **un seul nœud isolé, sans pairs**), `prometheus` et un `collector`.

```powershell
docker compose --profile node up -d geth        # démarre seulement le nœud (suffisant pour enregistrer des runs)
docker compose ps                               # le conteneur s'appelle ici eva-guard-geth-1 ; notez son nom exact
docker compose logs -f geth                     # Ctrl+C pour quitter les logs
```

Variables à définir **dans chaque nouvelle fenêtre PowerShell** (elles ne persistent pas) :
```powershell
$RPC = "http://127.0.0.1:8545"
$MET = "http://127.0.0.1:6060/debug/metrics/prometheus"
$CT  = "eva-guard-geth-1"                       # nom lu dans `docker compose ps`
```

Vérifications :
```powershell
Invoke-RestMethod -Uri $RPC -Method Post -ContentType "application/json" -Body '{"jsonrpc":"2.0","id":1,"method":"net_peerCount","params":[]}'
(Invoke-WebRequest -UseBasicParsing $MET).StatusCode      # attendu : 200
(Invoke-WebRequest -UseBasicParsing $MET).Content -split "`n" | Select-String "^p2p_ingress" | Select-Object -First 20
```
`result : 0x0` est normal (aucun pair). Si les métriques sont injoignables, vérifiez que `docker-compose.yml` publie le port `127.0.0.1:6060:6060`, puis `docker compose --profile node up -d --force-recreate geth`.

**Compte de test pour la charge (profils moderate, high, restart, burst)** :
```powershell
py -m pip install eth-account
py tools/load_gen.py --new-key                  # affiche une adresse et une clé PRIVÉE DE TEST (jamais une clé réelle)
py tools/fund_account.py --rpc $RPC --to 0xVOTRE_ADRESSE --eth 100     # finance l'adresse depuis le compte de développement (non vérifié sur toutes versions de Geth)
$env:EVA_PRIVATE_KEY = "0xVOTRE_CLE_DE_TEST"
```
Contrôle : `py tools/load_gen.py --rpc $RPC --profile moderate --duration 20` doit finir avec **0 erreur** ; des erreurs signifient que l'adresse n'est pas financée.

Arrêt : `docker compose --profile node down` (les CSV de `results\` sont conservés).

## 9. Enregistrer des runs étiquetés

Un run = 800 à 1000 s. La collecte produit un peu moins d'une ligne par fenêtre de 10 s : un run de 1000 s donne environ 80 lignes (le chargeur exige ≥ 30 lignes).

```powershell
# un run de chaque, pour valider
py tools/run_session.py --profile idle     --rpc $RPC --metrics $MET --container $CT --duration 300
py tools/run_session.py --profile moderate --rpc $RPC --metrics $MET --container $CT --duration 300
```
| Profil | Ce que fait la commande | Étiquette écrite |
|---|---|---|
| `idle` | rien (repos) | `normal` |
| `moderate` | ≈ 2 transferts/s | `normal` |
| `high` | ≈ 8 transferts/s | `normal` |
| `restart` | `docker restart` du conteneur à la fenêtre 40 | `benign_restart` (début 40, fin 65) |
| `burst` | 15 transferts/s pendant 12 fenêtres à partir de la 40 | `benign_burst` (40 → 52) |

La série complète (3 runs de chaque profil, ≈ 3 h) :
```powershell
Set-ExecutionPolicy -Scope Process Bypass       # si PowerShell bloque le script
.\tools\record_all.ps1                          # options : -Reps 3 -Duration 800 ; essai rapide : -Reps 1 -Duration 300
```
Chaque run ajoute une ligne à `results\runs\manifest.csv`. **Ne lancez jamais deux runs en même temps.**

**Réparer le manifeste** (supprimé, vidé, ou lignes obsolètes) : reconstruit depuis les CSV présents (sauf le sous-dossier `anciens`) :
```powershell
py tools/rebuild_manifest.py
```
Ne modifiez jamais un fichier avec `Import-Csv … | Export-Csv` sur le **même** fichier : il est vidé avant lecture.

## 10. Contrôle des fausses alertes sur vos runs réels

```powershell
py -m eva_guard.real_check --manifest results/runs/manifest.csv
docker compose run --rm realcheck               # équivalent Docker
```
- Les colonnes vides dans la majorité des runs sont retirées automatiquement (`Colonnes vides retirées automatiquement : …`).
- Un run qui a une colonne conservée entièrement vide est **ignoré avec un avertissement** ; un run de moins de 30 lignes aussi.
- Il faut **au moins 6 runs normaux utilisables** (idle + moderate + high).
- Lecture du tableau : pour `normal` et `benign_*`, « taux » = **fausses alertes** ; pour `eclipse` / `dos_p2p` (si vous en ajoutez), « taux » = **rappel**.
- Sortie : `results\runs\real_check.csv` (relu par le dashboard et les deux rapports).

Ranger les anciens runs inutilisables :
```powershell
New-Item -ItemType Directory results\runs\anciens -Force | Out-Null
Move-Item results\runs\idle_20261120_222635.csv results\runs\anciens\      # exemple
py tools/rebuild_manifest.py
```

## 11. Analyser une trace dans le dashboard

1. Ouvrez le dashboard (section 5), onglet **Analyser une trace (CSV)**.
2. Chargez un CSV (colonnes `t` + les 12 métriques ; le bouton « modèle de fichier » donne le format) ou choisissez un run de `results\runs`.
3. Indiquez la nature connue (si vous la connaissez) et la fenêtre de début de l'épisode (sinon −1).
4. Choisissez la référence de comportement normal :
   - **Données simulées** : rapide, mais les niveaux de base d'un vrai nœud diffèrent ;
   - **Mes runs normaux réels** : apprend la baseline sur `results\runs\manifest.csv` (au moins 4 runs normaux utilisables) : recommandé pour des traces réelles.
5. Lisez les six onglets ; le **chemin observé** donne l'ordre d'apparition des effets et la fenêtre de franchissement de chaque indicateur.

**Traces d'attaque fournies par l'encadrant** : mettez-les au format ci-dessus, copiez les CSV dans `results\runs\`, ajoutez une ligne par run dans `manifest.csv`
(`run_type` = `eclipse` ou `dos_p2p`, `onset`/`event_end` = fenêtres de début et de fin), puis lancez `real_check` : pour ces types, « taux » = **rappel**.
Si le format de l'encadrant diffère (pcap, journaux…), envoyez un extrait pour écrire le convertisseur.
Ce projet **ne fournit aucune procédure pour produire des attaques** : seules des traces autorisées et un cadre validé par l'encadrant sont utilisés.

## 12. Traces simulées pour une démo

```powershell
py tools/make_scenarios.py --out results/sim_traces --levels 0.3 0.6 1.0 --n 2
```
Écrit des CSV au format du collecteur (eclipse et dos_p2p à plusieurs intensités, normal, redémarrage, rafale) et un `manifest.csv`.
Chargez-les un par un dans l'onglet « Analyser une trace » (sélecteur « run enregistré » : copiez-les d'abord dans `results\runs`, sans écraser vos vrais runs : utilisez le préfixe `sim_` déjà présent).
Ce sont des **épisodes simulés** (profils du simulateur) : utiles pour la démonstration, pas pour conclure sur un vrai nœud.

## 13. Interprète Mistral (optionnel, non évalué)

```powershell
$env:MISTRAL_API_KEY = "votre_clé"
py tools/try_mistral.py                         # compare l'hypothèse offline et Mistral sur les cas du dashboard
```
Sans clé ou en cas d'erreur réseau, le programme retombe sur l'interprète offline et l'indique (`offline-rag`). Pour l'utiliser dans le pipeline,
remplacez `OfflineInterpreter(retriever)` par `MistralInterpreter(retriever)` (voir `eva_guard/evaluate.py`, classe `Bench`). L'évaluation chiffrée de Mistral reste à faire.

## 14. Réseau multi-nœuds avec Kurtosis (optionnel, non vérifié)

Nécessaire pour avoir de vrais pairs (topologie P2P non triviale).
```powershell
kurtosis run github.com/ethpandaops/ethereum-package --args-file infra/network_params.yaml
kurtosis enclave ls
kurtosis enclave inspect <nom_enclave>          # ports RPC/métriques de chaque nœud
```
Adaptez `$RPC`, `$MET`, `$CT` aux ports et noms affichés, puis reprenez la section 9. Le financement d'un compte de test dépend du package (voir sa documentation) : `tools/fund_account.py` ne s'applique qu'à `geth --dev`.

## 15. Référence Docker

| Besoin | Commande |
|---|---|
| Construire les images | `docker compose build` |
| Reconstruire sans cache | `docker compose build --no-cache` |
| Lancer un service ponctuel | `docker compose run --rm tests` · `evaluate` · `figures` · `realcheck` |
| Lancer en arrière-plan | `docker compose up -d dashboard` |
| Voir ce qui tourne | `docker compose ps` · `docker ps` |
| Suivre les logs | `docker compose logs -f dashboard` |
| Arrêter | `docker compose down` · `docker compose --profile node down` |
| Redémarrer un conteneur | `docker restart eva-guard-geth-1` |
| Shell dans un conteneur | `docker compose run --rm tests sh` |
| Services disponibles | `docker compose config --services` |
| Espace disque | `docker system df` · nettoyage : `docker system prune` (⚠ supprime les images inutilisées) |

Services du fichier : `tests`, `evaluate`, `figures`, `realcheck`, `dashboard`, et (profil `node`) `geth`, `prometheus`, `collector`.
Le code est **copié dans l'image** : après modification d'un fichier `.py`, relancez `docker compose build` (ou `docker compose run --rm --build <service>`).

## 16. Dépannage

| Symptôme | Cause probable | Correction |
|---|---|---|
| `docker: error during connect` | Docker Desktop non démarré | Lancez Docker Desktop, attendez « Engine running » |
| `$RPC` vide / `expected one argument` | Variables PowerShell perdues (nouvelle fenêtre) | Redéfinir `$RPC`, `$MET`, `$CT` (section 8) |
| `FileNotFoundError … results/runs/…csv` | CSV référencé dans le manifeste mais absent | `py tools/rebuild_manifest.py` |
| `EmptyDataError: No columns to parse` (manifeste) | Manifeste vidé | `py tools/rebuild_manifest.py` |
| `la colonne 'X' est vide partout` | Métrique non collectée | Les versions récentes la retirent seules ; sinon `$env:EVA_DROP_FEATURES="X"` |
| `ignoré … colonnes vides` | Ancien run sans `bytes_in`/`net_io` | Refaire le run ou le ranger dans `anciens` |
| `ignoré … lignes (< 30)` | Run trop court | Refaire avec `--duration 800` ou plus |
| `Il faut au moins 6 runs normaux` | Pas assez de runs idle/moderate/high utilisables | Enregistrer d'autres runs |
| `RemoteDisconnected` pendant `restart` | Normal : le nœud redémarre | Aucune action (le générateur de charge reprend seul) |
| `msgs_in` vide | Nom du compteur Prometheus inexact | Voir `Select-String "^p2p_ingress"` (section 8) ; envoyer le résultat pour corriger le collecteur |
| Erreurs à l'envoi des transactions | Adresse de test non financée | `py tools/fund_account.py …` |
| `Select-String` : script bloqué | Politique d'exécution | `Set-ExecutionPolicy -Scope Process Bypass` |
| Dashboard : « cases.json introuvable » | Résultats non générés | `py run_all.py --figures` |
| Port 8501 ou 8545 déjà utilisé | Autre programme | Arrêter l'autre programme ou changer le port dans `docker-compose.yml` |
| `pip install` échoue sur scikit-learn | Python 3.14 | Utiliser Python 3.12 ou Docker |
| Ancien message d'erreur après mise à jour | Fichiers de l'ancienne version | Remplacer tout le dossier `eva_guard\` (garder `results\`) ; Docker : `docker compose build` |

## 17. Remise à zéro

```powershell
Remove-Item results\runs\*.csv                  # supprime TOUS vos runs enregistrés : à n'utiliser qu'après sauvegarde
docker compose down --remove-orphans
docker compose build --no-cache
```
Sauvegarde conseillée avant : `Compress-Archive results\runs sauvegarde_runs.zip`.

## 18. Fichiers importants

| Fichier | Rôle |
|---|---|
| `eva_guard/` | code : simulateur, détecteur, RAG, interprètes, agents, évaluation, analyse de traces |
| `knowledge/*.md` | base de connaissances du RAG (6 fiches) |
| `collectors/collector.py` | collecteur de métriques (RPC, Prometheus, système) |
| `tools/` | `load_gen.py`, `run_session.py`, `record_all.ps1`, `fund_account.py`, `rebuild_manifest.py`, `make_scenarios.py`, `try_mistral.py` |
| `dashboard/app.py` | dashboard interactif · `dashboard.html` version statique |
| `report/` | `build_report.py` (rapport principal), `build_tech_report.py` (rapport technique), `encadrant.txt` |
| `results/` | résultats, figures, `cases.json`, `runs/` (vos données réelles) |
| `docs/` | guides, fiches de lecture des 3 articles, démo, courriel à l'encadrant |
