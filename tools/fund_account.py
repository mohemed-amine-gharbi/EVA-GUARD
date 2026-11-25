"""Finance une adresse de TEST sur une chaîne de développement locale (geth --dev) depuis le compte de développement du nœud.

    py tools/fund_account.py --rpc http://127.0.0.1:8545 --to 0xVotreAdresseDeTest --eth 100

Le compte de développement de `geth --dev` est débloqué et financé d'office ; il sert uniquement à alimenter vos comptes de test.
À n'utiliser que sur un réseau local isolé (jamais sur un réseau public).
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_gen import rpc   # noqa: E402


def fund(url, to, eth=100.0, wait_s=30):
    accounts = rpc(url, "eth_accounts")
    if not accounts:
        raise RuntimeError("Aucun compte débloqué sur ce nœud (est-il lancé avec --dev ?).")
    value = hex(int(eth * 10 ** 18))
    txh = rpc(url, "eth_sendTransaction", [{"from": accounts[0], "to": to, "value": value}])
    t0 = time.time()
    while time.time() - t0 < wait_s:
        if rpc(url, "eth_getTransactionReceipt", [txh]):
            break
        time.sleep(1)
    else:
        raise RuntimeError(f"Transaction {txh} non minée après {wait_s} s (période de blocs --dev.period ?).")
    return int(rpc(url, "eth_getBalance", [to, "latest"]), 16) / 10 ** 18


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rpc", default="http://127.0.0.1:8545")
    ap.add_argument("--to", required=True)
    ap.add_argument("--eth", type=float, default=100.0)
    a = ap.parse_args()
    print(f"Solde de {a.to} : {fund(a.rpc, a.to, a.eth):.4f} ETH")


if __name__ == "__main__":
    main()
