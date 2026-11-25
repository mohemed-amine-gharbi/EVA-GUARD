"""Agent de détection (ML) : Isolation Forest (anomalie) + Random Forest (type suspecté)."""
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from .config import FEATURES, ATTACKS, ALERT_CONSEC


class Detector:
    def __init__(self, stats, seed=0):
        self.stats = stats
        self.seed = seed
        self.iforest = IsolationForest(n_estimators=200, random_state=seed)
        self.rf = RandomForestClassifier(n_estimators=200, random_state=seed)
        self.threshold = None

    def fit(self, train_smoothed):
        z = self.stats.z(train_smoothed)
        normal = train_smoothed.run_type == "normal"
        self.iforest.fit(z[normal].values)
        y = np.where(train_smoothed.in_event, train_smoothed.run_type, "normal")
        self.rf.fit(z.values, y)
        return self

    def scores(self, run_smoothed):
        """Score d'anomalie par fenêtre (plus grand = plus anormal)."""
        return -self.iforest.score_samples(self.stats.z(run_smoothed).values)

    def first_alert(self, scores, thr=None):
        """Index de la première fenêtre où le score dépasse le seuil ALERT_CONSEC fois de suite."""
        thr = self.threshold if thr is None else thr
        above = scores > thr
        for t in range(ALERT_CONSEC - 1, len(above)):
            if above[t - ALERT_CONSEC + 1: t + 1].all():
                return t
        return None

    def suspected_type(self, run_smoothed, t):
        """Type d'attaque le plus probable (hors classe 'normal') sur les fenêtres t-1..t."""
        z = self.stats.z(run_smoothed.iloc[max(0, t - 1): t + 1]).values
        proba = self.rf.predict_proba(z).mean(axis=0)
        classes = list(self.rf.classes_)
        best, best_p = None, -1
        for a in ATTACKS:
            if a in classes and proba[classes.index(a)] > best_p:
                best, best_p = a, proba[classes.index(a)]
        return best, float(best_p)

    def top_features(self, run_smoothed, t, k=5):
        z = self.stats.z(run_smoothed.iloc[t: t + 1]).iloc[0]
        order = z.abs().sort_values(ascending=False).index[:k]
        return [(f, float(z[f])) for f in order]
