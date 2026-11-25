"""Génère dashboard/dashboard.html : version autonome (sans serveur) des cas rejoués, à ouvrir dans un navigateur."""
import base64
import html
import io
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
FEATS = {"eclipse": ["peer_diversity", "sync_lag", "peer_churn"], "dos_p2p": ["msgs_in", "cpu", "mem"],
         "benign_burst": ["msgs_in", "cpu", "rpc_latency"], "benign_restart": ["peer_count", "sync_lag", "peer_churn"],
         "benign_maintenance": ["bytes_in", "cpu", "mem"]}


def chart(c):
    t = np.arange(len(c["scores"])) * 10
    fig, ax = plt.subplots(1, 2, figsize=(10, 2.8))
    ax[0].plot(t, c["scores"], color="#444", lw=1.1)
    ax[0].axhline(c["threshold"], color="#d1603d", ls="--", lw=1)
    ax[0].axvspan(c["onset"] * 10, c["event_end"] * 10, color="#f4d9d0", alpha=.6, label="épisode (vérité terrain)")
    if c["t_alert"] is not None:
        ax[0].axvline(c["t_alert"] * 10, color="#5b8fd1", label="alerte ML")
    if c["verdict"] == "CONFIRMED":
        ax[0].axvline(c["t_decision"] * 10, color="#3aa675", label="confirmation")
    ax[0].set_title("Score d'anomalie", fontsize=9)
    ax[0].legend(frameon=False, fontsize=7)
    for f in FEATS[c["run_type"]]:
        s = np.array(c["series"][f])
        m, sd = s[:20].mean(), s[:20].std()
        ax[1].plot(t, (s - m) / max(sd, 0.05 * abs(m), 1e-3), lw=1, label=f)
    ax[1].axvspan(c["onset"] * 10, c["event_end"] * 10, color="#f4d9d0", alpha=.6)
    ax[1].set_title("Métriques clés : écart à la baseline initiale (en écarts-types)", fontsize=9)
    ax[1].legend(frameon=False, fontsize=7)
    for a in ax:
        a.set_xlabel("temps (s)")
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def card(c):
    h = c["hypothesis"] or {}
    rows = "".join(
        f"<tr><td>{'✅' if e['passed'] else '—'}</td><td>{html.escape(e['indicator'])}</td><td>{e['source']}</td>"
        f"<td>{e['value']:.3g}</td><td>{'&gt;' if e['direction'] == 'high' else '&lt;'} {e['threshold']:.3g}</td></tr>"
        for e in c["evidence"])
    cls = "ok" if c["verdict"] == "CONFIRMED" else "no"
    return f"""
<section><h2>{html.escape(c['title'])} <small>— vérité terrain : {c['run_type']}</small></h2>
<img src="data:image/png;base64,{chart(c)}" alt="séries temporelles">
<div class="grid">
 <div><h3>Hypothèse (LLM + RAG)</h3><p><b>{html.escape(str(h.get('attack', '—')))}</b> ({html.escape(str(h.get('backend', '')))})</p>
  <p>{html.escape(str(h.get('rationale', '')))}</p></div>
 <div><h3>Paquet de preuves</h3><table><tr><th></th><th>indicateur</th><th>source</th><th>valeur</th><th>seuil</th></tr>{rows}</table></div>
 <div class="verdict {cls}"><h3>Décision EVA-Guard</h3><p><b>{c['verdict']}</b></p>
  <p>Baseline 1 (ML seul) : {c['baseline1_pred']}<br>Baseline 2 (ML + LLM/RAG) : {c['baseline2_pred']}<br>EVA-Guard : {c['eva_pred']}</p></div>
</div>
<pre>{html.escape(c['report'])}</pre></section>"""


def main():
    cases = json.loads((ROOT / "results" / "cases.json").read_text(encoding="utf-8"))
    css = """body{font-family:system-ui,sans-serif;max-width:1050px;margin:24px auto;padding:0 16px;color:#222}
    section{border:1px solid #ddd;border-radius:10px;padding:14px 18px;margin:18px 0}
    img{max-width:100%}.grid{display:grid;grid-template-columns:1fr 1.2fr .8fr;gap:16px}
    table{border-collapse:collapse;font-size:13px}td,th{border-bottom:1px solid #eee;padding:3px 8px;text-align:left}
    .verdict.ok{background:#fdecea;padding:8px;border-radius:8px}.verdict.no{background:#fff7e0;padding:8px;border-radius:8px}
    pre{background:#f6f6f6;padding:10px;border-radius:8px;white-space:pre-wrap;font-size:12px}small{font-weight:400;color:#666}"""
    body = "".join(card(c) for c in cases)
    page = (f"<!doctype html><html lang='fr'><meta charset='utf-8'><title>EVA-Guard — dashboard</title>"
            f"<style>{css}</style><h1>EVA-Guard — observation → détection → hypothèse → preuves → confirmation</h1>"
            f"<p>Cas rejoués sur le jeu de test (télémétrie simulée). Zone rose : épisode réel ; ligne bleue : alerte ML ; "
            f"ligne verte : confirmation.</p>{body}</html>")
    out = ROOT / "dashboard" / "dashboard.html"
    out.write_text(page, encoding="utf-8")
    print("écrit", out)


if __name__ == "__main__":
    main()
