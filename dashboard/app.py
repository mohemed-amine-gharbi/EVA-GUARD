"""Dashboard EVA-Guard (Streamlit) : rejeu détaillé d'un cas, analyse de VOTRE trace CSV, chemin observé, résultats, aide.

Lancement :  streamlit run dashboard/app.py      (ou : docker compose up dashboard -> http://localhost:8501)
Prérequis : avoir exécuté `python run_all.py` ou `python run_all.py --figures` (génère results/cases.json).
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eva_guard.config import FEATURES, DESCRIPTION, SOURCE, CATALOG   # noqa: E402

st.set_page_config(page_title="EVA-Guard", layout="wide", page_icon="🛡️")

COL = {"CONFIRMED": "#c0392b", "NOT_CONFIRMED": "#d68910", "NO_ALERT": "#1e8449"}
VERDICT_FR = {"CONFIRMED": "ATTAQUE CONFIRMÉE", "NOT_CONFIRMED": "ALERTE NON CONFIRMÉE", "NO_ALERT": "AUCUNE ALERTE"}
ATT_FR = {"eclipse": "Eclipse (isolement P2P)", "dos_p2p": "DoS P2P (saturation par messages)", None: "aucune"}
SRC_FR = {"P2P": "réseau P2P", "SYS": "système", "RPC": "interface RPC"}

st.markdown("""<style>
.badge{display:inline-block;padding:.35rem .8rem;border-radius:.4rem;color:#fff;font-weight:700;font-size:1.05rem}
.box{border-left:4px solid #888;padding:.5rem .9rem;background:rgba(128,128,128,.08);margin:.4rem 0;border-radius:.2rem}
.small{font-size:.85rem;opacity:.8}
</style>""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------- figures
def _marks(ax, c, upto):
    if c["onset"] is not None and c["onset"] >= 0 and c["event_end"] >= 0:
        ax.axvspan(c["onset"], min(c["event_end"], upto + 1), color="#999", alpha=.18, lw=0)
    if c["t_alert"] is not None and upto >= c["t_alert"]:
        ax.axvline(c["t_alert"], color="#d68910", ls="--", lw=1.4)
    if c["t_decision"] is not None and upto >= c["t_decision"]:
        ax.axvline(c["t_decision"], color=COL.get(c["verdict"], "#444"), ls="-", lw=1.6)


def fig_scores(c, upto):
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    x = np.arange(upto + 1)
    ax.plot(x, c["scores"][: upto + 1], color="#1f4e79", lw=1.6, label="score d'anomalie (Isolation Forest)")
    ax.axhline(c["threshold"], color="#c0392b", ls=":", lw=1.2, label=f"seuil d'alerte = {c['threshold']:.2f}")
    _marks(ax, c, upto)
    ax.set_xlabel("fenêtre (1 fenêtre = 10 s)")
    ax.set_ylabel("score")
    ax.set_xlim(0, len(c["scores"]) - 1)
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(alpha=.25)
    fig.tight_layout()
    return fig


def fig_series(c, feats, upto):
    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    for f in feats:
        s = np.asarray(c["series"][f][: upto + 1], float)
        m, sd = s[:20].mean(), s[:20].std()
        ax.plot(s.shape[0] and np.arange(len(s)), (s - m) / max(sd, 0.05 * abs(m), 1e-3), lw=1.3, label=f)
    _marks(ax, c, upto)
    ax.axhline(0, color="#444", lw=.6)
    ax.set_xlabel("fenêtre (1 fenêtre = 10 s)")
    ax.set_ylabel("écart à la baseline initiale (σ)")
    ax.set_xlim(0, len(c["scores"]) - 1)
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=.25)
    fig.tight_layout()
    return fig


def fig_indicators(c, attack, upto):
    tl = c["timeline"][attack]
    names = list(tl.keys())
    mat = np.array([tl[n]["passed"][: upto + 1] for n in names], float)
    fig, ax = plt.subplots(figsize=(7.5, 0.55 * len(names) + 0.9))
    ax.imshow(mat, aspect="auto", cmap="Reds", vmin=0, vmax=1, interpolation="nearest",
              extent=[0, mat.shape[1], len(names), 0])
    ax.set_yticks(np.arange(len(names)) + .5)
    ax.set_yticklabels([f"{n} [{tl[n]['source']}] {'↑' if tl[n]['direction'] == 'high' else '↓'}" for n in names], fontsize=8)
    if c["t_alert"] is not None and upto >= c["t_alert"]:
        ax.axvline(c["t_alert"], color="#d68910", ls="--", lw=1.4)
    if c["t_decision"] is not None and upto >= c["t_decision"]:
        ax.axvline(c["t_decision"], color="#222", lw=1.6)
    ax.set_xlim(0, len(c["scores"]) - 1)
    ax.set_xlabel("fenêtre — rouge = indicateur au-delà de son seuil")
    fig.tight_layout()
    return fig


def fig_path(c, upto):
    steps = [s for s in c["path"] if s["first_window"] is not None and s["first_window"] <= upto]
    fig, ax = plt.subplots(figsize=(7.5, 2.4))
    ax.set_xlim(0, len(c["scores"]) - 1)
    ax.set_ylim(-0.5, max(len(steps), 1) - 0.5)
    ax.invert_yaxis()
    for i, s in enumerate(steps):
        ax.plot([s["first_window"], len(c["scores"]) - 1], [i, i], color="#c0392b", alpha=.25, lw=6, solid_capstyle="butt")
        ax.plot(s["first_window"], i, "o", color="#c0392b")
        ax.text(s["first_window"] + 1, i - .22, f"{s['stage']} (fenêtre {s['first_window']})", fontsize=8)
    _marks(ax, c, upto)
    ax.set_yticks([])
    ax.set_xlabel("fenêtre")
    fig.tight_layout()
    return fig


# ----------------------------------------------------------------------------- affichage d'un cas
def render_case(c, key):
    n = len(c["scores"])
    upto = st.slider("Fenêtre courante (rejeu : seules les données jusqu'à cette fenêtre sont affichées)", 5, n - 1, n - 1, key=f"w_{key}")
    alert_seen = c["t_alert"] is not None and upto >= c["t_alert"]
    decided = c["t_decision"] is not None and upto >= c["t_decision"]
    verdict = c["verdict"] if decided else ("EN COURS" if alert_seen else "NO_ALERT")

    k = st.columns(5)
    if decided:
        k[0].markdown(f"<span class='badge' style='background:{COL[c['verdict']]}'>{VERDICT_FR[c['verdict']]}</span>", unsafe_allow_html=True)
    elif alert_seen:
        k[0].markdown("<span class='badge' style='background:#d68910'>CONFIRMATION EN COURS</span>", unsafe_allow_html=True)
    else:
        k[0].markdown(f"<span class='badge' style='background:{COL['NO_ALERT']}'>{VERDICT_FR['NO_ALERT']}</span>", unsafe_allow_html=True)
    k[1].metric("Alerte ML", f"fenêtre {c['t_alert']}" if alert_seen else "—")
    k[2].metric("Décision", f"fenêtre {c['t_decision']}" if decided else "—")
    if alert_seen and c["onset"] is not None and c["onset"] >= 0:
        k[3].metric("Délai alerte / début de l'épisode", f"{(c['t_alert'] - c['onset']) * 10} s")
    else:
        k[3].metric("Délai alerte / début de l'épisode", "—", help="Disponible si le début réel de l'épisode est connu.")
    ev = c["evidence"] if decided else []
    k[4].metric("Indicateurs satisfaits", f"{sum(e['passed'] for e in ev)}/{len(ev)}" if ev else "—")

    tabs = st.tabs(["1 · Détection ML", "2 · Hypothèse LLM + RAG", "3 · Preuves et décision", "4 · Chemin observé", "5 · Comparer les 3 systèmes", "6 · Rapport"])

    with tabs[0]:
        st.markdown("<div class='box'>L'<b>Isolation Forest</b> apprend le comportement normal du nœud. Un score au-dessus du seuil pendant "
                    "<b>2 fenêtres de suite</b> lève l'alerte. Le ML ne dit pas si c'est une attaque : il dit que « quelque chose change ».</div>",
                    unsafe_allow_html=True)
        st.pyplot(fig_scores(c, upto))
        st.caption("Zone grise : épisode réel (si connu). Trait orange : alerte. Trait plein : décision.")
        feats = st.multiselect("Métriques à comparer à la baseline initiale", FEATURES,
                               default=[f for f in ["peer_diversity", "sync_lag", "msgs_in", "cpu"] if f in FEATURES], key=f"f_{key}")
        if feats:
            st.pyplot(fig_series(c, feats, upto))
        if alert_seen and c.get("top_features"):
            st.markdown("**Métriques les plus déviantes à l'alerte** (z-score par rapport à la baseline normale)")
            st.dataframe(pd.DataFrame(c["top_features"], columns=["métrique", "z-score"]).assign(
                signification=lambda d: d["métrique"].map(DESCRIPTION), source=lambda d: d["métrique"].map(SOURCE)), hide_index=True)

    with tabs[1]:
        if alert_seen and c["hypothesis"]:
            h = c["hypothesis"]
            a, b = st.columns([2, 1])
            a.markdown(f"**Hypothèse : {ATT_FR.get(h['attack'], h['attack'])}**" if h["attack"] in ATT_FR else f"**Hypothèse : {h['attack']}** (non offensive)")
            b.metric("Confiance de la récupération (similarité)", f"{h['confidence']:.2f}")
            st.markdown(f"<div class='box'>{h['rationale']}</div>", unsafe_allow_html=True)
            st.caption(f"Interprète : {h['backend']}. Le LLM propose, il ne confirme jamais : la décision dépend uniquement de l'onglet 3.")
            st.markdown("**Fiches de la base de connaissances (RAG) récupérées**")
            from eva_guard.rag import load_docs
            docs = {d["id"]: d for d in load_docs()}
            for i, did in enumerate(h["cited_docs"]):
                d = docs.get(did)
                if d:
                    with st.expander(f"{i + 1}. {d['title']}  ·  type : {d['label']}", expanded=(i == 0)):
                        st.markdown(d["text"])
            if h.get("evidence_to_check"):
                st.markdown("**Indicateurs à vérifier (catalogue fermé de l'hypothèse)** : " +
                            ", ".join(f"{f} ({'haut' if d == 'high' else 'bas'})" for f, d in h["evidence_to_check"]))
        elif alert_seen:
            st.info("Alerte ML sans hypothèse : le système « ML seul » ne consulte pas le LLM.")
        else:
            st.success("Aucune alerte pour l'instant : l'interprète n'est pas sollicité.")

    with tabs[2]:
        r = c["rule"]
        st.markdown(f"<div class='box'><b>Règle de confirmation (déterministe)</b> : au moins <b>{r['k']}</b> indicateurs au-delà de leur seuil, "
                    f"issus d'au moins <b>{r['min_sources']}</b> sources différentes (P2P, système, RPC), pendant <b>{r['persistence']}</b> fenêtres "
                    f"consécutives, dans un délai de {r['timeout']} fenêtres après l'alerte.</div>", unsafe_allow_html=True)
        if alert_seen:
            attack = (c["hypothesis"] or {}).get("attack")
            if attack in CATALOG and c.get("timeline"):
                st.pyplot(fig_indicators(c, attack, upto))
                st.caption("Chaque ligne est un indicateur du catalogue de l'hypothèse ; ↑ = preuve si la valeur dépasse le seuil haut, ↓ = si elle passe sous le seuil bas.")
            if decided and c["evidence"]:
                e = pd.DataFrame(c["evidence"])
                e["preuve"] = e["passed"].map({True: "✅ oui", False: "non"})
                e["source"] = e["source"].map(lambda s: f"{s} ({SRC_FR.get(s, s)})")
                e["sens"] = e["direction"].map({"high": "doit être > seuil", "low": "doit être < seuil"})
                e["signification"] = e["indicator"].map(DESCRIPTION)
                st.dataframe(e[["preuve", "indicator", "source", "value", "threshold", "sens", "signification"]].rename(
                    columns={"indicator": "indicateur", "value": "valeur", "threshold": "seuil"}), hide_index=True)
            if decided:
                msg = f"{VERDICT_FR[c['verdict']]} à la fenêtre {c['t_decision']}"
                (st.error if c["verdict"] == "CONFIRMED" else st.warning)(msg)
            else:
                st.info("Confirmation en cours : les preuves sont collectées fenêtre par fenêtre.")
        else:
            st.success("Pas d'alerte : aucune preuve à collecter.")

    with tabs[3]:
        st.markdown("<div class='box'>Cette vue reconstruit, <b>après coup</b>, l'ordre dans lequel les effets observables sont apparus sur le nœud. "
                    "Elle décrit des <b>symptômes mesurés</b> (métriques), pas la méthode d'un attaquant : elle sert à comprendre et expliquer l'incident.</div>",
                    unsafe_allow_html=True)
        steps = [s for s in c.get("path", []) if s["first_window"] is not None and s["first_window"] <= upto]
        if steps and alert_seen:
            st.markdown(f"**Hypothèse suivie : {ATT_FR.get(c['path_attack'], c['path_attack'])}**")
            st.pyplot(fig_path(c, upto))
            rows = []
            for i, s in enumerate(steps, 1):
                rows.append({"étape": i, "effet observable": s["stage"], "première fenêtre": s["first_window"],
                             "ce que cela signifie": s["description"],
                             "indicateurs (fenêtre)": ", ".join(f"{x['indicator']} ({x['window']})" for x in s["indicators"] if x["window"] is not None)})
            st.dataframe(pd.DataFrame(rows), hide_index=True)
            if c["onset"] is not None and c["onset"] >= 0:
                st.caption(f"Début réel de l'épisode (étiquette) : fenêtre {c['onset']}. Les écarts entre étapes montrent quels indicateurs réagissent en premier.")
        else:
            st.info("Aucun chemin à afficher : pas d'hypothèse offensive à ce stade du rejeu.")

    with tabs[4]:
        truth = c["run_type"]
        def row(name, pred, how):
            ok = "—" if truth in (None, "inconnu", "unknown") else ("✅" if (pred == truth if truth in CATALOG else pred is None) else "❌")
            return {"système": name, "classe l'épisode comme": ATT_FR.get(pred, pred) if pred else "bénin / pas d'attaque", "conforme à la vérité": ok, "comment il décide": how}
        st.dataframe(pd.DataFrame([
            row("Baseline 1 : ML seul", c["baseline1_pred"], "toute alerte du ML est une attaque"),
            row("Baseline 2 : ML + LLM/RAG", c["baseline2_pred"], "le LLM/RAG dit si l'alerte ressemble à une attaque ou à un événement bénin"),
            row("EVA-Guard", c["eva_pred"], "le LLM propose, la règle d'indicateurs multi-sources confirme")]), hide_index=True)
        st.caption(f"Vérité terrain de ce run : {truth}. Un seul run ne prouve rien : les résultats chiffrés sont dans l'onglet « Résultats ».")

    with tabs[5]:
        st.code(c["report"], language="text")
        if decided:
            st.download_button("Télécharger le rapport (.txt)", c["report"], file_name=f"rapport_{c['run_id']}.txt", key=f"dl_{key}")


# ----------------------------------------------------------------------------- pages
def page_cases():
    p = ROOT / "results" / "cases.json"
    if not p.exists():
        st.error("results/cases.json introuvable : lancez d'abord `python run_all.py --figures`.")
        return
    cases = json.loads(p.read_text(encoding="utf-8"))
    title = st.selectbox("Scénario à rejouer", [c["title"] for c in cases])
    c = next(x for x in cases if x["title"] == title)
    st.caption(f"Run simulé « {c['run_id']} » — vérité terrain : {c['run_type']}. Ces cas sont fabriqués par le simulateur de métriques (aucun trafic réel).")
    render_case(c, "case")


@st.cache_resource(show_spinner="Entraînement du détecteur sur données simulées (quelques secondes)…")
def _sim_bench():
    from eva_guard.analyze import load_bench
    return load_bench(100)


@st.cache_resource(show_spinner="Entraînement sur vos runs normaux réels…")
def _real_bench(manifest, mtime):
    from eva_guard.analyze import bench_from_manifest
    return bench_from_manifest(manifest)


def page_analyze():
    from eva_guard.analyze import prepare_frame, case_from_frame
    st.markdown("<div class='box'>Chargez <b>votre propre trace</b> (CSV du collecteur : colonne <code>t</code> + les métriques) et faites-la passer dans la chaîne "
                "EVA-Guard. C'est aussi ici que vous pourrez analyser des <b>traces d'attaque fournies par l'encadrant</b> ou produites dans un environnement isolé validé.</div>",
                unsafe_allow_html=True)
    runs_dir = ROOT / "results" / "runs"
    local = sorted(p.name for p in runs_dir.glob("*.csv") if p.name not in ("manifest.csv", "real_check.csv")) if runs_dir.exists() else []
    left, right = st.columns(2)
    up = left.file_uploader("Fichier CSV", type="csv")
    pick = right.selectbox("…ou un run déjà enregistré (results/runs)", ["—"] + local)
    sample = pd.DataFrame({"t": range(5), **{f: [0.0] * 5 for f in FEATURES}})
    left.download_button("Télécharger un modèle de fichier (colonnes attendues)", sample.to_csv(index=False), file_name="modele_trace.csv")
    a, b, c3 = st.columns(3)
    truth = a.selectbox("Nature connue de la trace", ["inconnue", "normal", "eclipse", "dos_p2p", "benign_restart", "benign_burst"])
    onset = b.number_input("Fenêtre de début de l'épisode (si connue, sinon -1)", -1, 1000, -1)
    train = c3.radio("Référence de comportement normal", ["Données simulées (rapide)", "Mes runs normaux réels"],
                     help="La deuxième option apprend la baseline sur results/runs/manifest.csv (au moins 4 runs normaux utilisables).")
    df, name = None, None
    if up is not None:
        df, name = pd.read_csv(up), up.name
    elif pick != "—":
        df, name = pd.read_csv(runs_dir / pick), pick
    if df is None:
        st.info("Chargez un fichier pour lancer l'analyse.")
        return
    try:
        if train.startswith("Mes"):
            man = runs_dir / "manifest.csv"
            if not man.exists():
                st.error("results/runs/manifest.csv introuvable.")
                return
            bench, thr, rule = _real_bench(str(man), man.stat().st_mtime)
        else:
            bench, thr, rule = _sim_bench()
        g = prepare_frame(df, run_id=name, run_type=truth, onset=int(onset),
                          event_end=int(onset) + 40 if onset >= 0 else -1)
        case = case_from_frame(g, bench, rule, thr, title=name, truth=truth)
    except Exception as e:      # message clair plutôt qu'une trace Python
        st.error(f"Analyse impossible : {e}")
        return
    if train.startswith("Données"):
        st.caption("Référence simulée : sur une trace réelle, le niveau de base du nœud diffère souvent ; préférez « Mes runs normaux réels ».")
    st.success(f"{len(g)} fenêtres analysées ({len(g) * 10} s).")
    render_case(case, "upload")


def page_results():
    st.markdown("Résultats de l'évaluation **sur télémétrie simulée** (5 graines, 130 runs de test par graine) et contrôle sur traces **réelles bénignes**.")
    sp, ap = ROOT / "results" / "summary.json", ROOT / "results" / "ablation_summary.json"
    if sp.exists():
        s = pd.DataFrame(json.loads(sp.read_text(encoding="utf-8")))
        cols = {"system": "système", "precision_mean": "précision", "recall_mean": "rappel", "f1_mean": "F1", "fpr_mean": "taux de fausses alertes",
                "detect_time_s_mean": "délai de détection (s)", "confirm_time_s_mean": "délai de confirmation (s)"}
        st.subheader("Comparaison des trois systèmes")
        st.dataframe(s[[c for c in cols if c in s.columns]].rename(columns=cols).round(3), hide_index=True)
        st.caption("Lecture : le contexte LLM/RAG réduit les fausses alertes ; la confirmation multi-sources n'améliore pas encore ML + LLM/RAG sur ces données simulées.")
    if ap.exists():
        a = pd.DataFrame(json.loads(ap.read_text(encoding="utf-8")))
        st.subheader("Étude ablative")
        st.dataframe(a[[c for c in ["system", "precision_mean", "recall_mean", "f1_mean", "fpr_mean"] if c in a.columns]].round(3), hide_index=True)
    fig = ROOT / "results" / "figures"
    for f, cap in [("comparison.png", "Comparaison des systèmes"), ("fpr_by_type.png", "Fausses alertes par type d'événement bénin"),
                   ("sensitivity.png", "Sensibilité à l'intensité de l'épisode simulé (rappel)"), ("ablation.png", "Ablation"), ("importance.png", "Importance des variables")]:
        if (fig / f).exists():
            st.image(str(fig / f), caption=cap)
    rc = ROOT / "results" / "runs" / "real_check.csv"
    if rc.exists():
        st.subheader("Contrôle sur vos traces réelles")
        st.dataframe(pd.read_csv(rc).round(2), hide_index=True)
        st.caption("Normal / bénin : « taux » = fausses alertes. Types offensifs (si vous en avez ajouté) : « taux » = rappel.")


def page_help():
    st.markdown("""
### Comment fonctionne EVA-Guard
**Observation** (3 sources : P2P, système, RPC) → **détection ML** (Isolation Forest + Random Forest) → **hypothèse** (LLM + RAG sur des fiches de diagnostic) →
**preuves multi-sources** (catalogue fermé d'indicateurs) → **confirmation déterministe** (k indicateurs, ≥ 2 sources, persistance) → **explication** et recommandation.

Le LLM **ne confirme jamais** : il propose une hypothèse, et une règle explicite sur des mesures décide.

### Que veulent dire les verdicts
- **ATTAQUE CONFIRMÉE** : la règle de confirmation est satisfaite pour l'hypothèse.
- **ALERTE NON CONFIRMÉE** : le ML a vu une anomalie, mais les preuves manquent (ou l'hypothèse est bénigne).
- **AUCUNE ALERTE** : le score reste sous le seuil.

### Les métriques observées
""")
    st.dataframe(pd.DataFrame({"métrique": list(DESCRIPTION), "source": [SOURCE[f] for f in DESCRIPTION], "signification": list(DESCRIPTION.values()),
                               "utilisée": [f in FEATURES for f in DESCRIPTION]}), hide_index=True)
    st.markdown("""
### Limites à garder en tête
Résultats chiffrés sur **données simulées** ; traces réelles seulement bénignes (nœud unique) ; aucun rappel réel mesuré tant qu'aucune trace d'attaque autorisée n'est ajoutée.
Guide complet : `docs/GUIDE_COMPLET.md`.
""")


st.title("🛡️ EVA-Guard — détection et confirmation agentiques sur un nœud Ethereum")
t1, t2, t3, t4 = st.tabs(["Rejeu des scénarios", "Analyser une trace (CSV)", "Résultats", "Aide et architecture"])
with t1:
    page_cases()
with t2:
    page_analyze()
with t3:
    page_results()
with t4:
    page_help()
