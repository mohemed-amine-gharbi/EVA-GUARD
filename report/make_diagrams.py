"""Schémas du rapport technique (matplotlib) -> results/figures/architecture.png, rag_flow.png, confirmation.png"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FIG = Path(__file__).resolve().parent.parent / "results" / "figures"
ACC, INK, GREY = "#d1603d", "#222222", "#f2f2f2"


def box(ax, x, y, w, h, text, fc="#fdf1ec", ec=ACC, fs=8, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=INK, fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, text=None, fs=6.5):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=11, color="#555", lw=1.1))
    if text:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.13, text, ha="center", fontsize=fs, color="#444")


def architecture():
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.6); ax.axis("off")
    # sources
    for i, (t, y) in enumerate([("P2P\npairs, churn, messages", 4.5), ("Système\nCPU, mémoire, réseau", 3.55), ("RPC\nlatence, erreurs, retard", 2.6)]):
        box(ax, 0.1, y, 1.9, 0.75, t, fc=GREY, ec="#999", fs=7)
    box(ax, 0.1, 1.55, 1.9, 0.75, "Nœud Ethereum\n(Geth) ou simulateur", fc="#e8f0fa", ec="#4a78b0", fs=7)
    ax.text(1.05, 5.3, "OBSERVATION", ha="center", fontsize=8, fontweight="bold", color=ACC)
    box(ax, 2.5, 3.2, 1.6, 1.6, "Fenêtres de 10 s\n12 métriques\nlissage causal\n(3 fenêtres)", fs=7.5)
    arrow(ax, 2.0, 4.85, 2.5, 4.3); arrow(ax, 2.0, 3.9, 2.5, 4.0); arrow(ax, 2.0, 2.95, 2.5, 3.6)
    box(ax, 4.5, 3.2, 1.7, 1.6, "DÉTECTION ML\nIsolation Forest\n(anomalie)\n+ Random Forest\n(type suspecté)", fs=7.5, bold=False)
    arrow(ax, 4.1, 4.0, 4.5, 4.0)
    box(ax, 6.6, 3.2, 1.7, 1.6, "INTERPRÈTE\nLLM + RAG\nhypothèse :\neclipse / dos_p2p /\nbénin", fs=7.5)
    arrow(ax, 6.2, 4.0, 6.6, 4.0, "alerte")
    box(ax, 8.6, 3.2, 1.3, 1.6, "Base RAG\n6 fiches\nde diagnostic", fc=GREY, ec="#999", fs=7.5)
    arrow(ax, 8.6, 4.0, 8.3, 4.0)
    box(ax, 4.5, 0.9, 1.9, 1.5, "CORRÉLATION\ncatalogue fermé\nde 5 indicateurs\npar hypothèse", fs=7.5)
    arrow(ax, 7.4, 3.2, 6.4, 2.0, "hypothèse")
    arrow(ax, 2.0, 1.9, 4.5, 1.5, "séries lissées", fs=6.5)
    box(ax, 6.8, 0.9, 1.7, 1.5, "CONFIRMATION\nrègle déterministe\nk indicateurs\n≥ 2 sources\npersistance", fs=7.5, bold=False)
    arrow(ax, 6.4, 1.65, 6.8, 1.65)
    box(ax, 8.8, 0.9, 1.1, 1.5, "RESTITUTION\nrapport\n+ dashboard", fs=7.5)
    arrow(ax, 8.5, 1.65, 8.8, 1.65)
    ax.text(5, 0.35, "Le LLM propose une hypothèse ; il ne confirme jamais. La décision repose uniquement sur des mesures et une règle explicite.",
            ha="center", fontsize=8, style="italic", color=INK)
    fig.tight_layout(); fig.savefig(FIG / "architecture.png", dpi=170); plt.close(fig)


def rag_flow():
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 3.4); ax.axis("off")
    box(ax, 0.1, 1.2, 1.7, 1.2, "Alerte ML\nfenêtre t", fs=8)
    box(ax, 2.2, 1.2, 2.0, 1.2, "Texte de symptômes\n« diversité très faible,\nretard de synchro… »", fs=7.5)
    arrow(ax, 1.8, 1.8, 2.2, 1.8, "z-scores +\ncharge relative", fs=6)
    box(ax, 4.7, 1.9, 1.9, 0.9, "Index TF-IDF\n(mots + bigrammes)", fc=GREY, ec="#999", fs=7.5)
    box(ax, 4.7, 0.5, 1.9, 0.9, "6 fiches .md\n(knowledge/)", fc=GREY, ec="#999", fs=7.5)
    arrow(ax, 5.65, 1.4, 5.65, 1.9)
    arrow(ax, 4.2, 1.8, 4.7, 2.3)
    box(ax, 7.1, 1.2, 1.5, 1.2, "Top-3 fiches\nsimilarité\ncosinus", fs=7.5)
    arrow(ax, 6.6, 2.35, 7.1, 1.9)
    box(ax, 8.9, 1.9, 1.0, 0.9, "Offline :\nfiche #1", fs=7.5)
    box(ax, 8.9, 0.5, 1.0, 0.9, "Mistral :\nprompt JSON", fs=7.5)
    arrow(ax, 8.6, 1.9, 8.9, 2.3); arrow(ax, 8.6, 1.5, 8.9, 1.0)
    ax.text(5, 3.05, "Récupération (RAG) : les fiches servent de connaissance de référence ; l'interprète en tire une hypothèse expliquée", ha="center", fontsize=8.5, fontweight="bold", color=ACC)
    fig.tight_layout(); fig.savefig(FIG / "rag_flow.png", dpi=170); plt.close(fig)


def confirmation():
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 3.2); ax.axis("off")
    box(ax, 0.1, 1.1, 1.6, 1.0, "Hypothèse\n(ex. eclipse)", fs=8)
    box(ax, 2.1, 1.1, 2.0, 1.0, "Pour chaque fenêtre τ :\nmesurer les 5 indicateurs\nvs seuils (p1 / p99)", fs=7.5)
    arrow(ax, 1.7, 1.6, 2.1, 1.6)
    box(ax, 4.5, 1.1, 2.0, 1.0, "≥ k indicateurs\nET ≥ 2 sources ?", fs=8)
    arrow(ax, 4.1, 1.6, 4.5, 1.6)
    box(ax, 6.9, 1.9, 1.5, 0.8, "oui : série +1", fs=7.5)
    box(ax, 6.9, 0.5, 1.5, 0.8, "non : série = 0", fs=7.5)
    arrow(ax, 6.5, 1.8, 6.9, 2.3); arrow(ax, 6.5, 1.4, 6.9, 0.9)
    box(ax, 8.7, 1.9, 1.2, 0.8, "série ≥ p\n→ CONFIRMÉE", fc="#f6dcd6", fs=7.5)
    box(ax, 8.7, 0.5, 1.2, 0.8, "délai de 8 fenêtres\n→ NON CONFIRMÉE", fc="#fff4d6", ec="#d68910", fs=6.5)
    arrow(ax, 8.4, 2.3, 8.7, 2.3); arrow(ax, 8.4, 0.9, 8.7, 0.9)
    ax.text(5, 2.95, "Confirmation déterministe, causale (n'utilise jamais le futur)", ha="center", fontsize=8.5, fontweight="bold", color=ACC)
    fig.tight_layout(); fig.savefig(FIG / "confirmation.png", dpi=170); plt.close(fig)


if __name__ == "__main__":
    architecture(); rag_flow(); confirmation()
    print("schémas écrits dans", FIG)
