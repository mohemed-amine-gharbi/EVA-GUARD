"""Simulateur de télémétrie de nœud Ethereum (séries temporelles statistiques).

IMPORTANT : ce module génère uniquement des *métriques* simulées (valeurs numériques par fenêtre de 10 s).
Il n'émet aucun trafic réseau et n'implémente aucune attaque. Il sert à développer et évaluer la chaîne
de détection/confirmation tant que des traces réelles (collectées sur le réseau privé du projet, ou fournies
par l'encadrant) ne sont pas disponibles. Les profils sont des modèles simplifiés écrits à partir des
symptômes décrits dans le cahier des charges ; ils ne remplacent pas des mesures réelles.
"""
import numpy as np
import pandas as pd
from .config import FEATURES, RUN_LEN

RUN_TYPES = ["normal", "eclipse", "dos_p2p", "benign_restart", "benign_burst", "benign_maintenance"]
ATTACK_TYPES = ["eclipse", "dos_p2p"]


def _ar1(rng, n, phi=0.6):
    e = rng.normal(0, 1, n)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + np.sqrt(1 - phi ** 2) * e[i]
    return x


def _baseline(rng, n):
    load = rng.choice([0.7, 1.0, 1.4])
    off = lambda: rng.normal(0, 0.4)  # décalage propre au run
    x = {}
    x["peer_count"] = np.clip(np.round(48 + off() * 2 + 2 * _ar1(rng, n)), 0, 50)
    x["peer_churn"] = np.clip(2.0 + off() * 0.5 + 1.0 * _ar1(rng, n), 0, None)
    x["peer_diversity"] = np.clip(0.85 + off() * 0.02 + 0.04 * _ar1(rng, n), 0.05, 1)
    x["single_source_ratio"] = np.clip(0.15 + off() * 0.02 + 0.05 * _ar1(rng, n), 0, 1)
    x["msgs_in"] = np.clip(120 * load * (1 + off() * 0.05) + 18 * load * _ar1(rng, n), 1, None)
    x["bytes_in"] = np.clip(800 * load * (1 + off() * 0.05) + 120 * load * _ar1(rng, n), 1, None)
    x["cpu"] = np.clip(18 + 10 * load + off() * 1.5 + 3 * _ar1(rng, n), 1, 100)
    x["mem"] = np.clip(40 + off() * 2 + 1.0 * _ar1(rng, n, 0.95), 5, 100)
    x["rpc_latency"] = np.clip(25 * (0.9 + 0.2 * load) + 4 * _ar1(rng, n), 5, None)
    x["rpc_error"] = np.clip(0.005 + 0.003 * _ar1(rng, n), 0, None)
    x["sync_lag"] = rng.poisson(0.3, n).astype(float)
    return x


def _net_io(x, rng):
    n = len(x["bytes_in"])
    x["net_io"] = np.clip(x["bytes_in"] * 0.008 + 0.4 * rng.normal(0, 1, n), 0.1, None)


def _ramp(n, t0, dur, width=3):
    t = np.arange(n)
    w = np.clip((t - t0 + 1) / width, 0, 1)
    w[t >= t0 + dur] = 0
    return w


def _apply(x, kind, t0, dur, rng, intensity=None):
    n = len(x["cpu"])
    t = np.arange(n)
    s = np.clip(t - t0, 0, None).astype(float)
    active = (t >= t0) & (t < t0 + dur)
    w = _ramp(n, t0, dur)
    if kind == "eclipse":
        a = rng.uniform(0.4, 1.0) if intensity is None else float(intensity)
        x["peer_diversity"] = np.clip(x["peer_diversity"] - w * a * 0.5 * rng.uniform(0.8, 1.2), 0.08, 1)
        x["single_source_ratio"] = np.clip(x["single_source_ratio"] + w * a * 0.55, 0, 1)
        x["peer_churn"] = x["peer_churn"] + w * a * (5 * np.exp(-s / 6) + 1.5)
        x["peer_count"] = np.clip(x["peer_count"] - w * a * 3, 0, 50)
        x["sync_lag"] = x["sync_lag"] + w * a * 0.25 * s
        x["cpu"] = x["cpu"] + w * a * 2
    elif kind == "dos_p2p":
        a = rng.uniform(0.4, 1.0) if intensity is None else float(intensity)
        x["msgs_in"] = x["msgs_in"] * (1 + w * a * 5)
        x["bytes_in"] = x["bytes_in"] * (1 + w * a * 3.5)
        x["cpu"] = np.clip(x["cpu"] + w * a * 40, 0, 100)
        x["mem"] = np.clip(x["mem"] + w * np.minimum(a * 0.6 * s, 30), 0, 100)
        x["rpc_latency"] = x["rpc_latency"] * (1 + w * a * 5)
        x["rpc_error"] = x["rpc_error"] + w * a * 0.12
        x["peer_churn"] = x["peer_churn"] + w * a * 2
        x["sync_lag"] = x["sync_lag"] + w * a * 2
    elif kind == "benign_restart":
        e = lambda tau: np.exp(-s / tau) * active
        x["peer_count"] = np.where(active, np.clip(48 * (1 - np.exp(-s / 6)) + rng.normal(0, 2, n), 0, 50), x["peer_count"])
        x["peer_churn"] = x["peer_churn"] + 6 * e(5)
        x["sync_lag"] = x["sync_lag"] + 12 * e(7)
        x["cpu"] = np.clip(x["cpu"] + 18 * e(6), 0, 100)
        x["msgs_in"] = x["msgs_in"] * (1 + 1.0 * e(6))
        x["bytes_in"] = x["bytes_in"] * (1 + 1.5 * e(8))
        x["single_source_ratio"] = np.clip(x["single_source_ratio"] + 0.35 * e(6), 0, 1)
        noisy = active & (s < 8)
        x["peer_diversity"] = np.where(noisy, np.clip(rng.normal(0.8, 0.08, n), 0.3, 1), x["peer_diversity"])
    elif kind == "benign_burst":
        g = w
        x["msgs_in"] = x["msgs_in"] * (1 + g * rng.uniform(0.6, 1.6))
        x["bytes_in"] = x["bytes_in"] * (1 + g * rng.uniform(0.4, 1.0))
        x["cpu"] = np.clip(x["cpu"] + g * rng.uniform(8, 20), 0, 100)
        x["rpc_latency"] = x["rpc_latency"] * (1 + g * rng.uniform(0.5, 1.5))
        x["mem"] = np.clip(x["mem"] + g * rng.uniform(0, 2), 0, 100)
        x["rpc_error"] = x["rpc_error"] + g * rng.uniform(0, 0.01)
    elif kind == "benign_maintenance":
        g = w
        x["bytes_in"] = x["bytes_in"] * (1 + g * rng.uniform(1.5, 3.0))
        x["msgs_in"] = x["msgs_in"] * (1 + g * rng.uniform(0.8, 1.8))
        x["cpu"] = np.clip(x["cpu"] + g * rng.uniform(15, 30), 0, 100)
        x["mem"] = np.clip(x["mem"] + g * rng.uniform(4, 10), 0, 100)
        x["rpc_latency"] = x["rpc_latency"] * (1 + g * rng.uniform(1.5, 3.5))
        x["rpc_error"] = x["rpc_error"] + g * rng.uniform(0, 0.04)
    return active


DUR = {"eclipse": (35, 45), "dos_p2p": (35, 45), "benign_restart": (15, 25),
       "benign_burst": (8, 20), "benign_maintenance": (15, 30)}


def make_run(run_type, run_id, rng, intensity=None):
    """intensity (0-1) : force l'amplitude des effets d'un épisode offensif (None : tirage aléatoire 0,4-1,0, comportement d'origine)."""
    n = RUN_LEN
    x = _baseline(rng, n)
    t0 = int(rng.integers(25, 46))
    dur = 0
    active = np.zeros(n, bool)
    if run_type != "normal":
        lo, hi = DUR[run_type]
        dur = int(rng.integers(lo, hi + 1))
        # les effets sont appliqués avant le calcul de net_io pour rester cohérents avec bytes_in
        active = _apply(x, run_type, t0, dur, rng, intensity)
    _net_io(x, rng)
    df = pd.DataFrame({f: x[f] for f in FEATURES})
    df.insert(0, "t", np.arange(n))
    df.insert(0, "run_id", run_id)
    df["run_type"] = run_type
    df["onset"] = t0 if run_type != "normal" else -1
    df["event_end"] = t0 + dur if run_type != "normal" else -1
    df["in_event"] = active
    return df


SPLITS = {
    "train": {"normal": 30, "eclipse": 20, "dos_p2p": 20},
    "val": {"normal": 10, "eclipse": 10, "dos_p2p": 10, "benign_restart": 8, "benign_burst": 8},
    "test": {"normal": 25, "eclipse": 30, "dos_p2p": 30, "benign_restart": 15,
             "benign_burst": 15, "benign_maintenance": 15},
}


def generate_dataset(seed=0, splits=None):
    """Retourne {split: DataFrame}. benign_maintenance n'existe qu'en test (variante jamais vue)."""
    splits = splits or SPLITS
    rng = np.random.default_rng(seed)
    out = {}
    for name, counts in splits.items():
        runs = []
        for rt, c in counts.items():
            for i in range(c):
                runs.append(make_run(rt, f"{name}-{rt}-{i:02d}", rng))
        out[name] = pd.concat(runs, ignore_index=True)
    return out
