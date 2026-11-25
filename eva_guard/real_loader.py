"""Charge des runs réels (CSV du collecteur + manifest.csv) au même schéma que le simulateur."""
from pathlib import Path
import numpy as np
import pandas as pd
from .config import FEATURES

NEEDED = ["run_id", "file", "run_type", "onset", "event_end"]


def load_runs(manifest_path, min_rows=30):
    manifest_path = Path(manifest_path)
    man = pd.read_csv(manifest_path)
    missing = [c for c in NEEDED if c not in man.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans {manifest_path.name} : {missing}")
    runs, skipped = [], []
    for r in man.itertuples():
        fp = manifest_path.parent / r.file
        if not fp.exists():
            print(f"  ignoré {r.run_id} : fichier introuvable ({r.file}) - corrigez ou supprimez cette ligne du manifeste")
            continue
        df = pd.read_csv(fp)
        if len(df) < min_rows:
            print(f"  ignoré {r.run_id} : {len(df)} lignes (< {min_rows})")
            continue
        absent = [f for f in FEATURES if f not in df.columns]
        if absent:
            raise ValueError(f"{r.file} : colonnes absentes {absent}")
        empty = [f for f in FEATURES if df[f].isna().all()]
        if empty:
            print(f"  ignoré {r.run_id} : colonnes vides {empty} (run enregistré sans ces métriques ; à refaire, ou "
                  f"retirez-les du modèle avec EVA_DROP_FEATURES=...)")
            skipped.append((r.file, empty))
            continue
        df = df[["t"] + FEATURES].copy()
        df[FEATURES] = df[FEATURES].interpolate(limit_direction="both")   # trous ponctuels
        df["t"] = np.arange(len(df))
        df.insert(0, "run_id", r.run_id)
        df["run_type"] = r.run_type
        df["onset"] = int(r.onset)
        df["event_end"] = int(r.event_end)
        df["in_event"] = (df["t"] >= r.onset) & (df["t"] < r.event_end) if r.onset >= 0 else False
        runs.append(df)
    if not runs:
        hint = ""
        if skipped:
            cols = sorted({c for _, e in skipped for c in e})
            hint = (f" Colonnes vides dans tous les runs : {cols}. Si elles ne sont pas collectables, lancez avec "
                    f"EVA_DROP_FEATURES={','.join(cols)} (PowerShell : $env:EVA_DROP_FEATURES=\"{','.join(cols)}\" ; "
                    f"WSL/Linux : export EVA_DROP_FEATURES={','.join(cols)}).")
        raise ValueError("Aucun run exploitable dans le manifeste." + hint)
    return pd.concat(runs, ignore_index=True)
