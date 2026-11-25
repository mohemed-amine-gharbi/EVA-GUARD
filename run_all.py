"""Exécute toute la chaîne : évaluation (5 graines) -> figures -> dashboard statique -> rapport PDF.

    python run_all.py            # tout (environ 15-20 min, surtout la sélection de la règle sur 5 graines)
    python run_all.py --figures  # régénère figures + dashboard + PDF à partir des résultats déjà calculés
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    only_figs = "--figures" in sys.argv
    if not only_figs:
        from eva_guard.evaluate import run_experiment
        run_experiment()
    from eva_guard.plots import make_all
    make_all()
    if not (ROOT / "results" / "sensitivity.csv").exists():      # étude de sensibilité à l'intensité (~1 min)
        from eva_guard import sensitivity
        out = sensitivity.run(verbose=False)
        sensitivity.plot(out, ROOT / "results" / "figures" / "sensitivity.png")
    sys.path.insert(0, str(ROOT / "dashboard"))
    import make_static_dashboard
    make_static_dashboard.main()
    sys.path.insert(0, str(ROOT / "report"))
    import build_report
    build_report.main()


if __name__ == "__main__":
    main()
