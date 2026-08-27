"""Small CPU LSTM for Stage D multi-step forecasting."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np


def torch_available() -> bool:
    try:
        import torch  # noqa: F401

        return True
    except Exception:
        return False


def torch_required_strict() -> bool:
    """When HVAC_LSTM_REQUIRE_TORCH=1, APIs refuse without torch (no silent soft-fail)."""
    import os

    return os.getenv("HVAC_LSTM_REQUIRE_TORCH", "0").strip() in ("1", "true", "TRUE", "yes")


def torch_gate_message() -> Dict[str, Any]:
    return {
        "code": "TORCH_REQUIRED",
        "message": "Install torch: pip install -r backend/requirements-lstm.txt"
        + (" (HVAC_LSTM_REQUIRE_TORCH=1)" if torch_required_strict() else ""),
        "status": "MODEL_NOT_AVAILABLE",
        "wrote_setpoints": False,
    }


def _import_torch():
    import torch
    import torch.nn as nn

    return torch, nn


class LstmForecastNet:
    """Wrapper around nn.LSTM + Linear head. Requires torch at runtime."""

    def __init__(self, n_features: int, horizon: int, hidden: int = 32):
        torch, nn = _import_torch()
        self.n_features = int(n_features)
        self.horizon = int(horizon)
        self.hidden = int(hidden)

        class _Net(nn.Module):
            def __init__(self_inner):
                super().__init__()
                self_inner.lstm = nn.LSTM(
                    input_size=n_features,
                    hidden_size=hidden,
                    num_layers=1,
                    batch_first=True,
                )
                self_inner.head = nn.Linear(hidden, horizon)

            def forward(self_inner, x):
                out, _ = self_inner.lstm(x)
                last = out[:, -1, :]
                return self_inner.head(last)

        self._torch = torch
        self.net = _Net()

    def state_dict(self) -> Dict[str, Any]:
        return {k: v.detach().cpu().numpy() for k, v in self.net.state_dict().items()}

    def load_state_dict(self, state: Dict[str, Any]) -> None:
        torch, _nn = _import_torch()
        sd = {k: torch.tensor(v) for k, v in state.items()}
        self.net.load_state_dict(sd)

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        *,
        epochs: int = 40,
        lr: float = 1e-3,
        val_frac: float = 0.2,
    ) -> Dict[str, float]:
        torch, nn = _import_torch()
        n = X.shape[0]
        n_val = max(1, int(n * val_frac)) if n > 5 else 0
        if n_val and n_val < n:
            X_tr, y_tr = X[:-n_val], y[:-n_val]
            X_va, y_va = X[-n_val:], y[-n_val:]
        else:
            X_tr, y_tr = X, y
            X_va = y_va = None

        opt = torch.optim.Adam(self.net.parameters(), lr=lr)
        loss_fn = nn.MSELoss()
        self.net.train()
        xt = torch.tensor(X_tr, dtype=torch.float32)
        yt = torch.tensor(y_tr, dtype=torch.float32)
        for _ in range(max(1, epochs)):
            opt.zero_grad()
            pred = self.net(xt)
            loss = loss_fn(pred, yt)
            loss.backward()
            opt.step()

        metrics = {"train_mse": float(loss.detach().item())}
        self.net.eval()
        with torch.no_grad():
            if X_va is not None:
                pv = self.net(torch.tensor(X_va, dtype=torch.float32)).numpy()
                err = pv - y_va
                metrics["val_mae"] = float(np.mean(np.abs(err)))
                metrics["val_rmse"] = float(np.sqrt(np.mean(err**2)))
            else:
                pt = self.net(xt).numpy()
                err = pt - y_tr
                metrics["val_mae"] = float(np.mean(np.abs(err)))
                metrics["val_rmse"] = float(np.sqrt(np.mean(err**2)))
        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        torch, _nn = _import_torch()
        self.net.eval()
        with torch.no_grad():
            t = torch.tensor(X, dtype=torch.float32)
            return self.net(t).numpy()


def standardize_fit(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = X.reshape(-1, X.shape[-1]).mean(axis=0)
    std = X.reshape(-1, X.shape[-1]).std(axis=0)
    std = np.where(std < 1e-6, 1.0, std)
    Xs = (X - mean) / std
    return Xs, mean, std


def standardize_apply(X: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return (X - mean) / std
