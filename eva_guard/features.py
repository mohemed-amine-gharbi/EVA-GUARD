"""Lissage, normalisation et seuils d'indicateurs appris sur la baseline normale."""
import numpy as np
import pandas as pd
from .config import FEATURES, SMOOTH, CATALOG


def smooth(df):
    """Moyenne glissante causale par run (n'utilise que le passé)."""
    parts = []
    for _, g in df.groupby("run_id", sort=False):
        g = g.copy()
        g[FEATURES] = g[FEATURES].rolling(SMOOTH, min_periods=1).mean()
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


class BaselineStats:
    """Moyenne/écart-type et quantiles de la baseline (fenêtres normales de l'entraînement)."""

    def __init__(self, train_smoothed):
        normal = train_smoothed[train_smoothed.run_type == "normal"]
        self.mean = normal[FEATURES].mean()
        self.std = normal[FEATURES].std().replace(0, 1e-9)
        self.q_high = normal[FEATURES].quantile(0.99)
        self.q_low = normal[FEATURES].quantile(0.01)

    def z(self, df):
        return (df[FEATURES] - self.mean) / self.std

    def threshold(self, feature, direction):
        return float(self.q_high[feature] if direction == "high" else self.q_low[feature])
