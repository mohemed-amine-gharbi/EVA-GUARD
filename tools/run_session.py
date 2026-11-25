"""Enregistre UN run étiqueté : lance le collecteur, la charge légitime et (si besoin) le redémarrage du nœud, puis
ajoute la ligne correspondante à results/runs/manifest.csv.

Exemples (un run = 1000 s ≈ 100 fenêtres de 10 s) :
    python tools/run_session.py --profile idle     --rpc http://127.0.0.1:P1 --metrics http://127.0.0.1:P2/debug/metrics/prometheus --container el-1-geth-lighthouse
    python tools/run_session.py --profile moderate ... --key 0x...
    python tools/run_session.py --profile high     ... --key 0x...
    python tools/run_session.py --profile restart  ... --key 0x...   # redémarre le conteneur du nœud à la fenêtre 40
    python tools/run_session.py --profile burst    ... --key 0x...   # rafale légitime de la fenêtre 40 à 52

Étiquettes écrites dans le manifeste (mêmes noms que le simulateur) :
    idle / moderate / high -> run_type=normal (onset=event_end=-1)
    restart                -> run_type=benign_restart (onset = fenêtre du redémarrage, event_end = onset + 25, approximation de la durée de rattrapage)
    burst                  -> run_type=benign_burst   (onset/event_end = début/fin exacts de la rafale)
"""
import argparse
import csv
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import load_gen  # noqa: E402

WINDOW_S = 10
RESTART_RECOVERY_WINDOWS = 25
MANIFEST_COLS = ["run_id", "file", "run_type", "onset", "event_end"]


def append_manifest(path, row):
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        if new:
            w.writeheader()
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True, choices=["idle", "moderate", "high", "restart", "burst"])
    ap.add_argument("--rpc", required=True)
    ap.add_argument("--metrics", default=None)
    ap.add_argument("--container", default=None, help="conteneur Docker du nœud surveillé (docker stats + redémarrage)")
    ap.add_argument("--key", default=os.environ.get("EVA_PRIVATE_KEY"))
    ap.add_argument("--duration", type=int, default=1000)
    ap.add_argument("--onset-window", type=int, default=40)
    ap.add_argument("--burst-windows", type=int, default=12)
    ap.add_argument("--outdir", default=str(ROOT / "results" / "runs"))
    a = ap.parse_args()

    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    run_id = f"{a.profile}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    csv_path = out / f"{run_id}.csv"
    if a.profile != "idle" and not a.key:
        raise SystemExit("Clé de test manquante (--key ou EVA_PRIVATE_KEY) pour générer de la charge.")
    if a.profile == "restart" and not a.container:
        raise SystemExit("--container est obligatoire pour le profil restart.")

    onset_s = a.onset_window * WINDOW_S
    if a.profile == "burst":
        run_type, onset, end = "benign_burst", a.onset_window, a.onset_window + a.burst_windows
    elif a.profile == "restart":
        run_type, onset, end = "benign_restart", a.onset_window, a.onset_window + RESTART_RECOVERY_WINDOWS
    else:
        run_type, onset, end = "normal", -1, -1

    cmd = [sys.executable, str(ROOT / "collectors" / "collector.py"), "--rpc", a.rpc, "--out", str(csv_path),
           "--duration", str(a.duration)]
    if a.metrics:
        cmd += ["--metrics", a.metrics]
    if a.container:
        cmd += ["--container", a.container]
    print(f"[{run_id}] collecte de {a.duration} s -> {csv_path}")
    collector = subprocess.Popen(cmd)
    t0 = time.time()

    stop = threading.Event()
    load_thread = None
    if a.profile != "idle":
        sender = load_gen.Sender(a.rpc, a.key)
        sched = load_gen.make_schedule(a.profile, onset_s, onset_s + a.burst_windows * WINDOW_S)
        load_thread = threading.Thread(target=load_gen.run_load, args=(sender, sched, a.duration, stop), daemon=True)
        load_thread.start()

    if a.profile == "restart":
        time.sleep(max(0, onset_s - (time.time() - t0)))
        print(f"[{run_id}] redémarrage du conteneur {a.container} (fenêtre {a.onset_window})")
        subprocess.run(["docker", "restart", a.container], check=False)

    collector.wait()
    stop.set()
    if load_thread:
        load_thread.join(timeout=10)
    append_manifest(out / "manifest.csv", dict(run_id=run_id, file=csv_path.name, run_type=run_type, onset=onset, event_end=end))
    print(f"[{run_id}] terminé. Ligne ajoutée au manifeste ({run_type}, onset={onset}, event_end={end}).")


if __name__ == "__main__":
    main()
