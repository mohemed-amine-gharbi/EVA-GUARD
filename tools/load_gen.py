"""Générateur de charge LÉGITIME pour un réseau Ethereum privé de test : transferts d'ether de très faible valeur
entre adresses de test, à un débit contrôlé. Sert à produire les profils « repos / modérée / élevée / rafale légitime ».

Prérequis : pip install eth-account
Clé : une clé privée d'un compte PRÉFINANCÉ de votre réseau de test (jamais une clé réelle).
    python tools/load_gen.py --new-key                      # génère une clé de test + son adresse
    python tools/load_gen.py --rpc http://127.0.0.1:PORT --key 0x... --profile moderate --duration 120

Profils (transactions par seconde) : idle=0, moderate=2, high=8, burst=1 en fond puis 15 pendant la rafale.
Les débits sont des points de départ : ajustez-les à votre machine (--tps pour imposer un débit fixe).
"""
import argparse
import json
import os
import random
import threading
import time
import urllib.request

PROFILE_TPS = {"idle": 0.0, "moderate": 2.0, "high": 8.0, "restart": 2.0}
BURST_BASE, BURST_PEAK = 1.0, 15.0


def rpc(url, method, params=None, timeout=5):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data["result"]


def make_schedule(profile, burst_start_s=None, burst_end_s=None, tps=None):
    """Retourne f(t_secondes) -> débit (tx/s)."""
    if tps is not None:
        return lambda t: tps
    if profile == "burst":
        return lambda t: BURST_PEAK if burst_start_s <= t < burst_end_s else BURST_BASE
    base = PROFILE_TPS[profile]
    return lambda t: base


class Sender:
    def __init__(self, rpc_url, private_key):
        from eth_account import Account
        self.Account = Account
        self.url = rpc_url
        self.key = private_key
        self.addr = Account.from_key(private_key).address
        self.chain_id = int(rpc(rpc_url, "eth_chainId"), 16)
        self.nonce = int(rpc(rpc_url, "eth_getTransactionCount", [self.addr, "pending"]), 16)
        self.rng = random.Random(1)
        self.sent = self.errors = 0

    def send_one(self):
        try:
            gas_price = int(rpc(self.url, "eth_gasPrice"), 16) * 2
        except Exception:                       # nœud indisponible (ex. redémarrage) : on compte l'erreur et on continue
            self.errors += 1
            time.sleep(1.0)
            return
        from eth_utils import to_checksum_address
        to = to_checksum_address("0x" + "%040x" % self.rng.getrandbits(160))
        tx = {"nonce": self.nonce, "gasPrice": gas_price, "gas": 21000, "to": to, "value": 1, "chainId": self.chain_id}
        signed = self.Account.sign_transaction(tx, self.key)
        raw = getattr(signed, "raw_transaction", None)
        if raw is None:
            raw = signed.rawTransaction
        try:
            rpc(self.url, "eth_sendRawTransaction", ["0x" + bytes(raw).hex()])
            self.nonce += 1
            self.sent += 1
        except Exception:
            self.errors += 1
            try:
                self.nonce = int(rpc(self.url, "eth_getTransactionCount", [self.addr, "pending"]), 16)
            except Exception:
                time.sleep(1.0)


def run_load(sender, schedule, duration_s, stop=None):
    stop = stop or threading.Event()
    t0 = last = time.time()
    acc = 0.0
    while not stop.is_set() and time.time() - t0 < duration_s:
        now = time.time()
        acc += schedule(now - t0) * (now - last)
        last = now
        while acc >= 1.0 and not stop.is_set():
            sender.send_one()
            acc -= 1.0
        time.sleep(0.05)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--new-key", action="store_true", help="génère une clé de test et affiche l'adresse à préfinancer")
    ap.add_argument("--rpc", default="http://127.0.0.1:8545")
    ap.add_argument("--key", default=os.environ.get("EVA_PRIVATE_KEY"))
    ap.add_argument("--profile", choices=["idle", "moderate", "high", "restart", "burst"], default="moderate")
    ap.add_argument("--tps", type=float, default=None, help="impose un débit fixe (tx/s)")
    ap.add_argument("--duration", type=float, default=120)
    ap.add_argument("--burst-start", type=float, default=400, help="secondes (profil burst)")
    ap.add_argument("--burst-end", type=float, default=520, help="secondes (profil burst)")
    a = ap.parse_args()
    if a.new_key:
        from eth_account import Account
        acct = Account.create()
        print("Adresse (à préfinancer dans votre réseau de test) :", acct.address)
        print("Clé privée de TEST :", "0x" + bytes(acct.key).hex())
        return
    if not a.key:
        raise SystemExit("Clé manquante : --key 0x... ou variable EVA_PRIVATE_KEY (compte de test préfinancé).")
    s = Sender(a.rpc, a.key)
    print(f"Compte {s.addr}, chainId {s.chain_id}, profil {a.profile}")
    run_load(s, make_schedule(a.profile, a.burst_start, a.burst_end, a.tps), a.duration)
    print(f"Terminé : {s.sent} transactions envoyées, {s.errors} erreurs.")


if __name__ == "__main__":
    main()
