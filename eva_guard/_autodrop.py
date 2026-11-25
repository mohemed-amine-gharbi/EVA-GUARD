"""Détecte automatiquement les colonnes entièrement vides des CSV réels et les retire du modèle (EVA_DROP_FEATURES).
Doit être importé AVANT eva_guard.config (qui lit la variable à l'import). Aucune action manuelle requise."""
import os
import sys
from pathlib import Path


def autodrop(manifest=None):
    try:
        import pandas as pd
        if manifest is None:
            argv = sys.argv
            manifest = argv[argv.index("--manifest") + 1] if "--manifest" in argv else "results/runs/manifest.csv"
        mp = Path(manifest)
        man = pd.read_csv(mp)
        counts, n = {}, 0
        for f in man["file"]:
            if not (mp.parent / f).exists():
                continue                                      # fichier absent : signalé par le chargeur
            d = pd.read_csv(mp.parent / f)
            n += 1
            for c in d.columns:
                if c != "t" and d[c].isna().all():
                    counts[c] = counts.get(c, 0) + 1
        empty = {c for c, k in counts.items() if k > n / 2}   # colonne vide dans la majorité des runs
        if empty:
            prev = {x for x in os.environ.get("EVA_DROP_FEATURES", "").split(",") if x}
            os.environ["EVA_DROP_FEATURES"] = ",".join(sorted(prev | empty))
            print("Colonnes vides retirées automatiquement :", ", ".join(sorted(empty)))
    except Exception as ex:                                   # ne jamais bloquer : le chargeur signalera le problème
        print("autodrop ignoré :", ex)
