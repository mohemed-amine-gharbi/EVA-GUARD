"""Configuration centrale d'EVA-Guard : schéma des features, sources, catalogues d'indicateurs."""

import os

WINDOW_S = 10          # durée d'une fenêtre d'observation (secondes)
RUN_LEN = 100          # nombre de fenêtres par run (≈ 16,7 min)
SMOOTH = 3             # lissage par moyenne glissante (fenêtres)

# Features collectées par fenêtre, et leur source
_ALL_FEATURES = [
    "peer_count", "peer_churn", "peer_diversity", "single_source_ratio", "msgs_in", "bytes_in",
    "cpu", "mem", "net_io",
    "rpc_latency", "rpc_error", "sync_lag",
]
# Pour les données réelles : EVA_DROP_FEATURES="single_source_ratio" retire une feature absente du collecteur
_DROP = {f.strip() for f in os.environ.get("EVA_DROP_FEATURES", "").split(",") if f.strip()}
FEATURES = [f for f in _ALL_FEATURES if f not in _DROP]
SOURCE = {
    "peer_count": "P2P", "peer_churn": "P2P", "peer_diversity": "P2P",
    "single_source_ratio": "P2P", "msgs_in": "P2P", "bytes_in": "P2P",
    "cpu": "SYS", "mem": "SYS", "net_io": "SYS",
    "rpc_latency": "RPC", "rpc_error": "RPC", "sync_lag": "RPC",
}
DESCRIPTION = {
    "peer_count": "nombre de pairs connectés",
    "peer_churn": "connexions/déconnexions de pairs par minute",
    "peer_diversity": "diversité des pairs (ratio de sous-réseaux /16 distincts)",
    "single_source_ratio": "part des nouveaux blocs reçus en premier du même pair",
    "msgs_in": "messages P2P entrants par seconde",
    "bytes_in": "débit P2P entrant (ko/s)",
    "cpu": "utilisation CPU du processus (%)",
    "mem": "utilisation mémoire (%)",
    "net_io": "débit réseau total (Mb/s)",
    "rpc_latency": "latence d'une requête RPC de sonde (ms)",
    "rpc_error": "taux d'erreurs/timeouts RPC",
    "sync_lag": "retard de hauteur de bloc par rapport au réseau",
}

ATTACKS = ["eclipse", "dos_p2p"]

# Catalogue FERMÉ d'indicateurs par hypothèse : (feature, direction)
# direction "high" : preuve si la valeur dépasse le seuil haut de la baseline ; "low" : sous le seuil bas.
_CATALOG_FULL = {
    "eclipse": [
        ("peer_diversity", "low"),
        ("single_source_ratio", "high"),
        ("peer_churn", "high"),
        ("sync_lag", "high"),
        ("peer_count", "low"),
    ],
    "dos_p2p": [
        ("msgs_in", "high"),
        ("cpu", "high"),
        ("mem", "high"),
        ("rpc_latency", "high"),
        ("rpc_error", "high"),
    ],
}

CATALOG = {a: [(f, d) for f, d in items if f not in _DROP] for a, items in _CATALOG_FULL.items()}

# Hyperparamètres par défaut (re-sélectionnés sur le jeu de validation dans l'évaluation)
DEFAULT_RULE = {"k": 3, "min_sources": 2, "persistence": 3}
CONFIRM_TIMEOUT = 8    # fenêtres d'attente maximales après l'alerte
ALERT_CONSEC = 2       # fenêtres consécutives au-dessus du seuil pour lever l'alerte
