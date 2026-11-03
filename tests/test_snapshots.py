"""Synthetic source snapshots only, written inside pytest temporary directories."""

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from volrisk.cli import main
from volrisk.data.models import ASSETS, DataError
from volrisk.data.normalization import normalize_nifty
from volrisk.data.pipeline import run_pipeline
from volrisk.data.storage import sha256


@pytest.fixture
def snapshot_settings(settings, raw_frame):
    yahoo = settings.raw_dir.parent / 'inputs/yahoo'
    nifty = settings.raw_dir.parent / 'inputs/nifty'
    yahoo.mkdir(parents=True)
    (nifty / 'source').mkdir(parents=True)
    for asset in ASSETS[:2]:
        raw = raw_frame if asset.symbol == 'SPY' else raw_frame.iloc[[0, 2]]
        filename = f'{asset.symbol}_yfinance_raw.parquet'
        raw.to_parquet(yahoo / filename)
        metadata = {
            'symbol':asset.symbol, 'currency':'USD', 'price_convention':asset.price_convention,
            'source_url':asset.source_url, 'retrieved_at_utc':'2024-01-05T10:00:00+00:00',
            'request':{'tickers':asset.symbol, 'start':'2024-01-02', 'end':'2024-01-05',
                       'interval':'1d','auto_adjust':True,'actions':True,'back_adjust':False,
                       'repair':False,'keepna':True,'rounding':False},
            'raw_snapshot':filename,'raw_sha256':sha256(yahoo / filename),
        }
        (yahoo / f'{asset.symbol}_metadata.json').write_text(json.dumps(metadata),encoding='utf-8')
    raw_json = nifty / 'source/tri_2024_response.json'
    raw_json.write_text(json.dumps([
        {'Index Name':'Nifty 50','Date':'04 Jan 2024','TotalReturnsIndex':'900','NTR_Value':'800'},
        {'Index Name':'Nifty 50','Date':'02 Jan 2024','TotalReturnsIndex':'1000','NTR_Value':'900'},
    ]),encoding='utf-8')
    provenance = {
        'index':'NIFTY 50','series':'Gross Total Returns Index','currency_basis':'INR',
        'endpoint':'https://www.niftyindices.com/BackPage/getTotalReturnIndexString',
        'source_page':'https://www.niftyindices.com/reports/historical-data','method':'POST',
        'source_responses':[{'file':'source/tri_2024_response.json','sha256':sha256(raw_json),
                             'saved_at_utc':'2024-01-05T10:00:00Z','observations':2,
                             'request':{'name':'NIFTY 50','indexName':'NIFTY 50',
                                        'startDate':'02-Jan-2024','endDate':'04-Jan-2024'}}],
    }
    (nifty / 'provenance.json').write_text(json.dumps(provenance),encoding='utf-8')
    return replace(settings,etf_snapshot_dir=yahoo,nifty_json_dir=nifty)


def no_network(*args, **kwargs):
    pytest.fail('Offline source replay must not call a downloader')


def test_replay_preserves_bytes_calendars_currencies_and_provenance(snapshot_settings, raw_frame):
    result = run_pipeline(snapshot_settings,downloader=no_network)
    assert result['complete']
    manifest = json.loads(Path(result['manifest']).read_text())
    assert manifest['implementation_sha256']['data/normalization.py']
    assert manifest['required_columns'] == ['date','asset','price','daily_return','currency','source','price_convention']
    for item in manifest['assets']:
        for record in item['raw']:
            assert Path(record['path']).read_bytes() == Path(record['original_path']).read_bytes()
            assert sha256(Path(record['path'])) == record['sha256']
        frame = pd.read_parquet(result['processed'][item['symbol']])
        assert frame.columns[:7].tolist() == manifest['required_columns']
        assert frame['asset'].eq(item['symbol']).all()
        assert frame['currency'].eq('INR' if item['symbol']=='NIFTY50_TRI' else 'USD').all()
        expected_dates = raw_frame.index if item['symbol']=='SPY' else raw_frame.index[[0,2]]
        assert frame['date'].tolist() == expected_dates.tolist()
        np.testing.assert_allclose(frame['daily_return'],frame['price']/frame['price'].shift(1)-1,equal_nan=True)
        assert pd.isna(frame['daily_return'].iloc[0])
    assert manifest['assets'][0]['acquisition']['retrieved_at_utc']=='2024-01-05T10:00:00+00:00'
    acquisition = manifest['assets'][2]['acquisition']
    assert acquisition['retrieved_at_utc'] is None
    assert acquisition['responses'][0]['response_saved_at_utc']=='2024-01-05T10:00:00Z'
    assert manifest['assets'][2]['source']=='NSE Indices official JSON responses'
    repeated = run_pipeline(snapshot_settings,downloader=no_network)
    assert repeated['run_id'] != result['run_id']
    for symbol in result['processed']:
        pd.testing.assert_frame_equal(pd.read_parquet(result['processed'][symbol]),pd.read_parquet(repeated['processed'][symbol]))


def test_changed_source_is_rejected_without_blocking_other_assets(snapshot_settings):
    source = snapshot_settings.etf_snapshot_dir / 'SPY_yfinance_raw.parquet'
    source.write_bytes(source.read_bytes()+b'changed')
    result = run_pipeline(snapshot_settings,downloader=no_network)
    assert not result['complete']
    assert set(result['processed'])=={'VT','NIFTY50_TRI'}
    assert 'SHA-256 mismatch' in result['assets'][0]['issues'][0]['message']
    manifest = json.loads(Path(result['manifest']).read_text())
    assert len(manifest['assets'][0]['raw'])==2  # Metadata and altered payload retained as evidence.


@pytest.mark.parametrize('change', [
    {'symbol':'VT'}, {'currency':'INR'}, {'raw_sha256':None},
    {'retrieved_at_utc':'2024-01-05T10:00:00'}, {'raw_snapshot':'../outside.parquet'},
])
def test_bad_etf_metadata_is_rejected(snapshot_settings, change):
    path=snapshot_settings.etf_snapshot_dir / 'SPY_metadata.json'
    meta=json.loads(path.read_text())
    meta.update(change)
    path.write_text(json.dumps(meta))
    result=run_pipeline(snapshot_settings,downloader=no_network)
    assert result['assets'][0]['status']=='failed'
    assert 'SPY' not in result['processed']


@pytest.mark.parametrize('field,value', [('auto_adjust',False),('actions',False),('interval','1wk'),('auto_adjust',1)])
def test_snapshot_price_convention_is_enforced(snapshot_settings, field, value):
    path=snapshot_settings.etf_snapshot_dir / 'SPY_metadata.json'
    meta=json.loads(path.read_text())
    meta['request'][field]=value
    path.write_text(json.dumps(meta))
    result=run_pipeline(snapshot_settings,downloader=no_network)
    assert result['assets'][0]['status']=='failed'
    assert 'snapshot request' in result['assets'][0]['issues'][0]['message']


@pytest.mark.parametrize('change', [{'sha256':'0'*64},{'file':'../outside.json'},{'observations':500}])
def test_nifty_provenance_controls_are_enforced(snapshot_settings, change):
    path=snapshot_settings.nifty_json_dir / 'provenance.json'
    meta=json.loads(path.read_text())
    meta['source_responses'][0].update(change)
    path.write_text(json.dumps(meta))
    result=run_pipeline(snapshot_settings,downloader=no_network)
    assert result['assets'][2]['status']=='failed'
    assert set(result['processed'])=={'SPY','VT'}


def test_duplicate_manifest_entry_is_rejected(snapshot_settings):
    path=snapshot_settings.nifty_json_dir / 'provenance.json'
    meta=json.loads(path.read_text())
    meta['source_responses'] *= 2
    path.write_text(json.dumps(meta))
    result=run_pipeline(snapshot_settings,downloader=no_network)
    assert result['assets'][2]['status']=='failed'
    assert 'Duplicate source manifest entry' in result['assets'][2]['issues'][0]['message']


def test_offline_cli_and_fail_on_warning(snapshot_settings, monkeypatch, tmp_path):
    monkeypatch.setattr('volrisk.cli.load_settings',lambda path:snapshot_settings)
    monkeypatch.setattr('volrisk.data.pipeline.download_etf',no_network)
    config=tmp_path/'config.toml'
    config.write_text('# Synthetic test config')
    assert main(['--config',str(config)])==0
    assert main(['--config',str(config),'--fail-on-warning'])==1  # Descending NSE source dates.


@pytest.mark.parametrize('row', [
    {'Index Name':'NIFTY NEXT 50','Date':'02 Jan 2024','TotalReturnsIndex':'100'},
    {'Index Name':'NIFTY 50','Date':'02 Jan 2024','NTR_Value':'100'},
])
def test_wrong_index_and_net_return_json_rejected(settings,tmp_path,row):
    path=tmp_path/'response.json'
    path.write_text(json.dumps([row]))
    with pytest.raises(DataError):
        normalize_nifty([path],ASSETS[2],settings.start,settings.end)
