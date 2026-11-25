"""Agents de corrélation, confirmation et restitution + pipeline complet EVA-Guard."""
from dataclasses import dataclass
from .config import CATALOG, SOURCE, CONFIRM_TIMEOUT, DEFAULT_RULE, FEATURES
from .schemas import Alert, Hypothesis, Evidence, Decision
from .llm import symptom_text


@dataclass
class Rule:
    k: int = DEFAULT_RULE["k"]
    min_sources: int = DEFAULT_RULE["min_sources"]
    persistence: int = DEFAULT_RULE["persistence"]
    timeout: int = CONFIRM_TIMEOUT

    def to_dict(self):
        return dict(k=self.k, min_sources=self.min_sources, persistence=self.persistence, timeout=self.timeout)


class CorrelationAgent:
    """Rassemble, pour une hypothèse, les preuves du catalogue fermé à l'instant t."""

    def __init__(self, stats, excluded_sources=()):
        self.stats = stats
        self.excluded = set(excluded_sources)

    def collect(self, hypothesis_attack, row):
        pack = []
        for feat, direction in CATALOG.get(hypothesis_attack, []):
            if SOURCE[feat] in self.excluded:
                continue
            thr = self.stats.threshold(feat, direction)
            val = float(row[feat])
            passed = val > thr if direction == "high" else val < thr
            pack.append(Evidence(feat, SOURCE[feat], val, thr, direction, bool(passed)))
        return pack


class ConfirmationAgent:
    """Règle explicite : >= k indicateurs sur >= min_sources sources, persistants sur `persistence` fenêtres."""

    def __init__(self, rule: Rule):
        self.rule = rule

    def satisfied(self, pack):
        passed = [e for e in pack if e.passed]
        return len(passed) >= self.rule.k and len({e.source for e in passed}) >= self.rule.min_sources

    def decide(self, attack, run_smoothed, alert_t, correlation: CorrelationAgent):
        """Rejoue la confirmation en flux à partir de la première fenêtre anormale ; causal (jamais le futur)."""
        start = max(0, alert_t - 1)
        end = min(len(run_smoothed) - 1, alert_t + self.rule.timeout)
        streak, last_pack = 0, []
        for tau in range(start, end + 1):
            pack = correlation.collect(attack, run_smoothed.iloc[tau])
            last_pack = pack
            streak = streak + 1 if self.satisfied(pack) else 0
            if streak >= self.rule.persistence and tau >= alert_t:
                n = sum(e.passed for e in pack)
                return Decision("CONFIRMED", attack, tau,
                                f"{n}/{len(pack)} indicateurs concordants pendant {streak} fenêtres consécutives.",
                                pack, self.rule.to_dict())
        n = sum(e.passed for e in last_pack)
        return Decision("NOT_CONFIRMED", attack, end,
                        f"Règle non satisfaite dans le délai ({n}/{len(last_pack)} indicateurs concordants à la fin).",
                        last_pack, self.rule.to_dict())


class ReportAgent:
    """Génère le rapport lisible (gabarit déterministe ; un LLM peut le reformuler)."""

    @staticmethod
    def render(alert, hyp, decision):
        lines = []
        if alert is None:
            return "Aucune alerte : fonctionnement normal."
        lines.append(f"Alerte ML à la fenêtre {alert.t} (score {alert.score:.2f}).")
        lines.append(f"Hypothèse ({hyp.backend}) : {hyp.attack} — {hyp.rationale}")
        lines.append(f"Décision : {decision.verdict}. {decision.reason}")
        for e in decision.evidence:
            lines.append(f"  - {'OK ' if e.passed else 'non'} {e.indicator} [{e.source}] valeur {e.value:.3g}"
                         f" ({'>' if e.direction == 'high' else '<'} seuil {e.threshold:.3g})")
        if decision.verdict == "CONFIRMED":
            rec = {"eclipse": "Isoler le nœud, ajouter des pairs de confiance, vérifier la chaîne auprès d'une source indépendante.",
                   "dos_p2p": "Limiter le débit par pair, déconnecter les pairs bruyants, surveiller la mémoire."}.get(decision.attack, "")
            lines.append(f"Recommandation : {rec}")
        else:
            lines.append("Recommandation : surveiller ; aucune action corrective tant que les preuves manquent.")
        return "\n".join(lines)


class EvaGuard:
    """Chaîne complète. `mode` sélectionne le système évalué."""

    def __init__(self, detector, interpreter, stats, rule=None, mode="eva", excluded_sources=(), use_interpreter=True):
        self.detector = detector
        self.interpreter = interpreter
        self.stats = stats
        self.rule = rule or Rule()
        self.mode = mode
        self.use_interpreter = use_interpreter
        self.corr = CorrelationAgent(stats, excluded_sources)
        self.conf = ConfirmationAgent(self.rule)

    def relative_load(self, run_smoothed, t):
        """Rapport charge actuelle / historique récent du nœud (fenêtres t-30..t-8, avant l'épisode)."""
        lo, hi = max(0, t - 30), t - 8
        ref = run_smoothed.iloc[lo:hi] if hi - lo >= 3 else None
        cur = run_smoothed.iloc[t]
        out = {}
        for f in ("msgs_in", "cpu", "rpc_latency"):
            if f not in run_smoothed.columns:        # feature retirée (non collectable) : charge neutre
                out[f] = 1.0
                continue
            base = float(ref[f].median()) if ref is not None else float(self.stats.mean[f])
            out[f] = float(cur[f]) / max(base, 1e-9)
        return out

    def process_run(self, run_smoothed, scores=None):
        scores = self.detector.scores(run_smoothed) if scores is None else scores
        t = self.detector.first_alert(scores)
        if t is None:
            return dict(alert=None, hypothesis=None, decision=Decision("NO_ALERT", None, None, "Aucune alerte."),
                        pred=None, t_alert=None, t_decision=None, report="Aucune alerte : fonctionnement normal.")
        suspected, _ = self.detector.suspected_type(run_smoothed, t)
        alert = Alert(t, float(scores[t]), suspected, self.detector.top_features(run_smoothed, t))
        if self.mode == "ml_only":
            dec = Decision("CONFIRMED", suspected, t, "Alerte ML seule (aucune vérification).")
            return dict(alert=alert, hypothesis=None, decision=dec, pred=suspected, t_alert=t, t_decision=t,
                        report=ReportAgent.render(alert, Hypothesis(suspected or "unknown", 0, "ML seul", [], [], "ml"), dec))
        z = self.stats.z(run_smoothed.iloc[t: t + 1]).iloc[0]
        symptoms = symptom_text(z, self.relative_load(run_smoothed, t))
        if self.use_interpreter:
            hyp = self.interpreter.interpret(symptoms, suspected=suspected)
        else:
            hyp = Hypothesis(suspected or "unknown", 0.0, "Hypothèse = type suggéré par le ML (sans LLM/RAG).",
                             [], [list(x) for x in CATALOG.get(suspected, [])], "ml-type")
        attack = hyp.attack in CATALOG
        if self.mode == "ml_llm":
            verdict = "CONFIRMED" if attack else "NOT_CONFIRMED"
            dec = Decision(verdict, hyp.attack if attack else None, t, "Décision fondée sur l'hypothèse du LLM/RAG seule.")
            pred = hyp.attack if attack else None
            return dict(alert=alert, hypothesis=hyp, decision=dec, pred=pred, t_alert=t, t_decision=t,
                        report=ReportAgent.render(alert, hyp, dec))
        # mode "eva" : confirmation par preuves
        if not attack:
            dec = Decision("NOT_CONFIRMED", None, t, "Hypothèse non offensive (bénin/inconnu) : pas de confirmation demandée.")
        else:
            dec = self.conf.decide(hyp.attack, run_smoothed, t, self.corr)
        pred = dec.attack if dec.verdict == "CONFIRMED" else None
        return dict(alert=alert, hypothesis=hyp, decision=dec, pred=pred, t_alert=t, t_decision=dec.t_decision,
                    report=ReportAgent.render(alert, hyp, dec))
