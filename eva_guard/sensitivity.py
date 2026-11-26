"""Sensibilité à l'intensité d'un épisode offensif SIMULÉ (niveau métriques, aucun trafic).

Question : à partir de quelle intensité (0,1 = très faible, 1,0 = forte) chaque système détecte-t-il et confirme-t-il
un épisode ? Les profils d'attaque sont ceux du simulateur (amplitude `intensity` des effets sur les métriques).

    python -m eva_guard.sensitivity            # écrit results/sensitivity.csv + figures/sensitivity.png
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from .simulator import make_run, ATTACK_TYPES
from .features import smooth
from .agents import EvaGuard, Rule
from .evaluate import Bench, RESULTS

LEVELS = [0.1, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0]
SYSTEMS = [("Baseline 1 : ML seul", "ml_only"), ("Baseline 2 : ML + LLM/RAG", "ml_llm"), ("EVA-Guard", "eva")]


def load_params(seed):
    from . import config
    f = RESULTS / "selected_params.csv"
    if f.exists() and len(config.FEATURES) == 12:       # paramètres appris avec les 12 métriques ; sinon recalibrage
        p = pd.read_csv(f)
        row = p[p.seed == seed]
        if len(row):
            r = row.iloc[0]
            return float(r.threshold), Rule(int(r.k), int(r.min_sources), int(r.persistence))
    b = Bench(seed)
    return b.select_threshold(), b.select_rule()


def run(seeds=(100, 101, 102), n_per=20, verbose=True):
    rows = []
    for seed in seeds:
        b = Bench(seed)
        thr, rule = load_params(seed)
        b.detector.threshold = thr
        systems = {m: EvaGuard(b.detector, b.interp, b.stats, rule, m) for _, m in SYSTEMS}
        rng = np.random.default_rng(seed + 5000)
        for lvl in LEVELS:
            for rt in ATTACK_TYPES:
                for i in range(n_per):
                    g = smooth(make_run(rt, f"s{seed}-{rt}-{lvl}-{i}", rng, intensity=lvl)).reset_index(drop=True)
                    sc = b.detector.scores(g)
                    for name, mode in SYSTEMS:
                        o = systems[mode].process_run(g, sc)
                        rows.append(dict(seed=seed, level=lvl, attack=rt, system=name, detected=o["pred"] is not None,
                                         correct=o["pred"] == rt, delay_s=(o["t_alert"] - int(g.onset.iloc[0])) * 10
                                         if o["t_alert"] is not None else np.nan))
        if verbose:
            print("seed", seed, "ok")
    df = pd.DataFrame(rows)
    out = df.groupby(["system", "attack", "level"]).agg(rappel=("detected", "mean"), type_correct=("correct", "mean"),
                                                        delai_median_s=("delay_s", "median"), n=("detected", "size")).reset_index()
    out.to_csv(RESULTS / "sensitivity.csv", index=False)
    return out


def plot(out, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4), sharey=True)
    col = {"Baseline 1 : ML seul": "#7f7f7f", "Baseline 2 : ML + LLM/RAG": "#1f77b4", "EVA-Guard": "#d9482b"}
    for ax, att, ttl in zip(axes, ["eclipse", "dos_p2p"], ["Eclipse (simulée)", "DoS P2P (simulé)"]):
        for name, _ in SYSTEMS:
            d = out[(out.system == name) & (out.attack == att)].sort_values("level")
            ax.plot(d.level, d.rappel, marker="o", color=col[name], label=name)
        ax.set_title(ttl)
        ax.set_xlabel("intensité de l'épisode (0,1 faible → 1,0 forte)")
        ax.grid(alpha=.3)
        ax.set_ylim(-0.02, 1.02)
    axes[0].set_ylabel("part des épisodes détectés (rappel)")
    axes[1].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    a = ap.parse_args()
    out = run(n_per=a.n)
    Path(RESULTS / "figures").mkdir(exist_ok=True)
    plot(out, RESULTS / "figures" / "sensitivity.png")
    print(out.pivot_table(index=["attack", "level"], columns="system", values="rappel").round(2).to_string())
