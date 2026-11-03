"""Per-asset diagnostic figures for walk-forward volatility forecasts.

Each model keeps one fixed colour across every figure; Student-t variants use
the hue of their Gaussian counterpart with a dashed line. Realized references
are grey. Every figure uses a single y-axis per panel.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from volrisk.forecasting.base import FIT_FAILED  # noqa: E402

PALETTE = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100", "magenta": "#e87ba4",
           "green": "#008300", "violet": "#4a3aa7", "red": "#e34948"}
MODEL_STYLE = {
    "expanding": (PALETTE["violet"], "-"), "rolling_20": (PALETTE["yellow"], "-"), "rolling_60": (PALETTE["yellow"], "--"),
    "ewma_094": (PALETTE["magenta"], "-"),
    "garch_normal": (PALETTE["blue"], "-"), "garch_t": (PALETTE["blue"], "--"),
    "egarch_normal": (PALETTE["orange"], "-"), "egarch_t": (PALETTE["orange"], "--"),
    "gjr_normal": (PALETTE["aqua"], "-"), "gjr_t": (PALETTE["aqua"], "--"),
    "markov_switching_2": (PALETTE["green"], "-"), "xgboost_v1": (PALETTE["red"], "-"),
}
FALLBACK_STYLES = [(PALETTE["green"], "-"), (PALETTE["red"], "-"), (PALETTE["green"], "--"), (PALETTE["red"], "--")]
GREY, INK, MUTED = "#9a9a97", "#0b0b0b", "#52514e"
FOOTER = "Walk-forward forecasts: every value uses returns through its origin only. Sealed periods are excluded."


def model_style(model: str, index: int) -> tuple[str, str]:
    return MODEL_STYLE.get(model, FALLBACK_STYLES[index % len(FALLBACK_STYLES)])


def _models(frame: pd.DataFrame) -> list[str]:
    return sorted(frame["model"].unique())


def _save(fig, directory: Path, asset: str, name: str, output: list[Path]) -> None:
    fig.text(0.01, 0.005, FOOTER, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    path = directory / f"{asset}_{name}.png"
    fig.savefig(path, dpi=140, metadata={"Software": "NEXUS Sprint 2"})
    plt.close(fig)
    output.append(path)


def _legend(ax, **kwargs):
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, fontsize=7, frameon=False, **kwargs)


def _wide(frame: pd.DataFrame, value: str, common_only: bool = True) -> pd.DataFrame:
    rows = frame[frame["common"].astype(bool)] if common_only else frame
    return rows.pivot(index="target_date", columns="model", values=value).sort_index()


def make_figures(frame: pd.DataFrame, fits: pd.DataFrame, *, asset: str, directory: Path, benchmark: str,
                 metrics: pd.DataFrame | None = None, rolling_window: int = 252, sessions_per_year: int = 252) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    output: list[Path] = []
    frame = frame.sort_values(["model", "origin_date"])
    models = _models(frame)
    if not models or not frame["target_observed"].astype(bool).any():
        return output
    styles = {m: model_style(m, i) for i, m in enumerate(models)}
    best = benchmark
    if metrics is not None and not metrics.empty:
        rows = metrics[(metrics["asset"] == asset) & (metrics["period"] == "all") & (metrics["sample"] == "common")]
        if not rows.empty and rows["qlike"].notna().any():
            best = rows.sort_values("qlike").iloc[0]["model"]
    realized = frame.drop_duplicates("target_date").set_index("target_date")["realized_log_return"].sort_index()
    realized = realized.dropna()
    realized_vol = np.sqrt((realized ** 2).rolling(21).mean() * sessions_per_year) * 100
    vol_wide = _wide(frame, "forecast_volatility_annualized", common_only=False) * 100
    subtitle = f"{asset} | out-of-sample, unsealed periods only"

    with plt.rc_context({"axes.grid": True, "grid.alpha": 0.18, "font.size": 9, "axes.edgecolor": MUTED,
                         "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED}):
        # 1. returns and predicted volatility -------------------------------------------------------------
        fig, axes = plt.subplots(2, 1, figsize=(12, 6.5), sharex=True)
        axes[0].plot(realized.index, realized * 100, lw=0.5, color=GREY)
        axes[0].set_ylabel("daily log return (%)")
        axes[0].set_title("Daily returns and one-step-ahead volatility forecasts — " + subtitle, fontsize=10)
        shown = [m for m in dict.fromkeys([benchmark, best, "ewma_094", "rolling_20"]) if m in vol_wide.columns]
        for m in shown:
            axes[1].plot(vol_wide.index, vol_wide[m], lw=1.1, color=styles[m][0], ls=styles[m][1], label=m)
        axes[1].plot(realized_vol.index, realized_vol, lw=0.9, color=GREY, label="realized 21-session (retrospective)")
        axes[1].set_ylabel("annualized volatility (%)")
        axes[1].set_xlabel("target session")
        _legend(axes[1], loc="upper left")
        _save(fig, directory, asset, "returns_and_forecast_vol", output)

        # 2. forecast comparison across models -------------------------------------------------------------
        fig, axes = plt.subplots(2, 1, figsize=(12, 7))
        for m in models:
            axes[0].plot(vol_wide.index, vol_wide[m], lw=0.8, color=styles[m][0], ls=styles[m][1], label=m)
        axes[0].set_title("Forecast comparison, all models — " + subtitle, fontsize=10)
        axes[0].set_ylabel("annualized volatility (%)")
        _legend(axes[0], ncol=5, loc="upper left")
        tail = vol_wide.iloc[-min(len(vol_wide), 2 * rolling_window):]
        for m in models:
            axes[1].plot(tail.index, tail[m], lw=1.0, color=styles[m][0], ls=styles[m][1], label=m)
        axes[1].plot(realized_vol.loc[tail.index.min():tail.index.max()].index,
                     realized_vol.loc[tail.index.min():tail.index.max()], lw=0.9, color=GREY, label="realized 21-session")
        axes[1].set_title(f"Last {len(tail)} evaluated sessions", fontsize=9)
        axes[1].set_ylabel("annualized volatility (%)")
        axes[1].set_xlabel("target session")
        _save(fig, directory, asset, "forecast_comparison", output)

        # 3. forecast vs observed variance -----------------------------------------------------------------
        common = frame[frame["common"].astype(bool) & frame["evaluable"].astype(bool)]
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        for m in [benchmark, best] if best != benchmark else [benchmark]:
            rows = common[common["model"] == m]
            axes[0].scatter(np.log10(rows["forecast_variance"]), np.log10(rows["realized_squared_return"].clip(lower=1e-12)),
                            s=5, alpha=0.25, color=styles[m][0], label=m, edgecolors="none")
        lims = axes[0].get_xlim()
        axes[0].plot(lims, lims, color=GREY, lw=0.8, ls=":")
        axes[0].set(xlabel="log10 forecast variance", ylabel="log10 realized squared return",
                    title="Forecast vs realized squared return (noisy proxy)")
        _legend(axes[0])
        for m in models:
            rows = common[common["model"] == m].sort_values("forecast_variance")
            if len(rows) < 50:
                continue
            bins = pd.qcut(rows["forecast_variance"], 10, labels=False, duplicates="drop")
            grouped = rows.groupby(bins).agg(h=("forecast_variance", "mean"), r2=("realized_squared_return", "mean"))
            axes[1].plot(np.sqrt(grouped["h"] * sessions_per_year) * 100, np.sqrt(grouped["r2"] * sessions_per_year) * 100,
                         marker="o", ms=3, lw=1, color=styles[m][0], ls=styles[m][1], label=m)
        lims = axes[1].get_xlim()
        axes[1].plot(lims, lims, color=GREY, lw=0.8, ls=":")
        axes[1].set(xlabel="mean forecast volatility in decile (% annualized)",
                    ylabel="realized volatility in decile (% annualized)", title="Decile calibration (common dates)")
        _legend(axes[1], ncol=2)
        fig.suptitle("Forecast vs observed variance — " + subtitle, fontsize=10)
        _save(fig, directory, asset, "forecast_vs_realized", output)

        # 4. cumulative QLIKE difference vs benchmark ------------------------------------------------------
        loss_wide = _wide(frame[frame["evaluable"].astype(bool)], "loss_qlike")
        fig, ax = plt.subplots(figsize=(12, 5))
        if benchmark in loss_wide.columns:
            for m in models:
                if m == benchmark or m not in loss_wide.columns:
                    continue
                diff = (loss_wide[m] - loss_wide[benchmark]).cumsum()
                ax.plot(diff.index, diff, lw=1.0, color=styles[m][0], ls=styles[m][1], label=m)
            ax.axhline(0, color=GREY, lw=0.8)
        ax.set(title=f"Cumulative QLIKE difference vs {benchmark} (negative = better than benchmark) — " + subtitle,
               ylabel="cumulative QLIKE difference", xlabel="target session (common dates)")
        _legend(ax, ncol=3, loc="upper left")
        _save(fig, directory, asset, "cumulative_qlike", output)

        # 5. calibration by period -----------------------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(12, 4.5))
        if metrics is not None and not metrics.empty:
            rows = metrics[(metrics["asset"] == asset) & (metrics["sample"] == "common")]
            periods = [p for p in ["all", "development", "validation", "holdout"] if p in set(rows["period"])]
            width = 0.8 / max(1, len(models))
            for i, m in enumerate(models):
                values = [rows[(rows["model"] == m) & (rows["period"] == p)]["calibration_ratio"].mean() for p in periods]
                ax.bar(np.arange(len(periods)) + i * width - 0.4 + width / 2, values, width=width * 0.9,
                       color=styles[m][0], alpha=0.9 if styles[m][1] == "-" else 0.5, label=m)
            ax.set_xticks(np.arange(len(periods)))
            ax.set_xticklabels(periods)
            ax.axhline(1.0, color=GREY, lw=0.8)
        ax.set(title="Calibration ratio = mean realized r² / mean forecast variance (1 = calibrated; >1 under-forecast) — "
                     + subtitle, ylabel="calibration ratio")
        _legend(ax, ncol=5)
        _save(fig, directory, asset, "calibration", output)

        # 6. extreme-volatility case studies -------------------------------------------------------------------
        shocks = frame.drop_duplicates("target_date").set_index("target_date")
        shocks = shocks[shocks["shock"].astype(bool)] if "shock" in shocks.columns else shocks.iloc[0:0]
        chosen = []
        for day in shocks["realized_log_return"].abs().sort_values(ascending=False).index:
            if all(abs(realized.index.get_indexer([day])[0] - realized.index.get_indexer([c])[0]) > 40 for c in chosen):
                chosen.append(day)
            if len(chosen) == 3:
                break
        n = max(1, len(chosen))
        fig, axes = plt.subplots(n, 1, figsize=(12, 3.4 * n), squeeze=False)
        for ax, day in zip(axes[:, 0], chosen):
            pos = realized.index.get_indexer([day])[0]
            window = realized.iloc[max(0, pos - 30): pos + 61]
            ax.bar(window.index, window.abs() * 100, width=1.0, color=GREY, label="|daily log return| (%)")
            local = vol_wide.loc[window.index.min(): window.index.max()] / np.sqrt(sessions_per_year)
            for m in models:
                ax.plot(local.index, local[m], lw=1.0, color=styles[m][0], ls=styles[m][1], label=m)
            ax.axvline(day, color=INK, lw=0.8, ls="--")
            ax.set_title(f"Shock {pd.Timestamp(day).date()} | realized {realized.loc[day] * 100:+.2f}% | forecast daily vol (%)",
                         fontsize=9)
            ax.set_ylabel("daily volatility (%)")
        if not chosen:
            axes[0, 0].text(0.1, 0.5, "No retrospective shock sessions in the evaluated sample.", transform=axes[0, 0].transAxes)
        _legend(axes[0, 0], ncol=4, loc="upper left")
        fig.suptitle("Extreme-volatility case studies (shock = |r| > k trailing sd, labelled retrospectively) — " + subtitle,
                     fontsize=10)
        _save(fig, directory, asset, "extreme_case_studies", output)

        # 7. estimation stability ----------------------------------------------------------------------------
        est = fits[fits["persistence"].notna()] if "persistence" in fits.columns else fits.iloc[0:0]
        fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
        for m in models:
            rows = est[(est["model"] == m)].sort_values("origin_date")
            if rows.empty:
                continue
            ok = rows[rows["status"] != FIT_FAILED]
            axes[0].plot(ok["origin_date"], ok["persistence"], lw=1.0, marker=".", ms=3, color=styles[m][0],
                         ls=styles[m][1], label=m)
            params = pd.DataFrame([json.loads(p) for p in ok["params"]], index=ok["origin_date"])
            if "alpha[1]" in params.columns:
                axes[1].plot(params.index, params["alpha[1]"], lw=1.0, color=styles[m][0], ls=styles[m][1], label=m)
            flagged = rows[(rows["status"] == FIT_FAILED) | (rows["converged"] == False)]  # noqa: E712
            if not flagged.empty:
                axes[0].scatter(flagged["origin_date"], np.full(len(flagged), 1.0), marker="x", s=25, color=styles[m][0])
        axes[0].set(ylabel="persistence (alpha + gamma/2 + beta; EGARCH beta)",
                    title="Parameter stability across scheduled refits (x = failed or non-converged fit) — " + subtitle)
        axes[1].set(ylabel="alpha[1]", xlabel="refit origin")
        if est.empty:
            axes[0].text(0.1, 0.5, "No estimated-parameter models in this experiment.", transform=axes[0].transAxes)
        _legend(axes[0], ncol=3, loc="lower left")
        _save(fig, directory, asset, "estimation_stability", output)

        # 8. rolling out-of-sample performance -----------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(12, 5))
        if benchmark in loss_wide.columns and len(loss_wide) > rolling_window:
            for m in models:
                if m == benchmark or m not in loss_wide.columns:
                    continue
                diff = (loss_wide[m] - loss_wide[benchmark]).rolling(rolling_window).mean()
                ax.plot(diff.index, diff, lw=1.0, color=styles[m][0], ls=styles[m][1], label=m)
            ax.axhline(0, color=GREY, lw=0.8)
        ax.set(title=f"Rolling {rolling_window}-session mean QLIKE difference vs {benchmark} — " + subtitle,
               ylabel="mean QLIKE difference (negative = better)", xlabel="target session (common dates)")
        _legend(ax, ncol=3, loc="upper left")
        _save(fig, directory, asset, "rolling_performance", output)
    return output
