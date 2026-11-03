"""XGBoost next-session conditional mean of squared daily log returns.

Tweedie regression (power 1.5) accepts zero/nonnegative targets and uses a log
link, avoiding the Jensen/retransformation bias of naively exponentiating a
regression on log squared returns. Targets are scaled by 10,000 for numerical
conditioning, then forecasts are converted back to decimal variance. A recorded
positive floor is a numerical safeguard, not an adjustment to observed returns.

Chronological blocked validation uses only labels available at the fitting
origin. Hyperparameters may be retuned during development, then are frozen.
Each asset owns its estimator, tuning history and fixed seed; no cross-asset data.
"""
from __future__ import annotations

import hashlib
import time

import numpy as np
import pandas as pd

from volrisk.forecasting.base import FIT_OK, FIT_WARNING, FitError, FitReport, VolatilityModel
from volrisk.forecasting.registry import register

FEATURE_NAMES = [
    "sq_return_lag1", "abs_return_lag1", "abs_return_lag2", "var_5", "var_20", "var_60", "ewma_094",
    "neg_return_lag1", "neg_count_5", "var_change_5_20", "var_change_20_60", "drawdown_60", "sq_return_lag2",
]


def build_lagged_features(log_returns: pd.Series, ewma_decay: float = 0.94, ewma_init: int = 20) -> pd.DataFrame:
    """Feature matrix aligned so that row t uses returns through t only.

    The target column ``target_sq_return_next`` is r_{t+1}^2 (NaN on the last row) and is
    provided for supervised training only; models must never read it at forecast time.
    """
    values = np.asarray(log_returns, dtype=float)
    if not np.isfinite(values).all():
        raise FitError("Features require a finite contiguous segment; missing observations must reset history")
    if not log_returns.index.is_unique or not log_returns.index.is_monotonic_increasing:
        raise FitError("Feature dates must be unique and increasing")
    if not 0 < ewma_decay < 1 or ewma_init < 2:
        raise ValueError("Invalid feature EWMA configuration")
    r = pd.Series(values, index=log_returns.index)
    sq = r ** 2
    frame = pd.DataFrame(index=r.index)
    frame["sq_return_lag1"] = sq
    frame["sq_return_lag2"] = sq.shift(1)
    frame["abs_return_lag1"] = r.abs()
    frame["abs_return_lag2"] = r.abs().shift(1)
    for window in (5, 20, 60):
        frame[f"var_{window}"] = r.rolling(window).var(ddof=1)
    h = np.full(len(r), np.nan)
    if len(r) >= ewma_init:
        h[ewma_init - 1] = float(np.mean(sq.values[:ewma_init]))
        for k in range(ewma_init, len(r)):
            h[k] = ewma_decay * h[k - 1] + (1 - ewma_decay) * sq.values[k]
    frame["ewma_094"] = h
    frame["neg_return_lag1"] = (r < 0).astype(float)
    frame["neg_count_5"] = (r < 0).astype(float).rolling(5).sum()
    frame["var_change_5_20"] = frame["var_5"] - frame["var_20"]
    frame["var_change_20_60"] = frame["var_20"] - frame["var_60"]
    cumulative = r.cumsum()
    frame["drawdown_60"] = cumulative - cumulative.rolling(60, min_periods=1).max()
    frame = frame[FEATURE_NAMES]
    frame["target_sq_return_next"] = sq.shift(-1)
    return frame



DEFAULT_SEARCH = [
    {"max_depth": 2, "n_estimators": 80},
    {"max_depth": 3, "n_estimators": 80},
    {"max_depth": 2, "n_estimators": 160},
]


def latest_features(values, ewma):
    """O(60) feature update exactly equivalent to the batch causal feature builder."""
    r = np.asarray(values, dtype=float)[-60:]
    if len(r) < 60 or not np.isfinite(r).all():
        raise FitError("Insufficient finite feature history")
    variances = {k: float(np.var(r[-k:], ddof=1)) for k in (5, 20, 60)}
    cumulative = np.cumsum(r)
    row = {"sq_return_lag1": r[-1] ** 2, "sq_return_lag2": r[-2] ** 2,
           "abs_return_lag1": abs(r[-1]), "abs_return_lag2": abs(r[-2]),
           "var_5": variances[5], "var_20": variances[20], "var_60": variances[60],
           "ewma_094": ewma, "neg_return_lag1": float(r[-1] < 0),
           "neg_count_5": float(np.sum(r[-5:] < 0)), "var_change_5_20": variances[5]-variances[20],
           "var_change_20_60": variances[20]-variances[60], "drawdown_60": cumulative[-1]-cumulative.max()}
    return pd.DataFrame([[row[n] for n in FEATURE_NAMES]], columns=FEATURE_NAMES)


@register("xgboost")
class XGBoostVolatility(VolatilityModel):
    family = "machine_learning"
    version = "1.0.0"
    supports_update = True

    def __init__(self, name, *, window=1500, min_observations=500, refit_every=21,
                 variance_floor=1e-10, target_scale=10000., seed=20261103,
                 hyperparameters=None, search_space=None, tuning_end="2021-12-31",
                 retune_every=252, cv_folds=2, cv_size=60, cv_min_train=100, min_train_samples=300):
        if window < min_observations or min_observations < min_train_samples + 60 or min_train_samples < 20:
            raise ValueError("Require window >= min_observations >= min_train_samples+60")
        if refit_every < 1 or retune_every < 1 or cv_folds < 1 or cv_size < 1 or cv_min_train < 20:
            raise ValueError("Invalid training/refit schedule")
        if not np.isfinite([variance_floor, target_scale]).all() or min(variance_floor, target_scale) <= 0:
            raise ValueError("Invalid variance floor or target scaling")
        supplied = dict(hyperparameters or {})
        allowed = {"n_estimators", "max_depth", "learning_rate", "min_child_weight", "reg_lambda", "max_bin"}
        grid = [dict(x) for x in (DEFAULT_SEARCH if search_space is None else search_space)]
        if not grid or len(grid) > 8 or set(supplied)-allowed or any(set(x)-allowed for x in grid):
            raise ValueError("Use a small search space of permitted tree parameters")
        super().__init__(name, window=int(window), min_observations=int(min_observations),
            refit_every=int(refit_every), variance_floor=float(variance_floor), target_scale=float(target_scale),
            seed=int(seed), hyperparameters=supplied, search_space=grid,
            tuning_end=str(pd.Timestamp(tuning_end).date()), retune_every=int(retune_every),
            cv_folds=int(cv_folds), cv_size=int(cv_size), cv_min_train=int(cv_min_train),
            min_train_samples=int(min_train_samples))
        self.reset()

    def reset(self):
        super().reset()
        self._estimator = None
        self._selected = None
        self._last_tune_n = None
        self._selection_date = None
        self._tail = []
        self._ewma = None
        self._origin = None
        self._last_prediction = {}

    def _new_estimator(self, chosen):
        from xgboost import XGBRegressor
        parameters = dict(n_estimators=80, max_depth=2, learning_rate=.03, min_child_weight=10.,
                          reg_lambda=10., max_bin=64)
        parameters.update(self._config["hyperparameters"])
        parameters.update(chosen)
        return XGBRegressor(**parameters, objective="reg:tweedie", tweedie_variance_power=1.5,
            tree_method="hist", device="cpu", n_jobs=1, random_state=self._config["seed"],
            subsample=1., colsample_bytree=1., verbosity=0)

    def _positive(self, raw):
        values = np.asarray(raw, dtype=float) / self._config["target_scale"]
        if not np.isfinite(values).all() or np.any(values < 0):
            raise FitError("Invalid XGBoost prediction; no replacement forecast used")
        return np.maximum(values, self._config["variance_floor"]), values < self._config["variance_floor"]

    def _tune(self, X, y, label_dates):
        n = len(y)
        width, folds = self._config["cv_size"], self._config["cv_folds"]
        first = n - folds * width
        if first < self._config["cv_min_train"]:
            raise FitError("Insufficient known training labels for chronological validation")
        scores = []
        for candidate in self._config["search_space"]:
            losses, fold_records, error = [], [], None
            try:
                for stop in range(first, n, width):
                    end = min(n, stop+width)
                    # Last training label is observed at the first validation forecast origin.
                    if label_dates[stop-1] > X.index[stop]:
                        raise FitError("Training target lies after validation forecast origin")
                    estimator = self._new_estimator(candidate)
                    estimator.fit(X.iloc[:stop], y[:stop] * self._config["target_scale"])
                    predictions, clipped = self._positive(estimator.predict(X.iloc[stop:end]))
                    losses.extend((np.log(predictions) + y[stop:end] / predictions).tolist())
                    fold_records.append({"training_label_end": label_dates[stop-1],
                        "validation_origin_start": X.index[stop], "validation_label_end": label_dates[end-1],
                        "train_samples": stop, "validation_samples": end-stop, "clipped_predictions": int(clipped.sum())})
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            scores.append({"hyperparameters": candidate, "mean_qlike": float(np.mean(losses)) if losses and error is None else None,
                           "folds": fold_records, "error": error})
        valid = [r for r in scores if r["mean_qlike"] is not None and np.isfinite(r["mean_qlike"])]
        if not valid:
            raise FitError(f"All chronological tuning candidates failed: {scores}")
        selected = min(valid, key=lambda r: r["mean_qlike"])
        return dict(selected["hyperparameters"]), scores

    def fit(self, returns, dates=None):
        tick = time.perf_counter()
        self._fitted = False
        values = self._as_array(returns)
        n = len(values)
        if n < self.min_observations:
            raise FitError("Insufficient XGBoost history")
        index = pd.RangeIndex(n) if dates is None else pd.DatetimeIndex(dates)
        frame = build_lagged_features(pd.Series(values, index=index))
        # Feature at k has label r[k+1]^2. Last row is never a training pair.
        start = max(59, n-self._config["window"]-1)
        training = frame.iloc[start:-1]
        X = training[FEATURE_NAMES]
        y = training["target_sq_return_next"].to_numpy(dtype=float)
        label_dates = index[start+1:]
        if len(X) < self._config["min_train_samples"] or not np.isfinite(X.to_numpy()).all() or not np.isfinite(y).all():
            raise FitError("Incomplete causal training features or labels")
        if np.mean(y) <= 0:
            raise FitError("All-zero training targets cannot identify positive variance")
        selection_allowed = dates is not None and index[-1] <= pd.Timestamp(self._config["tuning_end"])
        due = self._selected is None or (selection_allowed and n-self._last_tune_n >= self._config["retune_every"])
        cv, selection_note = [], "existing selection frozen"
        if due:
            if dates is None or selection_allowed:
                self._selected, cv = self._tune(X, y, label_dates)
                self._selection_date = None if dates is None else index[-1]
                selection_note = "chronological development validation"
            elif self._selected is None:
                # No training history before the selection cutoff: prespecified first candidate.
                self._selected = dict(self._config["search_space"][0])
                selection_note = "prespecified default; development tuning unavailable"
            self._last_tune_n = n
        estimator = self._new_estimator(self._selected)
        try:
            estimator.fit(X, y * self._config["target_scale"])
        except Exception as exc:
            raise FitError(f"XGBoost fit failed: {type(exc).__name__}: {exc}") from exc
        self._estimator = estimator
        self._tail = values[-60:].tolist()
        self._ewma = float(frame["ewma_094"].iloc[-1])
        self._origin = None if dates is None else index[-1]
        booster = estimator.get_booster()
        gains = booster.get_score(importance_type="gain")
        total = sum(gains.values())
        importance = {f: float(gains.get(f, 0.) / total) if total else 0. for f in FEATURE_NAMES}
        self._params = {"objective": "reg:tweedie", "tweedie_variance_power": 1.5,
            "hyperparameters": self._selected, "target_scale": self._config["target_scale"],
            "variance_floor": self._config["variance_floor"], "selection_date": self._selection_date,
            "booster_sha256": hashlib.sha256(booster.save_raw(raw_format="json")).hexdigest()}
        self._fitted = True
        self.forecast(1)
        diagnostics = {"feature_importance_gain_normalized": importance, "tuning_candidates": cv,
            "selection_note": selection_note, "training_feature_start": X.index[0],
            "training_feature_end": X.index[-1], "training_label_start": label_dates[0],
            "training_label_end": label_dates[-1], "origin": index[-1], "features": list(FEATURE_NAMES),
            "target": "next-session squared decimal log return", "boundary_flags": [],
            "prediction_floor_applied": self._last_prediction["prediction_clipped"]}
        status = FIT_WARNING if self._last_prediction["prediction_clipped"] else FIT_OK
        return FitReport(status=status, converged=True, params=self.params, diagnostics=diagnostics,
            training_start=None if dates is None else label_dates[0], training_end=None if dates is None else label_dates[-1],
            training_observations=len(X), runtime_seconds=time.perf_counter()-tick)

    def update(self, observed_return, date=None):
        self._require_fitted()
        if not np.isfinite(observed_return):
            raise FitError("Missing return breaks the XGBoost feature state")
        if date is not None and self._origin is not None and date <= self._origin:
            raise FitError("XGBoost updates must advance the origin date")
        self._tail = (self._tail + [float(observed_return)])[-60:]
        self._ewma = .94*self._ewma + .06*observed_return**2
        self._origin = date

    def forecast(self, horizon=1):
        self._require_fitted()
        if horizon != 1:
            raise NotImplementedError("XGBoost is a one-session supervised forecast")
        features = latest_features(self._tail, self._ewma)
        raw = self._estimator.predict(features)
        predicted, clipped = self._positive(raw)
        self._last_prediction = {"raw_variance": float(raw[0]/self._config["target_scale"]),
                                "prediction_clipped": bool(clipped[0]),
                                "features": features.iloc[0].to_dict(), "origin": self._origin}
        return predicted

    def state_diagnostics(self):
        return dict(self._last_prediction)


FUTURE_EXTENSIONS = {
    "lstm": "Sequence model on lagged returns; future research, not implemented.",
    "temporal_transformer": "Causal attention over lagged windows; future research, not implemented.",
}
