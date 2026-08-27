"""Classic RLS with forgetting factor. Never invents features or writes setpoints."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

_DEFAULT_LAMBDA = float(os.getenv("HVAC_RLS_LAMBDA", "0.995") or "0.995")
_DEFAULT_DELTA = float(os.getenv("HVAC_RLS_P_INIT", "1000") or "1000")
# Absolute residual gate; keep high enough for kW-scale HVAC_Power (temps stay well under this).
_DEFAULT_REJECT = float(os.getenv("HVAC_RLS_ERROR_REJECT", "500") or "500")


class RlsEngine:
    def __init__(
        self,
        n_features: int,
        *,
        lam: Optional[float] = None,
        delta: Optional[float] = None,
        error_reject: Optional[float] = None,
        theta: Optional[Sequence[float]] = None,
        p: Optional[Sequence[Sequence[float]]] = None,
    ) -> None:
        self.n = int(n_features)
        self.lam = float(lam if lam is not None else _DEFAULT_LAMBDA)
        self.lam = min(0.9999, max(0.9, self.lam))
        self.error_reject = float(error_reject if error_reject is not None else _DEFAULT_REJECT)
        d = float(delta if delta is not None else _DEFAULT_DELTA)
        if theta is not None and len(theta) == self.n:
            self.theta = np.asarray(theta, dtype=float).reshape(self.n)
        else:
            self.theta = np.zeros(self.n, dtype=float)
        if p is not None:
            mat = np.asarray(p, dtype=float)
            if mat.shape == (self.n, self.n):
                self.P = mat
            else:
                self.P = np.eye(self.n, dtype=float) * d
        else:
            self.P = np.eye(self.n, dtype=float) * d

    def predict(self, x: Sequence[float]) -> float:
        xv = np.asarray(x, dtype=float).reshape(self.n)
        return float(self.theta @ xv)

    def update(self, x: Sequence[float], y: float) -> Dict[str, Any]:
        xv = np.asarray(x, dtype=float).reshape(self.n)
        y_hat = float(self.theta @ xv)
        err = float(y) - y_hat
        rejected = abs(err) > self.error_reject
        if rejected or not np.isfinite(err) or not np.all(np.isfinite(xv)):
            return {
                "predicted": y_hat,
                "actual": float(y),
                "error": err,
                "rejected": True,
                "updated": False,
            }
        # K = P x / (λ + x' P x)
        Px = self.P @ xv
        denom = self.lam + float(xv @ Px)
        if denom <= 1e-12 or not np.isfinite(denom):
            return {
                "predicted": y_hat,
                "actual": float(y),
                "error": err,
                "rejected": True,
                "updated": False,
            }
        K = Px / denom
        self.theta = self.theta + K * err
        # P ← (P - K x' P) / λ
        self.P = (self.P - np.outer(K, xv) @ self.P) / self.lam
        # Keep P symmetric positive-ish
        self.P = 0.5 * (self.P + self.P.T)
        return {
            "predicted": y_hat,
            "actual": float(y),
            "error": err,
            "rejected": False,
            "updated": True,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theta": self.theta.tolist(),
            "p": self.P.tolist(),
            "lambda": self.lam,
            "n_features": self.n,
            "p_diag": np.diag(self.P).tolist(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], n_features: int) -> "RlsEngine":
        return cls(
            n_features,
            lam=data.get("lambda"),
            theta=data.get("theta"),
            p=data.get("p"),
        )
