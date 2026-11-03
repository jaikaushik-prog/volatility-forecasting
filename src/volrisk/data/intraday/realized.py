"""Session-aligned bars and realized measures with explicit missingness.

Each segment's price path starts at its observed first OPEN, then uses nonoverlapping
bar CLOSE endpoints. Overnight and scheduled-break returns are separate. A shortened
last interval is retained and labelled (375 minutes is not divisible by 10).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from .calendar import TZ, local_time
from .normalize import PRICE_COLUMNS


def aggregate_session(observed, info, frequency):
    if frequency not in (1,5,10,15):
        raise ValueError('Supported bar intervals are 1, 5, 10 and 15 minutes')
    records = []
    indexed = observed.set_index('timestamp')
    for segment,(a,b) in enumerate(info['segments']):
        start, stop = local_time(info['session_date'],a), local_time(info['session_date'],b)
        index = pd.date_range(start,stop,freq='min',inclusive='left')
        grid = indexed.reindex(index)
        good = grid.valid_bar.eq(True).to_numpy(dtype=bool)
        values = grid[PRICE_COLUMNS].to_numpy(dtype=float)
        volume = grid.volume.to_numpy(dtype=float)
        previous_close = np.nan
        for left in range(0,len(index),frequency):
            right = min(len(index),left+frequency)
            complete = bool(good[left:right].all())
            opened,high,low,closed = np.nan,np.nan,np.nan,np.nan
            if complete:
                opened,closed = float(values[left,0]),float(values[right-1,3])
                high,low = float(values[left:right,1].max()),float(values[left:right,2].min())
            reference = opened if left == 0 else previous_close
            r = float(np.log(closed/reference)) if complete and np.isfinite(reference) and reference>0 else np.nan
            records.append({'session_date': info['session_date'], 'segment': segment,
                'timestamp': index[left], 'available_at': index[right-1]+pd.Timedelta(minutes=1),
                'frequency_minutes':frequency,'duration_minutes':right-left,'short_interval':right-left<frequency,
                'expected_minutes':right-left,'observed_valid_minutes':int(good[left:right].sum()),
                'complete':complete,'open':opened,'high':high,'low':low,'close':closed,
                'volume':float(volume[left:right].sum()) if complete and np.isfinite(volume[left:right]).all() else np.nan,
                'intraday_log_return':r})
            previous_close = closed
    return pd.DataFrame(records)


def daily_measures(normalized, calendar, *, frequencies=(1,5,10,15), annualization=252, jump_min_intervals=20):
    groups = {date:g for date,g in normalized.groupby('session_date',sort=True)}
    schedule = calendar.grid(normalized.session_date.min(), normalized.session_date.max(), groups)
    days, bars = [], {f:[] for f in frequencies}
    empty = normalized.iloc[:0]
    for info in schedule.to_dict('records'):
        date = info['session_date']
        observed = groups.get(date,empty)
        expected = calendar.minutes(date)
        indexed = observed.set_index('timestamp')
        minute_grid = indexed.reindex(pd.DatetimeIndex(expected.timestamp))
        valid = minute_grid.valid_bar.eq(True)
        missing_times = expected.loc[~valid.to_numpy(), 'timestamp']
        n_expected = len(expected)
        complete = bool(n_expected and valid.all())
        open_valid = bool(n_expected and valid.iloc[0])
        close_valid = bool(n_expected and valid.iloc[-1])
        provenance = bool(len(observed) and observed.provenance_verified.all())
        row = {k:v for k,v in info.items() if k != 'segments'}
        row.update({'asset': normalized.asset.iloc[0], 'exchange':calendar.exchange,
            'currency':normalized.currency.iloc[0], 'source_rows':len(observed),
            'observed_valid_minutes':int(valid.sum()), 'missing_or_invalid_minutes':int(n_expected-valid.sum()),
            'missing_minutes':int((~pd.DatetimeIndex(expected.timestamp).isin(observed.timestamp)).sum()),
            'missing_minute_times':';'.join(missing_times.dt.strftime('%H:%M')),
            'session_complete':complete, 'completeness':float(valid.mean()) if n_expected else np.nan,
            'endpoint_open_valid':open_valid, 'endpoint_close_valid':close_valid,
            'open':float(minute_grid.open.iloc[0]) if open_valid else np.nan,
            'close':float(minute_grid.close.iloc[-1]) if close_valid else np.nan,
            'extreme_return_flags':int(observed.extreme_return.sum()),
            'stale_observations':int(observed.stale_sequence.sum()),
            'outside_session_rows':int(observed.outside_session.sum()),
            'max_unchanged_run_minutes':int(observed.unchanged_run_minutes.max()) if len(observed) else 0,
            'provenance_verified':provenance,
            'rv_eligible':bool(complete and info['schedule_verified']),
            'research_ready':bool(complete and info['schedule_verified'] and provenance)})
        segment_endpoints = []
        for segment in range(len(info['segments'])):
            part = minute_grid.iloc[np.flatnonzero(expected.segment.eq(segment))]
            segment_endpoints.append((part.open.iloc[0],part.close.iloc[-1],bool(part.valid_bar.iloc[0]) if pd.notna(part.valid_bar.iloc[0]) else False,
                                      bool(part.valid_bar.iloc[-1]) if pd.notna(part.valid_bar.iloc[-1]) else False))
        break_returns = []
        breaks_valid = True
        for prior,current in zip(segment_endpoints,segment_endpoints[1:]):
            if prior[3] and current[2]: break_returns.append(float(np.log(current[0]/prior[1])))
            else: breaks_valid=False
        row['reopening_log_return'] = sum(break_returns) if breaks_valid and n_expected else np.nan
        row['reopening_squared_return'] = sum(r*r for r in break_returns) if breaks_valid and n_expected else np.nan
        row['intraday_open_to_close_log_return'] = float(np.log(row['close']/row['open'])) if open_valid and close_valid else np.nan
        for freq in frequencies:
            aggregated = aggregate_session(observed,info,freq)
            if len(aggregated):
                aggregated['asset'] = row['asset']
                aggregated['schedule_verified'] = info['schedule_verified']
                aggregated['provenance_verified'] = provenance
                bars[freq].append(aggregated)
            r = aggregated.intraday_log_return.to_numpy() if len(aggregated) else np.array([])
            usable = row['rv_eligible'] and len(r)>0 and np.isfinite(r).all()
            rv = float(np.dot(r,r)) if usable else np.nan
            row[f'rv_{freq}min'] = rv
            row[f'realized_vol_{freq}min'] = np.sqrt(rv)
            row[f'annualized_realized_vol_{freq}min'] = np.sqrt(rv*annualization)
            row[f'positive_semivariance_{freq}min'] = float(np.square(r[r>0]).sum()) if usable else np.nan
            row[f'negative_semivariance_{freq}min'] = float(np.square(r[r<0]).sum()) if usable else np.nan
            row[f'return_intervals_{freq}min'] = len(r) if usable else 0
            if freq == 5:
                bpv = 0.
                enough = usable and len(r)>=jump_min_intervals
                if enough:
                    for _,g in aggregated.groupby('segment'):
                        q = g.intraday_log_return.to_numpy()
                        if len(q)<2 or g.duration_minutes.nunique()!=1:
                            enough=False
                            break
                        bpv += np.pi/2*len(q)/(len(q)-1)*float(np.sum(np.abs(q[1:])*np.abs(q[:-1])))
                row['bipower_variation_5min'] = bpv if enough else np.nan
                row['jump_variance_proxy_5min'] = max(rv-bpv,0.) if enough else np.nan
        row['quality_status'] = 'WARNING' if row['rv_eligible'] else 'FAIL'
        row['quality_reason'] = ('provisional_source_identity_timezone_bar_label' if row['rv_eligible'] and not provenance
            else 'valid' if row['research_ready'] else 'missing_or_invalid_minutes' if info['schedule_verified']
            else 'calendar_or_session_times_unverified')
        if row['research_ready']: row['quality_status']='PASS'
        days.append(row)
    daily = pd.DataFrame(days).sort_values('session_date').reset_index(drop=True)
    # Every expected/uncertain candidate session remains in the grid. Do not skip missing days.
    prior_calendar = daily.schedule_verified.shift(fill_value=False)
    adjacent_known = daily.schedule_verified & prior_calendar & daily.expected_session & daily.expected_session.shift(fill_value=False)
    overnight_ok = adjacent_known & daily.endpoint_open_valid & daily.endpoint_close_valid.shift(fill_value=False)
    c2c_ok = adjacent_known & daily.endpoint_close_valid & daily.endpoint_close_valid.shift(fill_value=False)
    daily['overnight_log_return'] = np.log(daily.open/daily.close.shift()).where(overnight_ok)
    daily['overnight_squared_return'] = daily.overnight_log_return**2
    daily['close_to_close_log_return'] = np.log(daily.close/daily.close.shift()).where(c2c_ok)
    daily['overnight_endpoints_valid'] = overnight_ok
    for freq in frequencies:
        daily[f'full_session_rv_{freq}min'] = daily[f'rv_{freq}min']+daily.reopening_squared_return
        daily[f'full_rv_proxy_{freq}min'] = daily[f'full_session_rv_{freq}min']+daily.overnight_squared_return
        daily[f'annualized_full_proxy_vol_{freq}min'] = np.sqrt(annualization*daily[f'full_rv_proxy_{freq}min'])
    return daily,{f:pd.concat(parts,ignore_index=True) if parts else pd.DataFrame() for f,parts in bars.items()}
