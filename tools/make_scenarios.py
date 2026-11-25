"""Génère des TRACES SIMULÉES au format du collecteur (niveau métriques, aucun trafic) pour tester la chaîne et le dashboard.

    py tools/make_scenarios.py --out results/sim_traces --levels 0.3 0.6 1.0 --n 2

Écrit un CSV par run (colonnes t + 12 métriques) et un manifest.csv (types eclipse / dos_p2p / benign_*, début et fin de l'épisode).
Ce sont des épisodes simulés par les profils du projet, pas des mesures : utiles pour la démonstration, pas pour conclure sur un vrai nœud.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eva_guard.config import FEATURES   # noqa: E402
from eva_guard.simulator import make_run   # noqa: E402


def generate(out, levels=(0.3, 0.6, 1.0), n=2, seed=7):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    rows = []

    def save(df, rid, rt):
        df[["t"] + FEATURES].to_csv(out / f"{rid}.csv", index=False)
        on, end = (int(df.onset.iloc[0]), int(df.event_end.iloc[0])) if rt != "normal" else (-1, -1)
        rows.append(dict(run_id=rid, file=f"{rid}.csv", run_type=rt, onset=on, event_end=end))

    for lvl in levels:
        for rt in ("eclipse", "dos_p2p"):
            for i in range(n):
                rid = f"sim_{rt}_i{int(lvl * 10):02d}_{i}"
                save(make_run(rt, rid, rng, intensity=lvl), rid, rt)
    for rt in ("normal", "benign_restart", "benign_burst"):
        for i in range(n):
            rid = f"sim_{rt}_{i}"
            save(make_run(rt, rid, rng), rid, rt)
    pd.DataFrame(rows).to_csv(out / "manifest.csv", index=False)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "results" / "sim_traces"))
    ap.add_argument("--levels", type=float, nargs="+", default=[0.3, 0.6, 1.0])
    ap.add_argument("--n", type=int, default=2)
    a = ap.parse_args()
    r = generate(a.out, a.levels, a.n)
    print(f"{len(r)} traces simulées écrites dans {a.out}")
