"""Retrospective review flags only. No trimming, winsorization or forecast inputs."""
import numpy as np
import pandas as pd


def detect_outliers(frame, settings, validation, flag):
    s = pd.to_numeric(frame['simple_return'], errors='coerce').to_numpy(dtype=float)
    logs = pd.to_numeric(frame['log_return'], errors='coerce').to_numpy(dtype=float)
    p = pd.to_numeric(frame['price'], errors='coerce').to_numpy(dtype=float)
    finite = np.isfinite(logs)
    median = mad = None
    for i in np.flatnonzero(np.isfinite(s) & (np.abs(s) > validation.extreme_simple_return)):
        flag(i, 'absolute_return', 'WARNING', 'Compare with official closes and market news; a crisis move can be genuine.')
    if finite.sum() >= settings.mad_min_observations:
        median = float(np.median(logs[finite]))
        mad = float(np.median(np.abs(logs[finite] - median)))
        deviations = np.abs(logs - median)
        robust = deviations > settings.mad_z_threshold * mad / 0.6744897501960817 if mad > 0 else deviations > 0
        robust &= finite & (np.abs(s) >= settings.mad_min_abs_return)
        for i in np.flatnonzero(robust):
            flag(i, 'median_MAD_outlier' if mad > 0 else 'zero_MAD_deviation', 'WARNING',
                 'Review the source observation. Full-sample MAD is descriptive and must not be a forecast feature.')
    reversal_pairs = 0
    for i in range(2, len(s)):
        if (np.isfinite(logs[i-1:i+1]).all() and s[i-1]*s[i] < 0
                and min(abs(s[i-1]), abs(s[i])) >= settings.reversal_min_move
                and abs(logs[i-1]+logs[i]) <= settings.reversal_max_log_residual):
            reversal_pairs += 1
            for j in (i-1, i):
                flag(j, 'large_two_observation_reversal', 'WARNING',
                     'Check both dates for bad ticks, corporate actions or a genuine market reversal.')
    max_stale, stale_observations = 0, 0
    first = 0
    while first < len(p):
        stop = first + 1
        while stop < len(p) and np.isfinite(p[first]) and p[first] > 0 and p[stop] == p[first]:
            stop += 1
        length = stop - first
        if np.isfinite(p[first]) and p[first] > 0:
            max_stale = max(max_stale, length)
            if length >= validation.stale_observations:
                stale_observations += length
                for i in range(first, stop):
                    flag(i, 'stale_price_sequence', 'WARNING', 'Verify trading activity and whether the provider repeated an old close.')
        first = stop
    if frame['currency'].eq('USD').all():
        factors = np.array([2, 3, 4, 5, 10], dtype=float)
        for i in np.flatnonzero(finite & (np.abs(s) >= 0.30)):
            if np.min(np.abs(abs(logs[i]) - np.log(factors))) < settings.split_log_tolerance:
                flag(i, 'split_like_jump', 'WARNING', 'Compare the price adjustment factor and recorded stock-split ratio; no correction applied.')
        if 'stock_splits' in frame:
            for i, ratio in enumerate(frame['stock_splits']):
                if pd.notna(ratio) and ratio not in (0, 1) and ratio > 0 and np.isfinite(logs[i]):
                    if abs(abs(logs[i])-abs(np.log(ratio))) < settings.split_log_tolerance:
                        flag(i, 'possible_split_adjustment_error', 'WARNING', 'Check for omitted or double-applied split adjustment.')
    return {'log_return_median': median, 'log_return_MAD': mad,
            'MAD_computed': median is not None, 'max_unchanged_price_run': max_stale,
            'stale_price_observations': stale_observations, 'reversal_pairs': reversal_pairs}
