"""Per-asset static audit figures on each original observation calendar."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def make_plots(frame, detail, events, directory: Path, event_limit=8):
    directory.mkdir(parents=True, exist_ok=True)
    s = detail['summary']
    symbol = s['asset']
    subtitle = f"{symbol} | {s['currency']} | {s['source_timezone']} | native observed sessions"
    dates = frame['date']
    prices = frame['price'].where(np.isfinite(frame['price']) & frame['price'].gt(0))
    output = []

    def save(fig, name):
        fig.text(0.01, 0.01, 'Retrospective data audit only. Flags require review; no extreme values removed.', fontsize=8, color='#555555')
        fig.tight_layout(rect=(0, .035, 1, .96))
        path = directory / f'{symbol}_{name}.png'
        fig.savefig(path, dpi=150, metadata={'Software': 'NEXUS Sprint 1B'})
        plt.close(fig)
        output.append(path)

    with plt.rc_context({'axes.grid': True, 'grid.alpha': .2, 'font.size': 10}):
        fig, ax = plt.subplots(figsize=(12, 4.5))
        valid = prices.dropna()
        if len(valid):
            ax.plot(dates, prices / valid.iloc[0] * 100, color='#126782', lw=1.1)
        ax.set(title='Historical normalized price — ' + subtitle, ylabel='First valid observation = 100', xlabel='Session date')
        save(fig, 'normalized_price')

        fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
        for ax, col, color in zip(axes, ('simple_return', 'log_return'), ('#126782', '#7b2cbf')):
            ax.plot(dates, frame[col] * 100, lw=.55, color=color)
            ax.set_ylabel(col.replace('_', ' ') + ' (%)')
            ax.axhline(0, color='#555555', lw=.5)
        axes[0].set_title('Daily observed returns — ' + subtitle)
        axes[-1].set_xlabel('Session date; unverified historical gaps remain marked in data')
        save(fig, 'daily_returns')

        fig, ax = plt.subplots(figsize=(10, 4.5))
        values = frame.loc[frame['return_usable'], 'log_return'] * 100
        ax.hist(values, bins=min(100, max(5, int(np.sqrt(len(values))))), color='#126782', edgecolor='white', lw=.3)
        ax.set(title='Log-return distribution — ' + subtitle, xlabel='Daily log return (%)', ylabel='Observation count')
        save(fig, 'log_return_distribution')

        fig, ax = plt.subplots(figsize=(12, 4.8))
        cal = detail['calendar_audit']
        years = np.arange(pd.Timestamp(s['earliest']).year, pd.Timestamp(s['latest']).year + 1)
        for shift, key, label, color in [(-.25, 'unverified_absent_weekdays', 'Absent weekday: calendar unverified', '#adb5bd'),
                                        (0, 'missing_expected_sessions', 'Confirmed missing session', '#c1121f'),
                                        (.25, 'unexpected_sessions', 'Unexpected observed session', '#f4a261')]:
            counts = pd.Series(pd.to_datetime(cal[key]).year).value_counts()
            ax.bar(years + shift, [counts.get(y, 0) for y in years], width=.25, label=label, color=color)
        ax.set(title='Session / gap review — ' + subtitle, ylabel='Dates flagged', xlabel='Year (unverified absences include holidays)')
        ax.set_xticks(years)
        ax.tick_params(axis='x', labelrotation=45)
        ax.set_ylim(0, max(1, ax.get_ylim()[1]) * 1.25)
        ax.legend(fontsize=8, loc='upper left')
        save(fig, 'session_gaps')

        candidates = [e for e in events if e['Simple return'] is not None and any(
            reason in e['Reason flagged'] for reason in ('return', 'reversal', 'split', 'adjustment', 'dividend', 'outlier', 'MAD'))]
        chosen = sorted(candidates, key=lambda e: (-abs(e['Simple return']), e['Date']))[:event_limit]
        n = max(1, len(chosen))
        fig, axes = plt.subplots((n+1)//2, 2, figsize=(12, 2.6*((n+1)//2)), squeeze=False)
        for ax, event in zip(axes.flat, chosen):
            day = pd.Timestamp(event['Date'])
            matches = np.flatnonzero(dates.eq(day))
            if not len(matches):
                continue
            pos = int(matches[0])
            left, right = max(0, pos-5), min(len(frame), pos+6)
            ax.plot(dates.iloc[left:right], prices.iloc[left:right], '-o', color='#126782', lw=1, markersize=3)
            ax.axvline(day, color='#c1121f', ls='--', lw=.9)
            ax.set_title(f"{event['Date']} | simple return {event['Simple return']:.2%}", fontsize=10)
            ax.set_ylabel(f"Price ({s['currency']})" if symbol != 'NIFTY50_TRI' else 'TRI level (INR index)')
            ax.tick_params(axis='x', labelrotation=30, labelsize=7)
        for ax in list(axes.flat)[len(chosen):]:
            ax.set_axis_off()
        if not chosen:
            axes.flat[0].text(.1, .5, 'No suspicious return events detected.', transform=axes.flat[0].transAxes)
        fig.suptitle(f'Extreme-event inspection — {subtitle}\nTop {len(chosen)} of {len(candidates)} flagged return dates by absolute move; complete list in suspicious_dates.csv', fontsize=10)
        save(fig, 'extreme_events')
    return output
