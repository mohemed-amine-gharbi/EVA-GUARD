"""Figures du rapport et export des cas d'étude (pour le dashboard et le PDF)."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .config import FEATURES, WINDOW_S, CATALOG
from .evaluate import Bench, RESULTS
from .agents import EvaGuard, Rule

FIG = RESULTS / "figures"
COL = {"Baseline 1": "#8c8c8c", "Baseline 2": "#5b8fd1", "EVA-Guard": "#d1603d"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})


def _short(name):
    for k in COL:
        if name.startswith(k):
            return k
    return name


def _load():
    summ = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    abl = json.loads((RESULTS / "ablation_summary.json").read_text(encoding="utf-8"))
    params = pd.read_csv(RESULTS / "selected_params.csv")
    return summ, abl, params


def fig_comparison(summ):
    FIG.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4), gridspec_kw={"width_ratios": [3, 2]})
    metrics = [("precision", "Precision"), ("recall", "Recall"), ("f1", "F1-score")]
    w = 0.25
    for i, s in enumerate(summ):
        name = _short(s["system"])
        xs = np.arange(len(metrics)) + (i - 1) * w
        ax[0].bar(xs, [s[f"{m}_mean"] for m, _ in metrics], w, yerr=[s[f"{m}_std"] for m, _ in metrics],
                  color=COL[name], label=name, capsize=2)
    ax[0].set_xticks(range(len(metrics)), [l for _, l in metrics])
    ax[0].set_ylim(0, 1.05)
    ax[0].set_title("Détection des attaques (moyenne ± écart-type, 5 graines)")
    ax[0].legend(frameon=False, loc="lower left", fontsize=8)
    for i, s in enumerate(summ):
        name = _short(s["system"])
        ax[1].bar(i, s["fpr_mean"], 0.6, yerr=s["fpr_std"], color=COL[name], capsize=3)
        ax[1].text(i, s["fpr_mean"] + s["fpr_std"] + 0.02, f"{s['fpr_mean']:.2f}", ha="center", fontsize=8)
    ax[1].set_xticks(range(len(summ)), [_short(s["system"]) for s in summ])
    ax[1].set_ylim(0, 1.0)
    ax[1].set_title("Taux de faux positifs (runs non offensifs)")
    fig.tight_layout()
    fig.savefig(FIG / "comparison.png")
    plt.close(fig)


def fig_fpr_by_type(summ):
    types = [("fpr_normal", "Normal"), ("fpr_benign_restart", "Redémarrage"), ("fpr_benign_burst", "Rafale légitime"),
             ("fpr_benign_maintenance", "Maintenance\n(jamais vue)")]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    w = 0.25
    for i, s in enumerate(summ):
        name = _short(s["system"])
        ax.bar(np.arange(len(types)) + (i - 1) * w, [s.get(f"{k}_mean", 0) for k, _ in types], w,
               yerr=[s.get(f"{k}_std", 0) for k, _ in types], color=COL[name], label=name, capsize=2)
    ax.set_xticks(range(len(types)), [l for _, l in types])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Part de runs classés « attaque »")
    ax.set_title("Faux positifs par type de run non offensif")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fpr_by_type.png")
    plt.close(fig)


def fig_times(summ):
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    w = 0.35
    for i, s in enumerate(summ):
        ax.bar(i - w / 2, s["detect_time_s_mean"], w, yerr=s["detect_time_s_std"], color="#5b8fd1",
               label="Temps de détection" if i == 0 else None, capsize=2)
        ax.bar(i + w / 2, s["confirm_time_s_mean"], w, yerr=s["confirm_time_s_std"], color="#d1603d",
               label="Temps de confirmation" if i == 0 else None, capsize=2)
    ax.set_xticks(range(len(summ)), [_short(s["system"]) for s in summ])
    ax.set_ylabel("secondes (médiane par graine)")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Délais : détection (début d'épisode → alerte) et confirmation (alerte → décision)")
    fig.tight_layout()
    fig.savefig(FIG / "times.png")
    plt.close(fig)


def fig_ablation(abl):
    names = [a["system"] for a in abl]
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.6), sharey=True)
    y = np.arange(len(names))[::-1]
    ax[0].barh(y, [a["f1_mean"] for a in abl], xerr=[a["f1_std"] for a in abl], color="#5b8fd1", capsize=2)
    ax[0].set_title("F1-score")
    ax[1].barh(y, [a["fpr_mean"] for a in abl], xerr=[a["fpr_std"] for a in abl], color="#d1603d", capsize=2)
    ax[1].set_title("Taux de faux positifs")
    ax[0].set_yticks(y, names)
    for a_ in ax:
        a_.set_xlim(0, 1.0)
    fig.tight_layout()
    fig.savefig(FIG / "ablation.png")
    plt.close(fig)


def fig_dataset_sample(b):
    feats = ["peer_diversity", "peer_count", "sync_lag", "msgs_in", "cpu", "rpc_error"]
    types = ["normal", "eclipse", "dos_p2p", "benign_restart", "benign_burst", "benign_maintenance"]
    labels = ["normal", "Eclipse", "DoS P2P", "redémarrage", "rafale légitime", "maintenance"]
    cols = ["#444444", "#d1603d", "#b03a8c", "#5b8fd1", "#3aa675", "#c9a227"]
    fig, axes = plt.subplots(2, 3, figsize=(9.5, 4.6))
    runs = b.runs["test"]
    for ax, f in zip(axes.ravel(), feats):
        for t, lab, c in zip(types, labels, cols):
            rid = next(r for r, g in runs.items() if g.run_type.iloc[0] == t)
            g = runs[rid]
            ax.plot(g["t"] * WINDOW_S, g[f], color=c, lw=1.1, label=lab)
        ax.set_title(f, fontsize=9)
        ax.set_xlabel("temps (s)")
    axes[0, 0].legend(frameon=False, fontsize=6.5, ncol=1)
    fig.tight_layout()
    fig.savefig(FIG / "dataset_sample.png")
    plt.close(fig)


def fig_importance(b):
    imp = pd.Series(b.detector.rf.feature_importances_, index=FEATURES).sort_values()
    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    ax.barh(imp.index, imp.values, color="#5b8fd1")
    ax.set_title("Importance des features (Random Forest, type d'attaque)")
    fig.tight_layout()
    fig.savefig(FIG / "importance.png")
    plt.close(fig)


def build_cases(seed, thr, rule):
    """Choisit 4 cas représentatifs sur le jeu de test et exécute EVA-Guard dessus."""
    from .analyze import indicator_timeline, attack_path
    from .config import CATALOG
    b = Bench(seed)
    b.detector.threshold = thr
    sys_ = EvaGuard(b.detector, b.interp, b.stats, rule, "eva")
    b2 = EvaGuard(b.detector, b.interp, b.stats, rule, "ml_llm")
    b1 = EvaGuard(b.detector, b.interp, b.stats, rule, "ml_only")
    wanted = [("eclipse", "Attaque Eclipse confirmée"), ("dos_p2p", "Déni de service P2P confirmé"),
              ("benign_burst", "Rafale légitime (écartée)"), ("benign_restart", "Redémarrage (écarté)"),
              ("benign_maintenance", "Maintenance jamais vue (faux positif)")]
    cases = []
    for rt, title in wanted:
        chosen = None
        for rid, g in b.runs["test"].items():
            if g.run_type.iloc[0] != rt:
                continue
            o = sys_.process_run(g, b.scores["test"][rid])
            if rt in ("eclipse", "dos_p2p"):
                good = o["decision"].verdict == "CONFIRMED" and o["pred"] == rt
            elif rt in ("benign_burst", "benign_restart"):
                good = o["alert"] is not None and o["decision"].verdict == "NOT_CONFIRMED"
            else:   # cas difficile montré tel quel : un faux positif d'EVA-Guard, pas un cas favorable
                good = o["decision"].verdict == "CONFIRMED"
            if good:
                chosen = (rid, g, o)
                break
        if chosen is None:
            continue
        rid, g, o = chosen
        sc = b.scores["test"][rid]
        tl = {a: indicator_timeline(g, b.stats, a) for a in CATALOG}
        pa = o["decision"].attack or (o["hypothesis"].attack if o["hypothesis"] and o["hypothesis"].attack in CATALOG else None)
        cases.append(dict(timeline=tl, path_attack=pa, path=attack_path(tl[pa], pa) if pa else [],
                          top_features=[(f, round(z, 2)) for f, z in o["alert"].top_features] if o["alert"] else [],
            title=title, run_id=rid, run_type=rt, onset=int(g.onset.iloc[0]), event_end=int(g.event_end.iloc[0]),
            t_alert=o["t_alert"], t_decision=o["t_decision"], verdict=o["decision"].verdict,
            baseline1_pred=b1.process_run(g, sc)["pred"], baseline2_pred=b2.process_run(g, sc)["pred"],
            eva_pred=o["pred"], report=o["report"],
            hypothesis=o["hypothesis"].to_dict() if o["hypothesis"] else None,
            evidence=[e.__dict__ for e in o["decision"].evidence],
            series={f: [round(float(v), 4) for v in g[f]] for f in FEATURES},
            scores=[round(float(v), 4) for v in sc], threshold=thr, rule=rule.to_dict()))
    (RESULTS / "cases.json").write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
    return b, cases


SHORT = {"eclipse": "Eclipse", "dos_p2p": "DoS P2P", "benign_burst": "Rafale légitime",
         "benign_restart": "Redémarrage", "benign_maintenance": "Maintenance"}


def rel_dev(s, n0=20):
    """Écart à la baseline initiale du run (20 premières fenêtres), en écarts-types (plancher sur l'écart-type)."""
    s = np.asarray(s, float)
    m, sd = s[:n0].mean(), s[:n0].std()
    return (s - m) / max(sd, 0.05 * abs(m), 1e-3)


def fig_cases(cases):
    n = len(cases)
    fig, axes = plt.subplots(n, 2, figsize=(9.5, 2.1 * n), sharex=True)
    feat_for = {"eclipse": ["peer_diversity", "sync_lag"], "dos_p2p": ["msgs_in", "cpu"],
                "benign_burst": ["msgs_in", "cpu"], "benign_restart": ["peer_count", "sync_lag"],
                "benign_maintenance": ["msgs_in", "cpu"]}
    for r, c in enumerate(cases):
        t = np.arange(len(c["scores"])) * WINDOW_S
        ax = axes[r, 0]
        ax.plot(t, c["scores"], color="#444", lw=1)
        ax.axhline(c["threshold"], color="#d1603d", ls="--", lw=0.8)
        ax.set_ylabel(SHORT[c["run_type"]], fontsize=7.5)
        ax.axvspan(c["onset"] * WINDOW_S, c["event_end"] * WINDOW_S, color="#f4d9d0", alpha=0.6)
        if c["t_alert"] is not None:
            ax.axvline(c["t_alert"] * WINDOW_S, color="#5b8fd1", lw=1.2)
        if c["t_decision"] is not None and c["verdict"] == "CONFIRMED":
            ax.axvline(c["t_decision"] * WINDOW_S, color="#3aa675", lw=1.2)
        a2 = axes[r, 1]
        for f, col in zip(feat_for[c["run_type"]], ["#b03a8c", "#3aa675"]):
            s = np.array(c["series"][f])
            a2.plot(t, rel_dev(s), color=col, lw=1, label=f)
        a2.axvspan(c["onset"] * WINDOW_S, c["event_end"] * WINDOW_S, color="#f4d9d0", alpha=0.6)
        a2.legend(frameon=False, fontsize=6.5, loc="upper left")
    axes[0, 0].set_title("Score d'anomalie (ligne pointillée : seuil ; bleu : alerte ; vert : confirmation)", fontsize=7.5)
    axes[0, 1].set_title("Métriques clés : écart à la baseline initiale (en écarts-types)", fontsize=7.5)
    axes[-1, 0].set_xlabel("temps (s)")
    axes[-1, 1].set_xlabel("temps (s)")
    fig.tight_layout()
    fig.savefig(FIG / "cases.png")
    plt.close(fig)


def make_all():
    summ, abl, params = _load()
    FIG.mkdir(parents=True, exist_ok=True)
    fig_comparison(summ)
    fig_fpr_by_type(summ)
    fig_times(summ)
    fig_ablation(abl)
    p0 = params.iloc[0]
    rule = Rule(k=int(p0.k), min_sources=int(p0.min_sources), persistence=int(p0.persistence))
    b, cases = build_cases(int(p0.seed), float(p0.threshold), rule)
    fig_dataset_sample(b)
    fig_importance(b)
    fig_cases(cases)
    return cases


if __name__ == "__main__":
    make_all()
