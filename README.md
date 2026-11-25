# EVA-Guard — détection et confirmation agentiques d'attaques sur nœuds Ethereum

Prototype du mini-projet Blockchain : **observation → détection (ML) → hypothèse (LLM + RAG) → preuves multi-sources → confirmation → explication**.
Le LLM ne confirme jamais seul : il propose une hypothèse ; une règle explicite sur des indicateurs observables décide.

> **À lire d'abord.** Les résultats fournis (`results/`, `report/EVA-Guard_Rapport.pdf`) viennent d'une évaluation sur **télémétrie simulée**
> (séries de métriques, aucun trafic, aucune attaque exécutée). Sur ces données, le contexte LLM/RAG réduit les faux positifs
> (0,55 → 0,15) mais la confirmation multi-sources **n'améliore pas** ML + LLM/RAG. Voir la section 13 du rapport.
> Pour des conclusions valides il faut des traces réelles (voir « Passer aux données réelles »).

## Contenu

```
eva_guard/        code : simulateur, features, détecteur ML, RAG, interprète, agents, évaluation, figures
knowledge/        base RAG (fiches de diagnostic défensif, en français)
collectors/       collecteur réel pour un nœud Geth (RPC + Prometheus + psutil), lecture seule
infra/            réseau privé Kurtosis, config Prometheus, drapeaux Geth (non lancés ici : à valider chez vous)
dashboard/        app Streamlit (rejeu interactif) + dashboard.html autonome
tests/            19 tests (pytest) : simulateur, détecteur, RAG, confirmation, collecteur (RPC simulé), outils de données réelles, dashboard
results/          résultats de l'évaluation (5 graines), figures, cas d'étude
report/           build_report.py -> EVA-Guard_Rapport.pdf
run_all.py        exécute tout : évaluation -> figures -> dashboard -> PDF
```

> **Guide complet Windows / PowerShell / Docker : `docs/GUIDE_COMPLET.md`.** Rapport technique : `report/EVA-Guard_Rapport_Technique.pdf`.

## Installation et exécution

```bash
pip install -r requirements.txt
python -m pytest -q tests                # 19 tests
python run_all.py                        # évaluation complète (~20 min) + figures + dashboard + PDF
python run_all.py --figures              # régénère figures/dashboard/PDF depuis results/ (rapide)
streamlit run dashboard/app.py           # dashboard interactif
open dashboard/dashboard.html            # version sans serveur
```

## Avec Docker (recommandé sous Windows)

```bash
docker compose build
docker compose run --rm tests        # 8 tests
docker compose run --rm evaluate     # évaluation complète (~20 min) -> results/, dashboard/dashboard.html, report/EVA-Guard_Rapport.pdf
docker compose run --rm figures      # régénère figures + dashboard.html + PDF (rapide)
docker compose up dashboard          # dashboard Streamlit : http://localhost:8501
docker compose --profile node up -d  # Geth (mode --dev) + Prometheus + collecteur réel -> results/real_run.csv
```

Les dossiers `results/`, `report/` et `dashboard/` sont montés : les fichiers générés apparaissent chez vous.
Le profil `node` démarre un **nœud Geth unique en mode --dev** (isolé, sans pairs) : il valide la collecte RPC/métriques,
mais les features de topologie P2P (pairs, diversité, churn) restent triviales. Pour un vrai réseau multi-nœuds, utilisez
Kurtosis (`infra/network_params.yaml`). Ces fichiers Docker n'ont pas été exécutés par l'auteur (Docker indisponible dans son environnement) :
signalez toute erreur.

## Données réelles : guide pas à pas

Voir `docs/GUIDE_DONNEES_REELLES.md` : `tools/run_session.py` enregistre et étiquette les runs (idle, moderate, high, restart, burst),
`python -m eva_guard.real_check` mesure les fausses alertes de chaque système sur vos données
(`export EVA_DROP_FEATURES=single_source_ratio` si cette colonne est vide).

## Agents et contrats

| Agent | Fichier | Sortie |
| --- | --- | --- |
| Détection (Isolation Forest + Random Forest) | `eva_guard/detector.py` | `Alert` |
| Interprétation (LLM + RAG) | `eva_guard/llm.py`, `rag.py` | `Hypothesis` |
| Corrélation (catalogue fermé d'indicateurs) | `eva_guard/agents.py` | liste de `Evidence` |
| Confirmation (règle déterministe k / sources / persistance) | `eva_guard/agents.py` | `Decision` |
| Restitution | `eva_guard/agents.py`, `dashboard/` | rapport + recommandation |

Les contrats sont dans `eva_guard/schemas.py`. Les systèmes comparés : `ml_only` (Baseline 1), `ml_llm` (Baseline 2), `eva` (EVA-Guard).

## Interprète LLM

Par défaut, l'interprète **offline** (récupération TF-IDF sur les fiches) est utilisé : reproductible, sans réseau. Pour utiliser Mistral :

```python
from eva_guard.llm import MistralInterpreter   # lit MISTRAL_API_KEY ; repli automatique sur l'offline en cas d'erreur
```

L'interprète Mistral est implémenté mais **n'a pas été évalué** (pas de clé ni de réseau pendant le développement).

## Passer aux données réelles

1. Lancer le réseau privé : `kurtosis run github.com/ethpandaops/ethereum-package --args-file infra/network_params.yaml`
   (adapter les paramètres à la version du package ; non testé ici).
2. Collecter : `python collectors/collector.py --rpc http://127.0.0.1:8545 --metrics http://127.0.0.1:6060/debug/metrics/prometheus --pid <pid geth> --out results/real_run.csv`.
   La feature `single_source_ratio` n'est pas disponible via le RPC standard (colonne vide) : ajoutez un parseur des journaux Geth.
3. Étiqueter chaque run (`run_type`, `onset`, `event_end`) ; les épisodes offensifs se font uniquement dans l'environnement isolé et selon la méthode validée par l'encadrant.
4. Remplacer `generate_dataset` par le chargement de vos CSV dans `eva_guard/evaluate.py` (même schéma de colonnes, voir `eva_guard/config.py`) et relancer.

## Limites connues

- Données simulées ; profils choisis par l'auteur (les recouvrements attaque faible / charge forte sont des hypothèses).
- Fiches RAG et simulateur ont le même auteur : l'écart Baseline 1 → Baseline 2 est probablement optimiste.
- Un épisode et une alerte par run ; pas de dérive de baseline.
- Collecteur et configuration Kurtosis non exécutés contre un vrai nœud dans cet environnement.
- L'étude bibliographique des 3 articles est à compléter par l'équipe (le rapport indique ce qui est attendu).

## Répartition conseillée à 4 (à ajuster)

1. **Infrastructure et données** (Hadil Kharoubi) : `infra/`, `collectors/`, dataset, agent de corrélation.
2. **ML et évaluation** (Baya Sayah) : `features.py`, `detector.py`, `evaluate.py`, figures.
3. **LLM, agents et dashboard** (Mohamed Amine Gharbi) : `knowledge/`, `rag.py`, `llm.py`, confirmation/restitution, `dashboard/`.
4. **Bibliographie, rapport, intégration, démo** (Hedi Gouia) : `report/`, `tests/`, Docker, soutenance.
