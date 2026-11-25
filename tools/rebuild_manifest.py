"""Reconstruit results/runs/manifest.csv à partir des CSV présents dans results/runs/ (sans sous-dossiers).
Le profil est lu dans le début du nom de fichier (idle_, moderate_, high_, restart_, burst_), avec les mêmes
étiquettes que tools/run_session.py (fenêtre de début 40 ; redémarrage : +25 fenêtres ; rafale : +12 fenêtres).
    py tools/rebuild_manifest.py            # écrit results/runs/manifest.csv (ancien fichier sauvegardé en .bak)
"""
import csv
import shutil
import sys
from pathlib import Path

LABELS = {"idle": ("normal", -1, -1), "moderate": ("normal", -1, -1), "high": ("normal", -1, -1),
          "restart": ("benign_restart", 40, 65), "burst": ("benign_burst", 40, 52)}


def rebuild(runs_dir):
    runs_dir = Path(runs_dir)
    rows, skipped = [], []
    for f in sorted(runs_dir.glob("*.csv")):
        if f.name in ("manifest.csv", "real_check.csv"):
            continue
        prof = f.stem.split("_")[0]
        if prof not in LABELS:
            skipped.append(f.name)
            continue
        t, on, end = LABELS[prof]
        rows.append(dict(run_id=f.stem, file=f.name, run_type=t, onset=on, event_end=end))
    man = runs_dir / "manifest.csv"
    if man.exists():
        shutil.copy(man, man.with_suffix(".bak"))
    with open(man, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["run_id", "file", "run_type", "onset", "event_end"])
        w.writeheader()
        w.writerows(rows)
    return rows, skipped


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent.parent / "results" / "runs")
    rows, skipped = rebuild(d)
    for r in rows:
        print(f"{r['run_id']:32s} {r['run_type']:15s} onset={r['onset']} end={r['event_end']}")
    if skipped:
        print("Ignorés (nom non reconnu) :", ", ".join(skipped))
    print(f"{len(rows)} runs écrits dans {Path(d) / 'manifest.csv'}")
