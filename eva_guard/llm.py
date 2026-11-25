"""Agent d'interprétation : transforme une alerte en hypothèse d'attaque expliquée (LLM + RAG).

Deux backends :
- OfflineInterpreter : interprétation par récupération (RAG) sans réseau ; utilisé pour l'évaluation reproductible.
- MistralInterpreter : appelle l'API Mistral (variable MISTRAL_API_KEY) avec les fiches RAG ; repli sur l'offline
  en cas d'erreur. Non évalué dans les résultats du rapport (pas de clé ni de réseau pendant la rédaction).

Dans les deux cas, l'interprète PROPOSE une hypothèse ; il ne confirme rien.
"""
import json
import os
import requests
from .config import CATALOG, ATTACKS
from .schemas import Hypothesis

LABEL_TO_HYP = {"eclipse": "eclipse", "dos_p2p": "dos_p2p", "benign_restart": "benign", "benign_burst": "benign"}


def symptom_text(z, rel=None):
    """Décrit l'état des métriques en langage naturel.

    - topologie P2P, mémoire, erreurs, synchronisation : z-score par rapport à la baseline apprise ;
    - magnitudes de charge (messages, CPU, latence RPC) : rapport à l'historique récent du nœud lui-même
      (`rel`, calculé sur les fenêtres précédant l'alerte), pour ne pas confondre charge habituelle élevée
      et surcharge soudaine.
    """
    def g(f):
        return float(z.get(f, 0.0))   # feature retirée (EVA_DROP_FEATURES) -> neutre
    rel = rel or {f: 1.0 + max(0.0, float(z.get(f, 0.0))) * 0.2 for f in ("msgs_in", "cpu", "rpc_latency")}
    p = []
    p.append("diversité des pairs très faible" if g("peer_diversity") < -2 else "diversité des pairs normale")
    p.append("blocs reçus d'un seul pair" if g("single_source_ratio") > 2 else "blocs reçus de plusieurs pairs")
    p.append("churn de pairs élevé" if g("peer_churn") > 2 else "churn de pairs normal")
    p.append("très peu de pairs" if g("peer_count") < -5 else "nombre de pairs normal")
    p.append("retard de synchronisation" if g("sync_lag") > 2 else "synchronisation à jour")
    m, c, l = rel.get("msgs_in", 1.0), rel.get("cpu", 1.0), rel.get("rpc_latency", 1.0)
    p.append("flux de messages extrême" if m > 2.5 else "flux de messages élevé" if m > 1.3 else "flux de messages normal")
    p.append("CPU saturé" if c > 1.9 else "CPU élevé" if c > 1.3 else "CPU normal")
    p.append("mémoire en hausse" if g("mem") > 3 else "mémoire stable")
    p.append("latence RPC extrême" if l > 2.5 else "latence RPC élevée" if l > 1.3 else "latence RPC normale")
    p.append("erreurs RPC nombreuses" if g("rpc_error") > 3 else "aucune erreur RPC")
    return ", ".join(p)


class OfflineInterpreter:
    name = "offline-rag"

    def __init__(self, retriever):
        self.retriever = retriever

    def interpret(self, symptoms, retrieved=None, suspected=None):
        retrieved = retrieved or self.retriever.retrieve(symptoms, k=3)
        top = next((d for d in retrieved if d["label"] != "reference"), None)
        if top is None or top["score"] < 0.05:
            return Hypothesis("unknown", 0.0, "Aucune fiche de la base ne correspond aux symptômes observés.",
                              [d["id"] for d in retrieved], [], self.name)
        attack = LABEL_TO_HYP.get(top["label"], "unknown")
        rationale = (f"Symptômes : {symptoms}. La fiche « {top['title']} » est la plus proche "
                     f"(similarité {top['score']:.2f}).")
        if attack == "benign":
            rationale += " Hypothèse : comportement légitime, pas d'attaque."
        else:
            rationale += " Hypothèse : attaque plausible, à confirmer par des preuves indépendantes."
        ev = [list(x) for x in CATALOG.get(attack, [])]
        return Hypothesis(attack, top["score"], rationale, [d["id"] for d in retrieved], ev, self.name)


class MistralInterpreter:
    name = "mistral"

    def __init__(self, retriever, model="mistral-small-latest", api_key=None):
        self.retriever = retriever
        self.model = model
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        self.fallback = OfflineInterpreter(retriever)

    def interpret(self, symptoms, retrieved=None, suspected=None):
        retrieved = retrieved or self.retriever.retrieve(symptoms, k=3)
        if not self.api_key:
            return self.fallback.interpret(symptoms, retrieved, suspected)
        context = "\n\n".join(f"[{d['id']}] {d['title']}\n{d['text']}" for d in retrieved)
        prompt = (
            "Tu es un analyste sécurité Ethereum. À partir des symptômes et des fiches, propose UNE hypothèse.\n"
            f"Symptômes : {symptoms}\nType suggéré par le modèle ML : {suspected}\n\nFiches :\n{context}\n\n"
            'Réponds uniquement en JSON : {"attack": "eclipse|dos_p2p|benign|unknown", "confidence": 0..1, '
            '"rationale": "2 phrases"}. Tu ne confirmes jamais une attaque : tu proposes une hypothèse.'
        )
        try:
            r = requests.post("https://api.mistral.ai/v1/chat/completions",
                              headers={"Authorization": f"Bearer {self.api_key}"},
                              json={"model": self.model, "temperature": 0,
                                    "response_format": {"type": "json_object"},
                                    "messages": [{"role": "user", "content": prompt}]}, timeout=30)
            r.raise_for_status()
            data = json.loads(r.json()["choices"][0]["message"]["content"])
            attack = data.get("attack", "unknown")
            if attack not in ATTACKS + ["benign", "unknown"]:
                attack = "unknown"
            ev = [list(x) for x in CATALOG.get(attack, [])]
            return Hypothesis(attack, float(data.get("confidence", 0.0)), str(data.get("rationale", "")),
                              [d["id"] for d in retrieved], ev, self.name)
        except Exception as e:  # repli : on ne bloque jamais le pipeline
            h = self.fallback.interpret(symptoms, retrieved, suspected)
            h.rationale += f" (repli offline : {type(e).__name__})"
            return h
