# Guide — enregistrer des runs réels (réseau privé Kurtosis + collecteur)

Terminal WSL (Ubuntu), dossier du projet. Remplacez P_RPC, P_METRICS et le nom du conteneur par ceux de votre `kurtosis enclave inspect <nom>`.

## 0. Préparation (une fois)
```bash
pip install eth-account                 # pour la charge de test (le collecteur n'a besoin de rien d'autre)
python3 tools/load_gen.py --new-key     # affiche une adresse + une clé PRIVÉE DE TEST
```
Préfinancez cette adresse dans votre réseau de test (paramètre `prefunded_accounts` de `network_params`, voir la doc d'ethereum-package :
non vérifié ici) ou utilisez la clé d'un compte déjà préfinancé indiqué par la doc du package. Jamais de clé réelle.
```bash
export EVA_PRIVATE_KEY=0x...            # la clé de test
docker ps --format '{{.Names}}' | grep el-1     # nom du conteneur du nœud surveillé (ex. el-1-geth-lighthouse--abc123)
```

## 1. Enregistrer les runs (un run = 1000 s ; relancez la commande autant de fois que de runs voulus)
```bash
RPC=http://127.0.0.1:P_RPC ; MET=http://127.0.0.1:P_METRICS/debug/metrics/prometheus ; CT=<nom du conteneur el-1>
python3 tools/run_session.py --profile idle     --rpc $RPC --metrics $MET --container $CT
python3 tools/run_session.py --profile moderate --rpc $RPC --metrics $MET --container $CT
python3 tools/run_session.py --profile high     --rpc $RPC --metrics $MET --container $CT
python3 tools/run_session.py --profile restart  --rpc $RPC --metrics $MET --container $CT
python3 tools/run_session.py --profile burst    --rpc $RPC --metrics $MET --container $CT
```
Chaque commande écrit `results/runs/<run_id>.csv` et ajoute la ligne d'étiquette dans `results/runs/manifest.csv`.
Quantité conseillée : 10 par profil (minimum 6 runs « normal » au total pour la suite). Commencez par 1 run de chaque pour valider.

## 2. Contrôles qualité
```bash
wc -l results/runs/*.csv                         # ~101 lignes par run
python3 -c "import pandas as pd,glob;[print(f, pd.read_csv(f).isna().sum()[lambda s:s>0].to_dict()) for f in glob.glob('results/runs/*.csv') if 'manifest' not in f]"
```
`single_source_ratio` sera vide : c'est attendu (voir ci-dessous).

## 3. Contrôle des fausses alertes sur vos données
```bash
export EVA_DROP_FEATURES=single_source_ratio
python3 -m eva_guard.real_check --manifest results/runs/manifest.csv
# ou avec Docker : docker compose run --rm realcheck
```
Résultat : pour chaque système (ML seul, ML + LLM/RAG, EVA-Guard), la part de runs normaux mis de côté, de redémarrages et de rafales
classés « attaque ». Fichier : `results/runs/real_check.csv`. Le rappel sur de vraies attaques ne peut pas être mesuré sans traces d'attaque
fournies par l'encadrant.

## Points d'attention
- La métrique `p2p_ingress` du collecteur est une hypothèse de nom : si `msgs_in`/`bytes_in` sont vides, envoyez 3 lignes du CSV pour corriger.
- Le CPU/la mémoire viennent de `docker stats` du conteneur (`--container`).
- Le profil `restart` redémarre le conteneur : l'épisode est étiqueté de la fenêtre 40 à 65 (approximation du rattrapage).
- Les débits de charge (2, 8 et 15 tx/s) sont des points de départ ; baissez-les si votre machine sature (`--tps` dans `tools/load_gen.py`).
