"""Synthetic fixtures only: no downloaded market history is used in these tests."""
from dataclasses import replace
from datetime import date
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volrisk.config import AuditSettings, ValidationSettings
from volrisk.data.audit import inspect_asset, run_audit
from volrisk.data.calendar_audit import audit_calendar, verify_calendar_evidence
from volrisk.data.models import ASSETS, DataError
from volrisk.data.normalization import normalize_yfinance
from volrisk.data.outliers import detect_outliers
from volrisk.data.pipeline import run_pipeline
from volrisk.data.return_audit import audit_returns
from volrisk.data.source_audit import _audit_adjustments, audit_source
from volrisk.data.storage import sha256


def fixture_frame(prices, dates=None):
    dates = pd.DatetimeIndex(dates) if dates is not None else pd.bdate_range('2024-01-02', periods=len(prices))
    raw = pd.DataFrame({'Close': prices, 'Dividends': 0., 'Stock Splits': 0.}, index=dates)
    return normalize_yfinance(raw, ASSETS[0], dates.min().date(), dates.max().date()).frame


def known_calendar(start='2024-01-02', end='2024-01-04', holidays=(), special=()):
    return {'markets': {'NYSE': {'timezone': 'America/New_York', 'verified_start': start,
        'verified_end': end, 'holidays': list(holidays), 'special_sessions': list(special),
        'sources': ['synthetic://unit-test-calendar']}}}


def mock_source(monkeypatch):
    monkeypatch.setattr('volrisk.data.audit.audit_source', lambda *args: {
        'total_return_compatible': True, 'cleaning_actions': [], 'limitations': []})


def test_arithmetic_log_and_cumulative_identities():
    f = fixture_frame([100., 110., 88., 99.])
    np.testing.assert_allclose(f.simple_return.iloc[1:], [.1, -.2, .125])
    np.testing.assert_allclose(f.log_return.iloc[1:], np.log([1.1, .8, 1.125]))
    np.testing.assert_allclose(f.log_return.iloc[1:], np.log1p(f.simple_return.iloc[1:]))
    result = audit_returns(f, AuditSettings())
    assert result['status'] == 'PASS'
    assert result['first_return_null']
    assert result['compounded_simple_reconciles'] and result['summed_log_reconciles']
    assert result['usable_return_observations'] == 3


@pytest.mark.parametrize('column', ['simple_return', 'log_return', 'daily_return'])
@pytest.mark.parametrize('value', [0., np.inf, -.5])
def test_bad_first_return_fails_without_repair(column, value):
    f = fixture_frame([100., 110., 88.])
    f.loc[0, column] = value
    original = f.copy(deep=True)
    assert audit_returns(f, AuditSettings())['status'] == 'FAIL'
    pd.testing.assert_frame_equal(f, original)


@pytest.mark.parametrize('value', [np.nan, np.inf, 0., -1.])
def test_invalid_price_breaks_both_adjacent_returns(value):
    f = fixture_frame([100., value, 110., 111.])
    assert f.simple_return.iloc[:3].isna().all()
    assert f.log_return.iloc[:3].isna().all()
    result = audit_returns(f, AuditSettings())
    assert result['status'] == 'PASS'
    assert result['usable_return_observations'] == 1


@pytest.mark.parametrize('column', ['simple_return', 'log_return'])
def test_nan_beyond_first_is_not_accepted_without_gap(column):
    f = fixture_frame([100., 101., 102.])
    f.loc[1, column] = np.nan
    result = audit_returns(f, AuditSettings())
    assert result['status'] == 'FAIL'
    assert result['unexpected_nonfinite_returns'] == 1


def test_log1p_can_pass_while_price_reconciliation_fails():
    f = fixture_frame([100., 110., 121.])
    f.loc[1, ['simple_return', 'daily_return']] = .2
    f.loc[1, 'log_return'] = np.log1p(.2)
    result = audit_returns(f, AuditSettings())
    assert result['log1p_identity_valid']
    assert not result['arithmetic_formula_valid']
    assert not result['compounded_simple_reconciles']
    assert not result['summed_log_reconciles']


def test_overflow_is_failure_even_when_formula_itself_overflows():
    f = fixture_frame([1e-300, 1e300])
    result = audit_returns(f, AuditSettings())
    assert result['status'] == 'FAIL'
    assert result['unexpected_nonfinite_returns'] == 1


def test_missing_session_excludes_only_affected_return(monkeypatch, settings):
    mock_source(monkeypatch)
    f = fixture_frame([100., 110.], ['2024-01-02', '2024-01-04'])
    canonical, detail, rows = inspect_asset(f, {}, ASSETS[0], settings, known_calendar())
    assert detail['summary']['validation_status'] == 'FAIL'
    assert detail['summary']['missing_expected_sessions'] == 1
    assert detail['canonical_return_audit']['status'] == 'PASS'
    assert canonical.simple_return.isna().all()
    assert canonical.observed_simple_return.iloc[1] == pytest.approx(.1)
    assert canonical.price.tolist() == [100., 110.]
    assert len(canonical) == 2  # The absent session is not inserted or filled.
    assert any(r['Date'] == '2024-01-03' and r['Price'] is None for r in rows)


def test_documented_holiday_does_not_exclude_return(monkeypatch, settings):
    mock_source(monkeypatch)
    f = fixture_frame([100., 101.], ['2024-01-02', '2024-01-04'])
    canonical, detail, _ = inspect_asset(f, {}, ASSETS[0], settings, known_calendar(holidays=['2024-01-03']))
    assert detail['summary']['validation_status'] == 'PASS'
    assert canonical.simple_return.iloc[1] == pytest.approx(.01)
    assert canonical.calendar_interval_verified.iloc[1]


def test_unverified_calendar_is_warning_not_missing_session(monkeypatch, settings):
    mock_source(monkeypatch)
    f = fixture_frame([100., 101.], ['2024-01-02', '2024-01-04'])
    canonical, detail, _ = inspect_asset(f, {}, ASSETS[0], settings, {})
    assert detail['summary']['validation_status'] == 'WARNING'
    assert detail['summary']['missing_expected_sessions'] == 0
    assert detail['summary']['unverified_absent_weekdays'] == 1
    assert canonical.simple_return.iloc[1] == pytest.approx(.01)
    assert not canonical.calendar_interval_verified.any()


def test_official_long_holiday_closure_is_not_unexplained(monkeypatch, settings):
    mock_source(monkeypatch)
    settings = replace(settings, end=date(2024, 1, 12))
    f = fixture_frame([100., 101.], ['2024-01-02', '2024-01-12'])
    holidays = pd.bdate_range('2024-01-03', '2024-01-11').strftime('%Y-%m-%d').tolist()
    _, detail, rows = inspect_asset(f, {}, ASSETS[0], settings,
        known_calendar(end='2024-01-12', holidays=holidays))
    assert detail['summary']['long_gap_count'] == 1
    assert detail['summary']['unexplained_long_gap_count'] == 0
    assert detail['summary']['validation_status'] == 'PASS'
    assert not rows


def test_separate_market_holidays_and_special_sunday():
    doc = known_calendar('2024-01-01', '2024-01-07', holidays=['2024-01-01'])
    doc['markets']['NSE'] = {'timezone': 'Asia/Kolkata', 'verified_start': '2024-01-01',
        'verified_end': '2024-01-07', 'holidays': ['2024-01-02'], 'special_sessions': ['2024-01-07'],
        'sources': ['synthetic://india-calendar']}
    days = pd.Series(pd.to_datetime(['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05']))
    us = audit_calendar(days, ASSETS[0], date(2024, 1, 1), date(2024, 1, 7), doc)
    india = audit_calendar(days, ASSETS[2], date(2024, 1, 1), date(2024, 1, 7), doc)
    assert us['missing_expected_sessions'] == []
    assert india['missing_expected_sessions'] == ['2024-01-01', '2024-01-07']
    assert india['unexpected_sessions'] == ['2024-01-02']


def test_unverified_hole_does_not_invent_missing_session_or_exclude_return(monkeypatch, settings):
    mock_source(monkeypatch)
    doc = known_calendar()
    doc['markets']['NYSE']['unverified_dates'] = ['2024-01-03']
    f = fixture_frame([100., 101.], ['2024-01-02', '2024-01-04'])
    canonical, detail, _ = inspect_asset(f, {}, ASSETS[0], settings, doc)
    cal = detail['calendar_audit']
    assert detail['summary']['validation_status'] == 'WARNING'
    assert cal['missing_expected_sessions'] == []
    assert cal['unverified_absent_weekdays'] == ['2024-01-03']
    assert not cal['full_window_verified']
    assert cal['expected_sessions_full_window'] is None
    assert cal['expected_sessions_verified_period'] == 2
    assert not canonical.calendar_interval_verified.any()
    assert canonical.simple_return.iloc[1] == pytest.approx(.01)
    assert canonical.price.tolist() == [100., 101.]


def test_observed_unverified_day_and_both_adjacent_intervals_remain_uncertain():
    doc = known_calendar()
    doc['markets']['NYSE']['unverified_dates'] = ['2024-01-03']
    f = fixture_frame([100., 101., 102.])
    cal = audit_calendar(f.date, ASSETS[0], '2024-01-02', '2024-01-04', doc)
    assert cal['unexpected_sessions'] == []
    assert cal['unverified_absent_weekdays'] == []
    assert not cal['full_window_verified'] and not cal['verified_interval'].any()


def test_uncertainty_is_date_specific_and_does_not_hide_other_missing_sessions():
    doc = known_calendar(end='2024-01-05')
    doc['markets']['NYSE']['unverified_dates'] = ['2024-01-03']
    f = fixture_frame([100., 101.], ['2024-01-02', '2024-01-05'])
    cal = audit_calendar(f.date, ASSETS[0], '2024-01-02', '2024-01-05', doc)
    assert cal['missing_expected_sessions'] == ['2024-01-04']
    assert cal['gap_mask'].tolist() == [False, True]


def test_uncertainty_outside_requested_window_does_not_taint_verified_period():
    doc = known_calendar(end='2024-01-05')
    doc['markets']['NYSE']['unverified_dates'] = ['2024-01-03']
    f = fixture_frame([100., 101.], ['2024-01-04', '2024-01-05'])
    cal = audit_calendar(f.date, ASSETS[0], '2024-01-04', '2024-01-05', doc)
    assert cal['full_window_verified']
    assert cal['verified_interval'].tolist() == [False, True]


@pytest.mark.parametrize('field', ['holidays', 'special_sessions'])
def test_contradictory_calendar_authority_rejected(field):
    doc = known_calendar()
    doc['markets']['NYSE']['unverified_dates'] = ['2024-01-03']
    doc['markets']['NYSE'][field] = ['2024-01-03']
    with pytest.raises(DataError, match='both verified and unverified'):
        audit_calendar(fixture_frame([100., 101.]).date, ASSETS[0], '2024-01-02', '2024-01-04', doc)


def test_calendar_evidence_resolves_relative_paths_and_rejects_tampering(tmp_path):
    source = tmp_path / 'notice.txt'
    source.write_text('Synthetic exchange notice')
    config = tmp_path / 'config' / 'calendar.json'
    doc = {'evidence_files': [{'path': '../notice.txt', 'sha256': sha256(source)}]}
    assert verify_calendar_evidence(doc, config) == {source.resolve()}
    source.write_text('changed notice')
    with pytest.raises(DataError, match='Calendar evidence missing or changed'):
        verify_calendar_evidence(doc, config)
    source.unlink()
    with pytest.raises(DataError, match='Calendar evidence missing or changed'):
        verify_calendar_evidence(doc, config)


def test_calendar_evidence_in_audit_identity_and_checked_before_cache(settings, raw_frame, tmp_path):
    add_tri(settings)
    run_pipeline(settings, downloader=lambda **kw: raw_frame)
    evidence = tmp_path / 'synthetic_notice.txt'
    evidence.write_text('Synthetic calendar evidence')
    doc = known_calendar()
    doc['evidence_files'] = [{'path': evidence.name, 'sha256': sha256(evidence)}]
    calendar = tmp_path / 'calendar.json'
    calendar.write_text(json.dumps(doc))
    settings = replace(settings, audit=replace(settings.audit, calendar_file=calendar))
    result = run_audit(settings, plots=False)
    assert result['inputs_sha256'][str(evidence.resolve())] == sha256(evidence)
    assert run_audit(settings, plots=False)['cache_reused']
    evidence.write_text('altered after audit')
    with pytest.raises(DataError, match='Calendar evidence missing or changed'):
        run_audit(settings, plots=False)


@pytest.mark.parametrize('mutation,expected', [
    ('duplicate', 'duplicate_asset_date_excess'), ('negative', 'invalid_price_count'),
    ('infinite', 'invalid_price_count'), ('nan', 'invalid_price_count')])
def test_structural_failure(monkeypatch, settings, mutation, expected):
    mock_source(monkeypatch)
    f = fixture_frame([100., 101., 102.])
    if mutation == 'duplicate':
        f = pd.concat([f, f.iloc[[1]]], ignore_index=True)
    else:
        f.loc[1, 'price'] = {'negative': -1., 'infinite': np.inf, 'nan': np.nan}[mutation]
    _, detail, _ = inspect_asset(f, {}, ASSETS[0], settings, known_calendar())
    assert detail['summary']['validation_status'] == 'FAIL'
    assert detail['summary'][expected] >= 1


@pytest.mark.parametrize('column,value', [('currency', 'INR'), ('asset', 'VT'),
                                         ('price_convention', 'raw_close'), ('source', 'unknown')])
def test_metadata_convention_failure(monkeypatch, settings, column, value):
    mock_source(monkeypatch)
    f = fixture_frame([100., 101., 102.])
    f.loc[1, column] = value
    _, detail, _ = inspect_asset(f, {}, ASSETS[0], settings, known_calendar())
    assert detail['summary']['validation_status'] == 'FAIL'


def test_nonmonotonic_input_fails_without_sorting_away_evidence(monkeypatch, settings):
    mock_source(monkeypatch)
    f = fixture_frame([100., 101., 102.]).iloc[::-1].reset_index(drop=True)
    c, detail, _ = inspect_asset(f, {}, ASSETS[0], settings, known_calendar())
    assert detail['summary']['validation_status'] == 'FAIL'
    assert not detail['summary']['dates_monotonic']
    assert c.date.tolist() == f.date.tolist()


def collect_flags(frame, audit=None):
    flags = []
    metrics = detect_outliers(frame, audit or AuditSettings(), ValidationSettings(), lambda *args: flags.append(args))
    return flags, metrics


def test_crisis_return_flagged_never_deleted_or_winsorized():
    f = fixture_frame([100., 101., 80., 81.])
    original = f.copy(deep=True)
    flags, _ = collect_flags(f)
    assert any(reason == 'absolute_return' for _, reason, _, _ in flags)
    pd.testing.assert_frame_equal(f, original)


def test_zero_mad_reversal_stale_and_split_patterns():
    f = fixture_frame([100.] * 35 + [50., 100., 100.])
    f.loc[35, 'stock_splits'] = 2.
    flags, metrics = collect_flags(f)
    reasons = {row[1] for row in flags}
    assert {'zero_MAD_deviation', 'stale_price_sequence', 'split_like_jump',
            'large_two_observation_reversal', 'possible_split_adjustment_error'} <= reasons
    assert metrics['max_unchanged_price_run'] == 35


def test_nonzero_mad_threshold_is_configurable():
    changes = np.tile([.002, -.002, .004, -.004], 20).tolist() + [.08]
    f = fixture_frame(np.r_[100., 100 * np.cumprod(1 + np.array(changes))])
    flags, metrics = collect_flags(f)
    assert metrics['log_return_MAD'] > 0
    assert any(r[1] == 'median_MAD_outlier' for r in flags)
    flags, _ = collect_flags(f, replace(AuditSettings(), mad_z_threshold=100.))
    assert not any(r[1] == 'median_MAD_outlier' for r in flags)


def test_exchange_timezone_conversion(settings):
    raw = pd.DataFrame({'Close': [100., 101.]}, index=pd.to_datetime(['2024-01-02 05:00Z', '2024-01-03 05:00Z']))
    normalized = normalize_yfinance(raw, ASSETS[0], settings.start, settings.end)
    assert normalized.frame.date.tolist() == list(pd.to_datetime(['2024-01-02', '2024-01-03']))
    assert normalized.details['original_index_timezone'] == 'UTC'
    assert normalized.details['source_timezone'] == 'America/New_York'


def test_invalid_source_request_fails(raw_frame, settings, tmp_path):
    path = tmp_path / 'raw.parquet'
    raw_frame.to_parquet(path)
    entry = {'raw': [{'path': str(path), 'sha256': sha256(path)}],
             'acquisition': {'request': {'tickers': 'SPY', 'auto_adjust': False, 'actions': True}}}
    with pytest.raises(DataError, match='convention'):
        audit_source(fixture_frame([100., 101., 99.]), entry, ASSETS[0], settings, lambda *args: None)


def test_distribution_factor_and_missing_adjustment_flags(settings, tmp_path):
    # A synthetic $1 distribution with no economic return: raw Close drops 100 -> 99,
    # while Adj Close remains 99 -> 99. Historical adjustment factor is .99 -> 1.
    ref = pd.DataFrame({'Close': [100., 99., 99.], 'Adj Close': [99., 99., 99.],
                        'Dividends': [0., 1., 0.], 'Stock Splits': [0., 0., 0.]},
                       index=pd.date_range('2024-01-02', periods=3))
    path = tmp_path / 'SPY_reference.parquet'
    ref.to_parquet(path)
    metadata = {'symbol': 'SPY', 'currency': 'USD', 'file': path.name, 'sha256': sha256(path),
                'request': {'tickers': 'SPY', 'auto_adjust': False, 'actions': True}}
    (tmp_path / 'SPY_adjustment_reference.json').write_text(json.dumps(metadata))
    settings = replace(settings, audit=replace(settings.audit, evidence_dir=tmp_path))
    flags = []
    result = _audit_adjustments(fixture_frame([99., 99., 99.]), ASSETS[0], settings, lambda *args: flags.append(args))
    assert result['total_return_compatible'] is True
    assert result['dividend_events_checked'] == 1 and not flags
    bad = _audit_adjustments(fixture_frame([100., 99., 99.]), ASSETS[0], settings, lambda *args: flags.append(args))
    assert bad['total_return_compatible'] is False
    assert any(r[1] == 'possible_missing_dividend_adjustment' for r in flags)
    flags.clear()
    _audit_adjustments(fixture_frame([99., 99.99, 99.99]), ASSETS[0], settings, lambda *args: flags.append(args))
    assert any(r[1] == 'possible_double_dividend_adjustment' for r in flags)


def add_tri(settings):
    settings.nifty_csv_dir.mkdir(parents=True, exist_ok=True)
    (settings.nifty_csv_dir / 'synthetic.csv').write_text(
        'Index Name,Date,Total Returns Index\nNIFTY 50,2024-01-02,1000\nNIFTY 50,2024-01-03,1010\nNIFTY 50,2024-01-04,990\n')


def test_audit_pipeline_reproducible_preserves_raw_and_never_substitutes(settings, raw_frame):
    add_tri(settings)
    original = run_pipeline(settings, downloader=lambda **kw: raw_frame)
    manifest = json.loads(Path(original['manifest']).read_text())
    raw_hashes = {r['path']: sha256(Path(r['path'])) for e in manifest['assets'] for r in e['raw']}
    first = run_audit(settings, plots=False)
    second = run_audit(settings, plots=False)
    assert first['complete'] and second['complete']
    assert first['audit_id'] == second['audit_id'] and second['cache_reused']
    assert first['output_sha256'] == second['output_sha256']
    assert first['audited_at_utc'] == second['audited_at_utc']
    assert all(sha256(Path(p)) == h for p, h in raw_hashes.items())
    for symbol, path in first['canonical'].items():
        canonical = pd.read_parquet(path)
        observed = pd.read_parquet(original['processed'][symbol])
        pd.testing.assert_frame_equal(canonical[observed.columns], observed)
    # Missing original evidence must not reuse the previous successful cache.
    Path(next(iter(raw_hashes))).unlink()
    failed = run_audit(settings, plots=False)
    assert failed['audit_id'] != first['audit_id']
    assert failed['assets'][0]['summary']['validation_status'] == 'FAIL'
    assert 'SPY' not in failed['canonical']


def test_audit_missing_dataset_explicit_failure(settings, raw_frame):
    run_pipeline(settings, downloader=lambda **kw: raw_frame)
    result = run_audit(settings, plots=False)
    nifty = result['assets'][2]['summary']
    assert nifty['validation_status'] == 'FAIL'
    assert 'No processed dataset' in nifty['failure']
    assert 'NIFTY50_TRI' not in result['canonical']


def test_output_tampering_not_silently_reused(settings, raw_frame):
    add_tri(settings)
    run_pipeline(settings, downloader=lambda **kw: raw_frame)
    result = run_audit(settings, plots=False)
    path = Path(result['report_dir']) / 'suspicious_dates.csv'
    path.write_text('tampered')
    with pytest.raises(DataError, match='Cached audit artifact'):
        run_audit(settings, plots=False)


def test_all_five_visual_artifacts(tmp_path):
    from volrisk.data.audit_plots import make_plots
    f = fixture_frame([100., 101., 80.])
    f['return_usable'] = f.simple_return.notna()
    detail = {'summary': {'asset': 'SPY', 'currency': 'USD', 'source_timezone': 'America/New_York',
                         'earliest': '2024-01-02', 'latest': '2024-01-04'},
              'calendar_audit': {'missing_expected_sessions': [], 'unverified_absent_weekdays': [], 'unexpected_sessions': []}}
    paths = make_plots(f, detail, [], tmp_path)
    assert len(paths) == 5 and all(p.stat().st_size > 1000 for p in paths)


@pytest.mark.parametrize('name,value', [('mad_z_threshold', 0), ('return_rtol', np.inf),
                                      ('annualization_sessions', 2.5), ('mad_min_observations', 2)])
def test_invalid_audit_configuration(name, value):
    with pytest.raises(ValueError):
        AuditSettings(**{name: value})
