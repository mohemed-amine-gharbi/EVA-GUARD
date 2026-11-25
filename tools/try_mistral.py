"""Essaie l'interprète Mistral sur un cas du dashboard (sans clé : repli automatique sur l'interprète offline).

    $env:MISTRAL_API_KEY = "..."      # PowerShell
    py tools/try_mistral.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from eva_guard.llm import MistralInterpreter, OfflineInterpreter, symptom_text   # noqa: E402
from eva_guard.rag import Retriever   # noqa: E402
from eva_guard.features import BaselineStats   # noqa: E402
from eva_guard.analyze import load_bench   # noqa: E402

if __name__ == "__main__":
    bench, thr, rule = load_bench(100)
    cases = json.loads((ROOT / "results" / "cases.json").read_text(encoding="utf-8"))
    ret = Retriever()
    mis, off = MistralInterpreter(ret), OfflineInterpreter(ret)
    print("Clé Mistral détectée :", bool(mis.api_key))
    for c in cases:
        if c["t_alert"] is None:
            continue
        import pandas as pd
        from eva_guard.config import FEATURES
        g = pd.DataFrame({f: c["series"][f] for f in FEATURES})
        z = bench.stats.z(g.iloc[c["t_alert"]: c["t_alert"] + 1]).iloc[0]
        sym = symptom_text(z)
        hm, ho = mis.interpret(sym), off.interpret(sym)
        print(f"\n== {c['title']} (vérité : {c['run_type']})\n  offline : {ho.attack}\n  {hm.backend:8s}: {hm.attack}  — {hm.rationale[:160]}")
