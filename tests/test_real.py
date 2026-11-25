import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import numpy as np
import pandas as pd
from eva_guard.config import FEATURES
from eva_guard.simulator import make_run
from eva_guard.real_loader import load_runs
from eva_guard import real_check
import load_gen
import run_session


class _Rpc(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        m = body["method"]
        res = {"eth_chainId": "0x539", "eth_getTransactionCount": "0x0", "eth_gasPrice": "0x3b9aca00"}.get(m)
        if m == "eth_sendRawTransaction":
            _Rpc.received.append(body["params"][0])
            res = "0x" + "ab" * 32
        out = json.dumps({"jsonrpc": "2.0", "id": 1, "result": res}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


def test_schedule_profiles():
    assert load_gen.make_schedule("idle")(10) == 0
    assert load_gen.make_schedule("high")(10) == 8.0
    b = load_gen.make_schedule("burst", 100, 200)
    assert b(50) == load_gen.BURST_BASE and b(150) == load_gen.BURST_PEAK and b(250) == load_gen.BURST_BASE


def test_sender_signs_and_sends_legit_transfers():
    from eth_account import Account
    key = "0x" + bytes(Account.create().key).hex()
    srv = HTTPServer(("127.0.0.1", 0), _Rpc)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    s = load_gen.Sender(f"http://127.0.0.1:{srv.server_port}", key)
    assert s.chain_id == 1337
    load_gen.run_load(s, lambda t: 20.0, 0.6)
    srv.shutdown()
    srv.server_close()
    assert s.sent >= 5 and s.errors == 0
    assert all(r.startswith("0x") and len(r) > 100 for r in _Rpc.received)


def _export(tmp, types):
    rng = np.random.default_rng(5)
    rows = []
    for i, t in enumerate(types):
        df = make_run(t, f"r{i}", rng)
        name = f"r{i}.csv"
        df[["t"] + FEATURES].to_csv(tmp / name, index=False)
        on, end = (int(df.onset.iloc[0]), int(df.event_end.iloc[0])) if t != "normal" else (-1, -1)
        rows.append(dict(run_id=f"r{i}", file=name, run_type=t, onset=on, event_end=end))
    pd.DataFrame(rows).to_csv(tmp / "manifest.csv", index=False)
    return tmp / "manifest.csv"


def test_loader_and_real_check_roundtrip(tmp_path):
    man = _export(tmp_path, ["normal"] * 9 + ["benign_restart", "benign_burst"])
    df = load_runs(man)
    assert set(df.columns) >= {"run_id", "t", "run_type", "onset", "event_end", "in_event"} | set(FEATURES)
    assert df[df.run_type == "benign_burst"].in_event.sum() > 0
    res, summ = real_check.run(man, verbose=False)
    assert set(summ.system) == {"Baseline 1 : ML seul", "Baseline 2 : ML + LLM/RAG", "EVA-Guard"}
    assert {"normal", "benign_restart", "benign_burst"} <= set(summ.run_type)


def test_loader_explains_empty_column(tmp_path):
    man = _export(tmp_path, ["normal"] * 2)
    for n in ("r0.csv", "r1.csv"):
        f = tmp_path / n
        d = pd.read_csv(f)
        d["peer_diversity"] = np.nan
        d.to_csv(f, index=False)
    try:
        load_runs(man)
        assert False
    except ValueError as e:
        assert "EVA_DROP_FEATURES" in str(e)


def test_manifest_append(tmp_path):
    p = tmp_path / "manifest.csv"
    run_session.append_manifest(p, dict(run_id="a", file="a.csv", run_type="normal", onset=-1, event_end=-1))
    run_session.append_manifest(p, dict(run_id="b", file="b.csv", run_type="benign_burst", onset=40, event_end=52))
    d = pd.read_csv(p)
    assert list(d.columns) == run_session.MANIFEST_COLS and len(d) == 2


def test_loader_skips_run_with_empty_column_when_others_ok(tmp_path):
    man = _export(tmp_path, ["normal"] * 3)
    f = tmp_path / "r0.csv"
    d = pd.read_csv(f)
    d["bytes_in"] = np.nan
    d.to_csv(f, index=False)
    df = load_runs(man)
    assert set(df.run_id) == {"r1", "r2"}


def test_analyze_trace_and_real_bench(tmp_path):
    from eva_guard.analyze import prepare_frame, case_from_frame, bench_from_manifest, load_bench
    man = _export(tmp_path, ["normal"] * 8 + ["benign_burst"])
    bench, thr, rule = bench_from_manifest(man)
    raw = pd.read_csv(tmp_path / "r8.csv")
    case = case_from_frame(prepare_frame(raw), bench, rule, thr, truth="benign_burst")
    for key in ("verdict", "timeline", "path", "series", "scores", "evidence", "rule", "top_features"):
        assert key in case
    assert len(case["scores"]) == len(raw)


def test_attack_path_orders_observed_effects():
    from eva_guard.analyze import prepare_frame, case_from_frame, load_bench
    b, thr, rule = load_bench(100)
    rng = np.random.default_rng(1)
    raw = make_run("eclipse", "x", rng, intensity=0.9)
    case = case_from_frame(prepare_frame(raw[["t"] + FEATURES]), b, rule, thr, truth="eclipse")
    wins = [s["first_window"] for s in case["path"] if s["first_window"] is not None]
    assert case["path_attack"] == "eclipse" and wins == sorted(wins) and len(wins) >= 2


def test_intensity_scales_effect():
    rng1, rng2 = np.random.default_rng(3), np.random.default_rng(3)
    weak = make_run("dos_p2p", "a", rng1, intensity=0.2)
    strong = make_run("dos_p2p", "b", rng2, intensity=1.0)
    assert strong.msgs_in.max() > weak.msgs_in.max()


def test_fund_account_with_mock_rpc():
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            res = {"eth_accounts": ["0x" + "11" * 20], "eth_sendTransaction": "0x" + "ab" * 32,
                   "eth_getTransactionReceipt": {"status": "0x1"}, "eth_getBalance": hex(100 * 10 ** 18)}.get(body["method"])
            out = json.dumps({"jsonrpc": "2.0", "id": 1, "result": res}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(out)

        def log_message(self, *a):
            pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    import fund_account
    bal = fund_account.fund(f"http://127.0.0.1:{srv.server_port}", "0x" + "22" * 20, 100)
    srv.shutdown()
    assert bal == 100.0


def test_make_scenarios_loadable(tmp_path):
    import make_scenarios
    make_scenarios.generate(tmp_path, levels=(0.5,), n=1)
    df = load_runs(tmp_path / "manifest.csv")
    assert {"eclipse", "dos_p2p", "normal"} <= set(df.run_type)
