import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from eva_guard.simulator import generate_dataset, make_run, SPLITS
from eva_guard.features import smooth, BaselineStats
from eva_guard.config import FEATURES, CATALOG
from eva_guard.agents import Rule, ConfirmationAgent, CorrelationAgent
from eva_guard.schemas import Evidence
from eva_guard.rag import Retriever
from eva_guard.llm import OfflineInterpreter, symptom_text
from eva_guard.evaluate import metrics_from_outcomes
import pandas as pd


SMALL = {"train": {"normal": 6, "eclipse": 4, "dos_p2p": 4}, "val": {"normal": 2}, "test": {"normal": 2, "eclipse": 2}}


def test_dataset_shape_and_labels():
    d = generate_dataset(1, SMALL)
    assert set(d) == {"train", "val", "test"}
    tr = d["train"]
    assert all(f in tr.columns for f in FEATURES)
    assert tr.groupby("run_id").size().eq(100).all()
    assert tr[tr.run_type == "normal"].in_event.sum() == 0
    assert tr[tr.run_type == "eclipse"].in_event.sum() > 0


def test_smoothing_is_causal():
    d = generate_dataset(2, SMALL)["train"]
    s = smooth(d)
    g, gs = d[d.run_id == d.run_id.iloc[0]], s[s.run_id == d.run_id.iloc[0]]
    assert np.isclose(gs["cpu"].iloc[5], g["cpu"].iloc[3:6].mean())


def test_confirmation_rule():
    ev = lambda name, src, ok: Evidence(name, src, 1.0, 0.5, "high", ok)
    agent = ConfirmationAgent(Rule(k=3, min_sources=2, persistence=2))
    assert agent.satisfied([ev("a", "P2P", True), ev("b", "SYS", True), ev("c", "RPC", True)])
    assert not agent.satisfied([ev("a", "P2P", True), ev("b", "P2P", True), ev("c", "P2P", True)])  # 1 seule source
    assert not agent.satisfied([ev("a", "P2P", True), ev("b", "SYS", True), ev("c", "RPC", False)])  # < k


def test_rag_retrieves_relevant_fiche():
    r = Retriever()
    top = r.retrieve("diversité des pairs très faible, blocs reçus d'un seul pair, retard de synchronisation", 1)[0]
    assert top["id"] == "eclipse"
    top = r.retrieve("flux de messages extrême, CPU saturé, erreurs RPC nombreuses, mémoire en hausse", 1)[0]
    assert top["id"] == "dos_p2p"


def test_interpreter_never_confirms():
    r = Retriever()
    h = OfflineInterpreter(r).interpret("flux de messages extrême, CPU saturé, erreurs RPC nombreuses")
    assert h.attack in ("dos_p2p", "benign", "unknown", "eclipse")


def test_catalog_is_closed_and_multisource():
    from eva_guard.config import SOURCE
    for attack, items in CATALOG.items():
        assert len(items) == 5
        assert len({SOURCE[f] for f, _ in items}) >= 2


def test_metrics():
    df = pd.DataFrame([
        dict(run_type="eclipse", onset=30, pred="eclipse", t_alert=32, t_decision=35),
        dict(run_type="dos_p2p", onset=30, pred=None, t_alert=None, t_decision=None),
        dict(run_type="normal", onset=-1, pred=None, t_alert=None, t_decision=None),
        dict(run_type="benign_burst", onset=30, pred="dos_p2p", t_alert=31, t_decision=31),
    ])
    m = metrics_from_outcomes(df)
    assert m["tp"] == 1 and m["fp"] == 1 and m["fn"] == 1
    assert abs(m["precision"] - 0.5) < 1e-9 and abs(m["recall"] - 0.5) < 1e-9
    assert m["detect_time_s"] == 20 and m["confirm_time_s"] == 30


class _H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        res = {"net_peerCount": "0x30", "eth_syncing": False,
               "admin_peers": [{"id": str(i), "network": {"remoteAddress": f"10.{i % 5}.1.2:30303"}} for i in range(10)]}
        out = json.dumps({"jsonrpc": "2.0", "id": 1, "result": res.get(body["method"])}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


def test_real_collector_against_mock_rpc():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collectors"))
    from collector import Collector
    srv = HTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    c = Collector(f"http://127.0.0.1:{srv.server_port}")
    row = c.sample()
    srv.shutdown()
    assert row["peer_count"] == 48
    assert row["sync_lag"] == 0.0
    assert abs(row["peer_diversity"] - 0.5) < 1e-9   # 5 sous-réseaux /16 pour 10 pairs
    assert row["rpc_error"] == 0
