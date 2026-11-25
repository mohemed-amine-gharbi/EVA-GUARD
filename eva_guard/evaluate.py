"""Évaluation comparative (3 systèmes), étude ablative, métriques, intervalles de confiance."""
import json
import itertools
from pathlib import Path
import numpy as np
import pandas as pd

from .config import WINDOW_S, FEATURES
from .simulator import generate_dataset, ATTACK_TYPES
from .features import smooth, BaselineStats
from .detector import Detector
from .rag import Retriever
from .llm import OfflineInterpreter
from .agents import EvaGuard, Rule

RESULTS = Path(__file__).resolve().parent.parent / "results"


# ---------------------------------------------------------------- métriques
def metrics_from_outcomes(df):
    """df : une ligne par run (run_type, onset, pred, t_alert, t_decision)."""
    pos = df[df.run_type.isin(ATTACK_TYPES)]
    neg = df[~df.run_type.isin(ATTACK_TYPES)]
    tp = int(pos.pred.notna().sum())
    fp = int(neg.pred.notna().sum())
    fn = len(pos) - tp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / len(pos) if len(pos) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    hit = pos[pos.pred.notna()]
    type_acc = float((hit.pred == hit.run_type).mean()) if len(hit) else 0.0
    ok = hit[hit.t_alert >= hit.onset]
    det = ((ok.t_alert - ok.onset) * WINDOW_S)
    conf = ((hit.t_decision - hit.t_alert) * WINDOW_S)
    out = dict(precision=precision, recall=recall, f1=f1, fpr=fp / len(neg) if len(neg) else 0.0,
               type_acc=type_acc, tp=tp, fp=fp, fn=fn,
               detect_time_s=float(det.median()) if len(det) else np.nan,
               confirm_time_s=float(conf.median()) if len(conf) else np.nan)
    for rt in sorted(neg.run_type.unique()):
        sub = neg[neg.run_type == rt]
        out[f"fpr_{rt}"] = float(sub.pred.notna().mean())
    return out


def bootstrap_ci(df, stat, n=1000, seed=0):
    rng = np.random.default_rng(seed)
    vals = []
    idx = np.arange(len(df))
    for _ in range(n):
        s = df.iloc[rng.choice(idx, len(idx), replace=True)]
        vals.append(metrics_from_outcomes(s)[stat])
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


# ---------------------------------------------------------------- pipeline par graine
class Bench:
    def __init__(self, seed):
        self.seed = seed
        raw = generate_dataset(seed)
        self.sm = {k: smooth(v) for k, v in raw.items()}
        self.stats = BaselineStats(self.sm["train"])
        self.detector = Detector(self.stats, seed).fit(self.sm["train"])
        self.retriever = Retriever()
        self.interp = OfflineInterpreter(self.retriever)
        self.runs = {s: {rid: g.reset_index(drop=True) for rid, g in df.groupby("run_id", sort=False)}
                     for s, df in self.sm.items()}
        self.scores = {s: {rid: self.detector.scores(g) for rid, g in runs.items()} for s, runs in self.runs.items()}

    def outcomes(self, split, mode="eva", rule=None, **kw):
        sys_ = EvaGuard(self.detector, self.interp, self.stats, rule or Rule(), mode, **kw)
        rows = []
        for rid, g in self.runs[split].items():
            o = sys_.process_run(g, self.scores[split][rid])
            rows.append(dict(seed=self.seed, run_id=rid, run_type=g.run_type.iloc[0], onset=int(g.onset.iloc[0]),
                             pred=o["pred"], t_alert=o["t_alert"], t_decision=o["t_decision"]))
        return pd.DataFrame(rows)

    def select_threshold(self):
        allv = np.concatenate(list(self.scores["val"].values()))
        grid = np.quantile(allv, np.linspace(0.70, 0.999, 40))
        best = None
        for thr in grid:
            self.detector.threshold = float(thr)
            m = metrics_from_outcomes(self.outcomes("val", "ml_only"))
            key = (m["f1"], -m["fpr"], thr)
            if best is None or key > best[0]:
                best = (key, float(thr))
        self.detector.threshold = best[1]
        return best[1]

    def select_rule(self):
        best = None
        for k, s, p in itertools.product([2, 3, 4], [1, 2], [1, 2, 3, 4]):
            r = Rule(k=k, min_sources=s, persistence=p)
            m = metrics_from_outcomes(self.outcomes("val", "eva", r))
            key = (m["f1"], -m["fpr"], k, s, p)   # à égalité : règle la plus stricte
            if best is None or key > best[0]:
                best = (key, r)
        return best[1]


ABLATIONS = [
    ("EVA-Guard complet", dict()),
    ("sans source RPC", dict(excluded_sources=("RPC",))),
    ("sans source système", dict(excluded_sources=("SYS",))),
    ("sans source P2P", dict(excluded_sources=("P2P",))),
    ("sans LLM/RAG (type ML)", dict(use_interpreter=False)),
    ("sans persistance (1 fenêtre)", dict(rule_override=dict(persistence=1))),
    ("sans exigence multi-source", dict(rule_override=dict(min_sources=1))),
    ("k = 2 indicateurs", dict(rule_override=dict(k=2))),
    ("k = 4 indicateurs", dict(rule_override=dict(k=4))),
]


def run_experiment(seeds=(100, 101, 102, 103, 104), verbose=True):
    RESULTS.mkdir(exist_ok=True)
    all_out, all_abl, params, cases = [], [], [], None
    for seed in seeds:
        b = Bench(seed)
        thr = b.select_threshold()
        rule = b.select_rule()
        params.append(dict(seed=seed, threshold=thr, **rule.to_dict()))
        if verbose:
            print(f"seed {seed}: seuil={thr:.3f} règle={rule.to_dict()}")
        for name, mode in [("Baseline 1 : ML seul", "ml_only"), ("Baseline 2 : ML + LLM/RAG", "ml_llm"),
                           ("EVA-Guard : ML + LLM/RAG + agents + confirmation", "eva")]:
            o = b.outcomes("test", mode, rule)
            o["system"] = name
            all_out.append(o)
        for name, kw in ABLATIONS:
            kw = dict(kw)
            r = rule
            if "rule_override" in kw:
                d = rule.to_dict()
                d.update(kw.pop("rule_override"))
                d.pop("timeout")
                r = Rule(**d)
            o = b.outcomes("test", "eva", r, **kw)
            o["system"] = name
            all_abl.append(o)
        if seed == seeds[0]:
            cases = b
    out = pd.concat(all_out, ignore_index=True)
    abl = pd.concat(all_abl, ignore_index=True)
    out.to_csv(RESULTS / "outcomes.csv", index=False)
    abl.to_csv(RESULTS / "ablation_outcomes.csv", index=False)
    pd.DataFrame(params).to_csv(RESULTS / "selected_params.csv", index=False)

    def summarize(df):
        rows = []
        for system, g in df.groupby("system", sort=False):
            per_seed = pd.DataFrame([metrics_from_outcomes(gs) for _, gs in g.groupby("seed")])
            row = dict(system=system)
            for c in per_seed.columns:
                row[f"{c}_mean"] = float(per_seed[c].mean())
                row[f"{c}_std"] = float(per_seed[c].std(ddof=0))
            row["f1_ci"] = bootstrap_ci(g, "f1")
            row["fpr_ci"] = bootstrap_ci(g, "fpr")
            rows.append(row)
        return pd.DataFrame(rows)

    summ = summarize(out)
    summ_abl = summarize(abl)
    summ.to_json(RESULTS / "summary.json", orient="records", indent=1, force_ascii=False)
    summ_abl.to_json(RESULTS / "ablation_summary.json", orient="records", indent=1, force_ascii=False)
    return b, out, abl, summ, summ_abl, params


if __name__ == "__main__":
    run_experiment()
