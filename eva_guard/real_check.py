"""Contrôle sur données RÉELLES (sans épisodes offensifs) : taux de fausses alertes de chaque système.

    python -m eva_guard.real_check --manifest results/runs/manifest.csv

Principe : la baseline et l'Isolation Forest sont appris sur une partie des runs « normal » ; on mesure ensuite, sur les
runs normaux mis de côté et sur les épisodes bénins (redémarrage, rafale), la part de runs classés « attaque » par
Baseline 1 (ML seul), Baseline 2 (ML + LLM/RAG) et EVA-Guard. Aucune attaque n'est nécessaire : seules des fausses alertes
sont mesurées. Le rappel (détection des vraies attaques) ne peut pas être mesuré sans traces d'attaque fournies par l'encadrant.
"""
import argparse
from ._autodrop import autodrop
autodrop()
from pathlib import Path
import numpy as np
import pandas as pd

from .features import smooth, BaselineStats
from .detector import Detector
from .rag import Retriever
from .llm import OfflineInterpreter
from .agents import EvaGuard, Rule
from .real_loader import load_runs

SYSTEMS = [("Baseline 1 : ML seul", "ml_only"), ("Baseline 2 : ML + LLM/RAG", "ml_llm"), ("EVA-Guard", "eva")]


def run(manifest, seed=0, quantile=0.995, rule=None, verbose=True):
    df = smooth(load_runs(manifest))
    normal_ids = sorted(df[df.run_type == "normal"].run_id.unique())
    if len(normal_ids) < 6:
        counts = df.drop_duplicates("run_id").run_type.value_counts().to_dict()
        raise ValueError(f"Il faut au moins 6 runs normaux (idle + moderate + high) ; trouvés : {len(normal_ids)}. "
                         f"Runs chargés par type : {counts}. Enregistrez d'autres runs avec tools/run_session.py.")
    test_normal = set(normal_ids[2::3])                       # 1 run normal sur 3 mis de côté
    train = df[(df.run_type == "normal") & ~df.run_id.isin(test_normal)]
    stats = BaselineStats(train)
    det = Detector(stats, seed).fit(train)
    det.threshold = float(np.quantile(det.scores(train), quantile))
    interp = OfflineInterpreter(Retriever())
    rule = rule or Rule()
    evaluated = df[df.run_id.isin(test_normal) | (df.run_type != "normal")]
    rows = []
    for name, mode in SYSTEMS:
        sysm = EvaGuard(det, interp, stats, rule, mode)
        for rid, g in evaluated.groupby("run_id", sort=False):
            g = g.reset_index(drop=True)
            o = sysm.process_run(g)
            rows.append(dict(system=name, run_id=rid, run_type=g.run_type.iloc[0], flagged=o["pred"] is not None,
                             t_alert=o["t_alert"], hypothesis=o["hypothesis"].attack if o["hypothesis"] else None))
    res = pd.DataFrame(rows)
    summ = res.groupby(["system", "run_type"]).agg(runs=("flagged", "size"), classes_attaque=("flagged", "sum"),
                                                   taux=("flagged", "mean")).reset_index()
    if verbose:
        print(f"Runs d'entraînement (normal) : {train.run_id.nunique()} ; seuil d'alerte : {det.threshold:.3f}")
        print(summ.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    return res, summ


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default="results/runs/manifest.csv")
    ap.add_argument("--quantile", type=float, default=0.995)
    a = ap.parse_args()
    res, summ = run(a.manifest, quantile=a.quantile)
    out = Path(a.manifest).parent / "real_check.csv"
    summ.to_csv(out, index=False)
    print("écrit", out)


if __name__ == "__main__":
    main()
