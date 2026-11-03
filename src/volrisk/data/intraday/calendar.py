"""Bounded exchange schedules: unknown dates/times never become verified by observation."""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd

TZ = 'Asia/Kolkata'


def local_time(date, clock):
    return pd.Timestamp(f'{pd.Timestamp(date).date()} {clock}', tz=TZ)


class SessionCalendar:
    def __init__(self, exchange, daily, intraday):
        self.exchange = exchange
        self.spec = intraday['markets'][exchange]
        if self.spec.get('daily_calendar_market'):
            self.daily = daily['markets'][self.spec['daily_calendar_market']]
        else:
            self.daily = self.spec
        self.holidays = set(self.daily.get('holidays', []))
        self.special = set(self.daily.get('special_sessions', []))
        self.unknown = set(self.daily.get('unverified_dates', []))
        self.overrides = self.spec.get('session_overrides', {})

    def describe(self, date):
        d = pd.Timestamp(date).normalize().tz_localize(None)
        key = d.strftime('%Y-%m-%d')
        covered = pd.Timestamp(self.daily['verified_start']) <= d <= pd.Timestamp(self.daily['verified_end'])
        covered = covered and d.year not in self.daily.get('unverified_years', []) and key not in self.unknown
        special = key in self.special or key in self.overrides
        expected = (d.dayofweek < 5 and key not in self.holidays) or special
        override = self.overrides.get(key)
        if override is not None:
            segments = override['segments']
            timing_verified = bool(override.get('verified', False))
            kind = override.get('kind', 'special')
        elif special:
            segments, timing_verified, kind = [], False, 'special_times_unverified'
        elif expected:
            segments, timing_verified, kind = self.spec['regular_segments'], True, 'regular'
        else:
            segments, timing_verified, kind = [], True, 'closed'
        # An unavailable annual calendar cannot validate a normal-looking weekday.
        verified = bool(covered and expected and timing_verified)
        return {'session_date': d, 'expected_session': bool(expected), 'calendar_verified': bool(covered),
                'schedule_verified': verified, 'session_kind': kind, 'segments': segments,
                'session_open': local_time(d, segments[0][0]) if segments else pd.NaT,
                'session_close': local_time(d, segments[-1][1]) if segments else pd.NaT,
                'expected_minutes': sum(int((local_time(d,b)-local_time(d,a)).total_seconds()/60) for a,b in segments)}

    def grid(self, start, end, observed=()):
        # Include absent candidate sessions so rolling features cannot skip holes.
        days = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize(), freq='D')
        observed = {pd.Timestamp(d).strftime('%Y-%m-%d') for d in observed}
        rows = [self.describe(d) for d in days]
        rows = [r for r in rows if r['expected_session'] or r['session_date'].strftime('%Y-%m-%d') in observed]
        return pd.DataFrame(rows)

    def minutes(self, date):
        info = self.describe(date)
        pieces = [pd.DataFrame({'timestamp': pd.date_range(local_time(date,a), local_time(date,b),
                    freq='min', inclusive='left'), 'segment': i}) for i,(a,b) in enumerate(info['segments'])]
        return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame({'timestamp': pd.DatetimeIndex([],tz=TZ),
                                                                               'segment': pd.Series(dtype=int)})
