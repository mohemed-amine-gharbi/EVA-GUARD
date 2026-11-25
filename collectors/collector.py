"""Collecteur réel pour un nœud Geth (lecture seule, monitoring passif).

Interroge toutes les 5 s : le RPC JSON (net_peerCount, eth_syncing, eth_blockNumber, admin_peers, txpool_status),
l'endpoint de métriques Prometheus de Geth (--metrics) et l'état du processus (psutil), puis agrège par fenêtre
de 10 s au schéma de eva_guard.config.FEATURES et écrit un CSV.

Usage :
    python collectors/collector.py --rpc http://127.0.0.1:8545 --metrics http://127.0.0.1:6060/debug/metrics/prometheus \
        --pid <pid geth> --out results/real_run.csv --duration 3600

Limites (à documenter dans le rapport) :
- peer_diversity est calculée depuis admin_peers (IP distantes -> ratio de sous-réseaux /16 distincts) ;
- single_source_ratio nécessite l'observation des annonces de blocs par pair : non disponible via le RPC standard,
  la colonne est laissée vide (NaN) sauf si vous ajoutez un parseur de logs Geth ;
- ce collecteur est lecture seule : il n'envoie aucun trafic autre que des requêtes RPC/HTTP de monitoring.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import time
import urllib.request

FEATURES = ["peer_count", "peer_churn", "peer_diversity", "single_source_ratio", "msgs_in", "bytes_in",
            "cpu", "mem", "net_io", "rpc_latency", "rpc_error", "sync_lag"]


def rpc(url, method, params=None, timeout=3):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    return data.get("result"), (time.time() - t0) * 1000


def prom_counter(text, name):
    m = re.search(rf"^{re.escape(name)}\s+([0-9.eE+-]+)$", text, re.M)
    return float(m.group(1)) if m else None


def subnet16(enode_or_addr):
    m = re.search(r"(\d+\.\d+)\.\d+\.\d+", enode_or_addr or "")
    return m.group(1) if m else None


def docker_stats(container):
    """CPU % et mémoire % d'un conteneur via `docker stats` (nécessite le CLI docker). NaN si indisponible."""
    try:
        out = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}};{{.MemPerc}}", container],
                             capture_output=True, text=True, timeout=15).stdout.strip()
        cpu, mem = out.split(";")
        return float(cpu.strip("%")), float(mem.strip("%"))
    except Exception:
        return float("nan"), float("nan")


class Collector:
    def __init__(self, rpc_url, metrics_url=None, pid=None, container=None):
        self.rpc_url, self.metrics_url, self.container = rpc_url, metrics_url, container
        self.prev_peers, self.prev_prom, self.prev_t = set(), {}, None
        self.proc = None
        if pid:
            import psutil
            self.proc = psutil.Process(pid)
            self.proc.cpu_percent(None)

    def sample(self):
        now = time.time()
        row = dict.fromkeys(FEATURES, float("nan"))
        err = 0
        try:
            n, lat = rpc(self.rpc_url, "net_peerCount")
            row["peer_count"] = int(n, 16)
            row["rpc_latency"] = lat
        except Exception:
            err = 1
        try:
            s, _ = rpc(self.rpc_url, "eth_syncing")
            row["sync_lag"] = 0.0 if s is False else int(s["highestBlock"], 16) - int(s["currentBlock"], 16)
        except Exception:
            err = 1
        try:
            peers, _ = rpc(self.rpc_url, "admin_peers")
            ids = {p["id"] for p in peers}
            nets = [subnet16(p.get("network", {}).get("remoteAddress", "")) for p in peers]
            nets = [x for x in nets if x]
            row["peer_diversity"] = len(set(nets)) / max(len(nets), 1)
            row["peer_churn"] = len(ids ^ self.prev_peers)
            self.prev_peers = ids
        except Exception:
            err = 1
        row["rpc_error"] = err
        if self.metrics_url:
            try:
                text = urllib.request.urlopen(self.metrics_url, timeout=3).read().decode()
                cur = {"in": prom_counter(text, "p2p_ingress"), "msgs": prom_counter(text, "p2p_ingress_eth_66_0x02")}
                if self.prev_t and cur["in"] is not None and self.prev_prom.get("in") is not None:
                    dt = now - self.prev_t
                    row["bytes_in"] = (cur["in"] - self.prev_prom["in"]) / 1000 / dt
                    row["net_io"] = row["bytes_in"] * 0.008
                    if cur["msgs"] is not None and self.prev_prom.get("msgs") is not None:
                        row["msgs_in"] = (cur["msgs"] - self.prev_prom["msgs"]) / dt
                self.prev_prom = cur
            except Exception:
                pass
        if self.proc:
            row["cpu"] = self.proc.cpu_percent(None)
            row["mem"] = self.proc.memory_percent()
        elif self.container:
            row["cpu"], row["mem"] = docker_stats(self.container)
        self.prev_t = now
        return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rpc", default="http://127.0.0.1:8545")
    ap.add_argument("--metrics", default=None)
    ap.add_argument("--pid", type=int, default=None)
    ap.add_argument("--container", default=None, help="nom du conteneur Docker du nœud (CPU/mémoire via docker stats)")
    ap.add_argument("--out", default="results/real_run.csv")
    ap.add_argument("--duration", type=int, default=600)
    ap.add_argument("--interval", type=float, default=5.0)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)   # crée results/runs/ si besoin
    c = Collector(a.rpc, a.metrics, a.pid, a.container)
    buf, t0, win = [], time.time(), 0
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t"] + FEATURES)
        while time.time() - t0 < a.duration:
            buf.append(c.sample())
            if len(buf) >= int(10 / a.interval):
                agg = {k: sum(r[k] for r in buf if r[k] == r[k]) / max(1, sum(1 for r in buf if r[k] == r[k]))
                       if any(r[k] == r[k] for r in buf) else float("nan") for k in FEATURES}
                w.writerow([win] + [agg[k] for k in FEATURES])
                f.flush()
                buf, win = [], win + 1
            time.sleep(a.interval)


if __name__ == "__main__":
    main()
