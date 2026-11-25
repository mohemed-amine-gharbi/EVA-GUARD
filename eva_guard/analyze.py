"""Analyse d'une trace (DataFrame au schéma du collecteur) par la chaîne EVA-Guard + reconstruction du « chemin observé ».

Le « chemin de l'attaque » est une lecture DÉFENSIVE : pour une hypothèse (Eclipse ou DoS P2P), on indique à quelle fenêtre
chaque indicateur observable du catalogue franchit durablement son seuil, regroupés en étapes d'effets observables
(voisinage, connexions, synchronisation / trafic, ressources, service). Ce n'est pas une description de la méthode d'un attaquant.
"""
import numpy as np
import pandas as pd

from .config import FEATURES, CATALOG, SOURCE, DESCRIPTION, ALERT_CONSEC
from .features import smooth, BaselineStats
from .agents import EvaGuard, Rule
from .evaluate import Bench, RESULTS
from .sensitivity import load_params

# Étapes d'effets observables par hypothèse (indicateurs du catalogue fermé)
STAGES = {
    "eclipse": [
        ("Voisinage appauvri", "le nœud voit moins de pairs, moins variés, et reçoit ses blocs d'une seule source",
         ["peer_diversity", "single_source_ratio", "peer_count"]),
        ("Connexions instables", "les connexions sont rompues et renouvelées plus souvent que d'habitude", ["peer_churn"]),
        ("Isolement du réseau honnête", "le nœud prend du retard sur la chaîne du réseau", ["sync_lag"]),
    ],
    "dos_p2p": [
        ("Trafic entrant anormal", "le volume de messages P2P reçus dépasse nettement la normale", ["msgs_in"]),
        ("Pression sur les ressources", "le processeur et la mémoire du nœud montent", ["cpu", "mem"]),
        ("Service dégradé", "les requêtes RPC deviennent lentes ou échouent", ["rpc_latency", "rpc_error"]),
    ],
}
SUSTAIN = 2          # fenêtres consécutives au-delà du seuil pour dater le franchissement
BASE_WINDOWS = 20    # début de run supposé normal


def prepare_frame(df, run_id="trace", run_type="unknown", onset=-1, event_end=-1):
    """Valide le schéma, comble les trous, lisse (causal) et ajoute les colonnes d'étiquette."""
    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        raise ValueError(f"Colonnes absentes : {missing}. Attendu : t + {FEATURES}")
    d = df[[c for c in df.columns if c in ["t"] + FEATURES]].copy()
    if "t" not in d.columns:
        d.insert(0, "t", np.arange(len(d)))
    for f in FEATURES:
        d[f] = pd.to_numeric(d[f], errors="coerce")
        if d[f].isna().all():
            raise ValueError(f"La colonne '{f}' est vide. Retirez-la du modèle (variable EVA_DROP_FEATURES) ou refaites la collecte.")
    d[FEATURES] = d[FEATURES].interpolate(limit_direction="both")
    d["t"] = np.arange(len(d))
    d.insert(0, "run_id", run_id)
    d["run_type"], d["onset"], d["event_end"] = run_type, int(onset), int(event_end)
    d["in_event"] = (d.t >= onset) & (d.t < event_end) if onset >= 0 else False
    return smooth(d).reset_index(drop=True)


def indicator_timeline(g, stats, attack):
    """Pour chaque indicateur du catalogue : seuil, direction, source, et 0/1 par fenêtre (1 = au-delà du seuil)."""
    out = {}
    for feat, direction in CATALOG[attack]:
        thr = stats.threshold(feat, direction)
        v = g[feat].values
        passed = (v > thr) if direction == "high" else (v < thr)
        out[feat] = dict(source=SOURCE[feat], direction=direction, threshold=float(thr), description=DESCRIPTION[feat],
                         passed=[int(x) for x in passed])
    return out


def first_sustained(passed, start=BASE_WINDOWS, n=SUSTAIN):
    p = np.asarray(passed, bool)
    for t in range(start, len(p) - n + 1):
        if p[t: t + n].all():
            return t
    return None


def attack_path(timeline, attack):
    """Étapes observées dans l'ordre chronologique, avec la fenêtre de franchissement de chaque indicateur."""
    if attack not in STAGES:
        return []
    steps = []
    for name, desc, feats in STAGES[attack]:
        ind = []
        for f in feats:
            if f in timeline:
                ind.append(dict(indicator=f, source=timeline[f]["source"], window=first_sustained(timeline[f]["passed"])))
        seen = [i["window"] for i in ind if i["window"] is not None]
        steps.append(dict(stage=name, description=desc, indicators=ind, first_window=min(seen) if seen else None))
    return sorted(steps, key=lambda s: (s["first_window"] is None, s["first_window"] or 0))


def case_from_frame(g, bench, rule, threshold, title="Trace analysée", truth="inconnu"):
    """Exécute les 3 systèmes sur une trace lissée et retourne un dict au format de results/cases.json (+ chemin observé)."""
    g = g.reset_index(drop=True)
    sc = bench.detector.scores(g)
    bench.detector.threshold = threshold
    sys_ = {m: EvaGuard(bench.detector, bench.interp, bench.stats, rule, m) for m in ("ml_only", "ml_llm", "eva")}
    o = {m: s.process_run(g, sc) for m, s in sys_.items()}
    e = o["eva"]
    attack = e["decision"].attack or (e["hypothesis"].attack if e["hypothesis"] and e["hypothesis"].attack in CATALOG else None)
    tl = {a: indicator_timeline(g, bench.stats, a) for a in CATALOG}
    return dict(
        title=title, run_id=str(g.run_id.iloc[0]), run_type=truth, onset=int(g.onset.iloc[0]), event_end=int(g.event_end.iloc[0]),
        t_alert=e["t_alert"], t_decision=e["t_decision"], verdict=e["decision"].verdict,
        baseline1_pred=o["ml_only"]["pred"], baseline2_pred=o["ml_llm"]["pred"], eva_pred=e["pred"], report=e["report"],
        hypothesis=e["hypothesis"].to_dict() if e["hypothesis"] else None,
        evidence=[x.__dict__ for x in e["decision"].evidence],
        series={f: [round(float(v), 4) for v in g[f]] for f in FEATURES},
        scores=[round(float(v), 4) for v in sc], threshold=float(threshold), rule=rule.to_dict(),
        timeline=tl, path_attack=attack, path=attack_path(tl[attack], attack) if attack else [],
        top_features=[(f, round(z, 2)) for f, z in e["alert"].top_features] if e["alert"] else [])


def load_bench(seed=100):
    b = Bench(seed)
    thr, rule = load_params(seed)
    b.detector.threshold = thr
    return b, thr, rule


class RealBench:
    """Équivalent de Bench pour des runs réels : baseline et Isolation Forest appris sur vos runs normaux (comme real_check)."""

    def __init__(self, stats, detector, interp):
        self.stats, self.detector, self.interp = stats, detector, interp


def bench_from_manifest(manifest, seed=0, quantile=0.995):
    from .detector import Detector
    from .rag import Retriever
    from .llm import OfflineInterpreter
    from .real_loader import load_runs
    df = smooth(load_runs(manifest))
    normal = df[df.run_type == "normal"]
    if normal.run_id.nunique() < 4:
        raise ValueError(f"Au moins 4 runs normaux utilisables sont nécessaires (trouvés : {normal.run_id.nunique()}).")
    stats = BaselineStats(normal)
    det = Detector(stats, seed).fit(normal)
    thr = float(np.quantile(det.scores(normal), quantile))
    det.threshold = thr
    return RealBench(stats, det, OfflineInterpreter(Retriever())), thr, Rule()
