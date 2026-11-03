"""Load and validate the H4 monitoring configuration; block prospective use until it is frozen."""
from __future__ import annotations
from pathlib import Path
import tomllib
from volrisk.data.storage import sha256

FROZEN = 'FROZEN'
DRAFT = 'DRAFT_NOT_FROZEN'
FORBIDDEN_TRUE = ('automatic_trading','automatic_position_reduction','automatic_reallocation',
                  'success_measured_by_pnl','directional_signal')
REQUIRED_LIMITATIONS = (
    "This is an estimate of market-index risk, not the risk of WSC's combined stock portfolio.",
    'High forecast volatility is not a bearish signal and does not predict a crash or a negative return.',
    'Provisional models use unverified intraday or VIX inputs and do not affect the alert level.',
)
COMMON_TARGET = 'next_session_squared_close_to_close_log_return'


class ProtocolNotFrozen(RuntimeError):
    """Raised whenever prospective collection or evaluation is attempted on an unfrozen protocol."""


def load(path):
    with Path(path).open('rb') as handle:
        config = tomllib.load(handle)
    validate(config)
    return config


def provisional_names(config):
    p = config['models']['provisional']
    return p['existing_close_to_close']+p['requires_respecification']+p['archived_comparators']


def validate(config):
    p = config['protocol']
    if p['status'] not in (DRAFT, FROZEN):
        raise ValueError(f"Unknown protocol status {p['status']!r}")
    if not p.get('advisory_only'):
        raise ValueError('H4 must be advisory only')
    for key in FORBIDDEN_TRUE:
        if p.get(key, True):
            raise ValueError(f'{key} must be false in H4')
    r = config['risk']
    if r['common_target'] != COMMON_TARGET:
        raise ValueError('All models must share the close-to-close target')
    if r['scope'] != 'market_index_risk':
        raise ValueError('H4 measures market-index risk, not portfolio risk')
    if not r.get('reliability_reported_separately'):
        raise ValueError('Model reliability must be reported separately from the risk level')
    if r['primary_probability_method'] not in r['probability_methods']:
        raise ValueError('Primary probability method is not among the registered methods')
    m = config['models']; prod = m['production']; prov = m['provisional']
    overlap = set(prod['names']) & set(provisional_names(config))
    if overlap:
        raise ValueError(f'Models listed as both production and provisional: {sorted(overlap)}')
    if m['alert_model'] not in prod['names']:
        raise ValueError('The alert model must be a production-grade model')
    if prov.get('contributes_to_production', True):
        raise ValueError('Provisional models must not contribute to production classifications')
    for window in (m['development_window'], prov['existing_development_window']):
        if window[1] >= '2024-01-01':
            raise ValueError('Development windows must end before 2024')
    a = config['alerts']
    if a['levels'] != ['NORMAL','ELEVATED','CRITICAL']:
        raise ValueError('Alert levels must be NORMAL, ELEVATED, CRITICAL')
    if not 0 < a['elevated_percentile'] < a['critical_percentile'] < 100:
        raise ValueError('Require 0 < elevated percentile < critical percentile < 100')
    if a.get('thresholds_optimized_on_2024', True):
        raise ValueError('Thresholds must not be optimized on 2024')
    if not a.get('no_model_substitution', False):
        raise ValueError('Model substitution is not permitted')
    if int(a['deescalation_consecutive_sessions']) < 1:
        raise ValueError('De-escalation requires at least one session')
    if set(a['risk_fields']) & set(a['reliability_fields']):
        raise ValueError('Risk and reliability fields must be disjoint')
    for text in REQUIRED_LIMITATIONS:
        if text not in a['standard_limitations']:
            raise ValueError(f'Missing required limitation: {text}')
    e = config['events']
    if not 0 < e['elevated_realized_percentile'] < e['critical_realized_percentile'] < 100:
        raise ValueError('Invalid realized-event percentiles')
    if config['schedule']['primary_horizon_sessions'] != 1:
        raise ValueError('The registered primary horizon is one session')
    ev = config['evaluation']
    if ev['early_stopping'] or ev['extension']:
        raise ValueError('Evaluation length is fixed in advance')
    if ev['minimum_eligible_sessions'] > ev['sessions']:
        raise ValueError('Minimum eligible sessions exceeds the evaluation length')
    required = {'precision','recall','false_positive_rate','missed_event_rate'}
    if not required <= set(ev['alert_metrics']):
        raise ValueError('Alert metrics must include precision, recall, false-positive and missed-event rates')
    return True


def model_inventory(config):
    m = config['models']; prov = m['provisional']; rows = []
    for name in m['production']['names']:
        rows.append(dict(model=name,grade='PRODUCTION',group='audited_daily',
                         role='alert_model' if name == m['alert_model'] else 'production_shadow',
                         contributes_to_production=True,status='existing_forecasts'))
    for key, status in (('existing_close_to_close','existing_close_to_close_forecasts'),
                        ('requires_respecification','requires_horizon1_close_to_close_respecification'),
                        ('archived_comparators','archived_comparator')):
        for name in prov[key]:
            rows.append(dict(model=name,grade='PROVISIONAL',group=key,role='provisional_shadow',
                             contributes_to_production=False,status=status))
    for row in rows: row['target'] = config['risk']['common_target']
    return rows


def assert_prospective_allowed(config, config_path, registration=None):
    """Prospective collection requires FROZEN status AND a registration whose hash matches the config file."""
    if config['protocol']['status'] != FROZEN:
        raise ProtocolNotFrozen('H4 protocol is a draft; prospective collection and evaluation are not authorized')
    if registration is None or registration.get('config_sha256') != sha256(Path(config_path)):
        raise ProtocolNotFrozen('No matching timestamped registration for this configuration')
    return True


def production_view(forecasts, config):
    """Filter a per-model forecast mapping to production-grade models only (provisional never leak in)."""
    allowed = set(config['models']['production']['names'])
    return {k:v for k,v in forecasts.items() if k in allowed}
