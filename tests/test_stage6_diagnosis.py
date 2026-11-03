"""Stage 6 diagnosis: synthetic unit fixtures plus read-only checks on the saved Stage 5 run."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from volrisk.economics.accounting import Policy, run_close
from volrisk.economics import diagnosis as dg

ROOT = Path(__file__).resolve().parents[1]
HAS_STAGE5 = (ROOT/'reports/latest_stage5.json').exists()


def prices(n=90, seed=4, shock_at=None):
    rng = np.random.default_rng(seed); dates = pd.bdate_range('2024-01-01',periods=n)
    r = rng.normal(.0005,.01,n)
    if shock_at is not None: r[shock_at] = -.05; r[shock_at+1:shock_at+4] = .02
    return pd.DataFrame({'simple_return':r,'origin_timestamp':dates.tz_localize('Asia/Kolkata')+pd.Timedelta(hours=15,minutes=30)},index=dates)


def signals(p, vol):
    rows = []
    for i in range(1,len(p)-1):
        rows.append(dict(model='m',horizon=2,asset='NIFTY50_TRI',origin_date=p.index[i-1],execution_date=p.index[i],target_date=p.index[i+1],
            issued_at=p.origin_timestamp.iloc[i-1]+pd.Timedelta(microseconds=1),forecast_variance=vol[i]**2/252,
            target_quantity='daily_close_to_close_log_return_variance',failure_reason=''))
    return pd.DataFrame(rows)


def paths(seed=4, shock_at=40, cost=10.):
    p = prices(seed=seed,shock_at=shock_at)
    vol = np.full(len(p),.10); vol[shock_at+1:shock_at+30] = .30
    policy = Policy(cost_bps=cost)
    dyn = run_close(p,signals(p,vol),'m',policy,start=p.index[0],end=p.index[-1])
    bh = run_close(p,pd.DataFrame(),'static',policy,start=p.index[0],end=p.index[-1],constant=1.,buy_hold=True)
    return dyn, bh


@pytest.mark.parametrize('seed',[1,2,3])
@pytest.mark.parametrize('cost',[0.,10.,50.])
def test_decomposition_reconciles_terminal_wealth(seed,cost):
    dyn, bh = paths(seed,cost=cost)
    parts = dg.terminal_decomposition(dyn,bh,1e6)
    assert abs(parts['reconciliation_error']) < 1e-12
    assert parts['avoided_loss_total'] >= 0 and parts['missed_upside_total'] <= 0
    assert parts['transaction_cost'] <= 0 if cost else parts['transaction_cost'] == 0


def test_decomposition_rejects_misaligned_paths():
    dyn, bh = paths()
    with pytest.raises(ValueError,match='identical'):
        dg.terminal_decomposition(dyn.iloc[1:],bh,1e6)


def test_identical_paths_have_zero_decomposition():
    _, bh = paths()
    parts = dg.terminal_decomposition(bh,bh,1e6)
    assert all(abs(v) < 1e-15 for k,v in parts.items() if isinstance(v,float))


def test_recovery_window_excludes_shock_day_and_spans_ten_sessions():
    r = pd.Series([0.,-.03]+[.001]*12)
    w = dg.recovery_window(r)
    assert not w.iloc[1] and w.iloc[2:12].all() and not w.iloc[12]


def test_spell_lengths():
    assert dg.spell_lengths([1,1,0,1,0,0,1,1,1]) == [2,1,3]
    assert dg.spell_lengths([0,0]) == []


def test_event_study_respects_two_session_reaction_lag():
    dyn, _ = paths(shock_at=40)
    shock_date = prices(shock_at=40).index[40]
    events, path = dg.shock_event_study(dyn,1e6)
    row = events[events.shock_date.eq(shock_date.date())].iloc[0]
    j = dyn.index.get_loc(shock_date)
    # Forecast issued after the shock close executes at the next close and first governs the session after that.
    assert row.exposure_on_shock_day == pytest.approx(1.)
    assert dyn.exposure.iloc[j+1] == pytest.approx(1.)
    assert row.first_reactive_exposure == pytest.approx(dyn.exposure.iloc[j+2]) == pytest.approx(.4,rel=1e-3)
    assert row.consecutive_sessions_forecast_above_target == 29
    assert set(path.offset) <= set(range(-3,16))


def test_event_concentration_and_buckets_partition_allocation():
    dyn, bh = paths()
    c = dg.event_concentration(dyn,1e6)
    total = dg.terminal_decomposition(dyn,bh,1e6)['allocation_total']
    # Concentration and buckets measure against 100% equity; buy-and-hold differs only by its entry cost.
    assert c['full_year_allocation_effect'] == pytest.approx(total,abs=1e-4)
    b = dg.exposure_buckets(dyn,1e6)
    assert b.allocation_effect.sum() == pytest.approx(c['full_year_allocation_effect'],abs=1e-14) and b.sessions.sum() == len(dyn)


def test_cap_and_volatility_shares():
    dyn, _ = paths()
    c = dg.cap_and_volatility(dyn)
    assert 0 <= c['variance_share_from_capped_days'] <= 1 and 0 <= c['cap_binding_fraction'] <= 1


def test_cutoff_guard_blocks_post_2024_rows():
    frame = pd.DataFrame(index=pd.to_datetime(['2024-12-31','2025-01-02']))
    with pytest.raises(ValueError,match='after 2024-12-31'):
        dg.assert_within_cutoff(frame)
    assert dg.assert_within_cutoff(frame.iloc[:1])


def test_forecast_bias_uses_next_session_target():
    idx = pd.bdate_range('2024-01-01',periods=5)
    ledger = pd.DataFrame(dict(forecast_variance=[1e-4]*5),index=idx)
    lr = pd.Series([0.,.02,.02,.02,.02],index=idx)
    out = dg.forecast_bias(ledger,lr)
    assert out.loc['overall','sessions'] == 4
    assert out.loc['overall','calibration_ratio'] == pytest.approx(4.)


def test_constant_sharpe_is_scale_invariant_without_costs():
    p = prices()
    policy = Policy(cost_bps=0)
    a = run_close(p,pd.DataFrame(),'static',policy,start=p.index[0],end=p.index[-1],constant=.5)
    b = run_close(p,pd.DataFrame(),'static',policy,start=p.index[0],end=p.index[-1],constant=1.)
    assert dg.sharpe(a) == pytest.approx(dg.sharpe(b),rel=1e-2)


@pytest.mark.skipif(not HAS_STAGE5,reason='Stage 5 run not present')
def test_saved_stage5_run_reconciles_and_is_unchanged():
    data, tables = dg.run_diagnosis(ROOT)
    assert data['verified_files'] > 0
    d = tables['terminal_decomposition']
    assert d.matches_stage5.all() and d.reconciliation_error.abs().max() < 1e-12
    saved = pd.read_csv(data['run']/'allocation_attribution.csv')
    for m in dg.PRIMARY_MODELS:
        s = saved[(saved.model==m)&(saved.benchmark=='buy_hold')].set_index('category').allocation_effect
        row = d.set_index('model').loc[m]
        assert row.missed_rebound == pytest.approx(s['missed_recovery'],abs=1e-12)
        assert row.avoided_loss_before == pytest.approx(s['reduced_exposure_before_loss'],abs=1e-12)
        assert row.avoided_loss_after == pytest.approx(s['reduced_exposure_after_loss'],abs=1e-12)
    assert tables['forecast_bias'].sessions.gt(0).all()
    assert data['inputs'].index.max() <= dg.CUTOFF


@pytest.mark.skipif(not (ROOT/'reports/latest_stage6.json').exists(),reason='Stage 6 not run')
def test_published_stage6_outputs_match_manifest():
    from volrisk.data.storage import sha256
    pointer = json.loads((ROOT/'reports/latest_stage6.json').read_text())
    run = ROOT/pointer['run']
    assert sha256(run/'manifest.json') == pointer['manifest_sha256']
    m = json.loads((run/'manifest.json').read_text())
    assert not m['future_period_evaluated'] and m['new_policies_simulated'] == 0 and m['trades_executed'] == 0
    for rel,digest in m['output_hashes'].items():
        assert sha256(run/rel) == digest
