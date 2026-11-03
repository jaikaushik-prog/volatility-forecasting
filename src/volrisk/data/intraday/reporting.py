"""Descriptive integration reports. No model fitting, selection, or pooled-market results."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from volrisk.data.storage import write_text


def table(frame):
    def cell(x):
        if pd.isna(x): return 'missing'
        if isinstance(x, (float, np.floating)): return f'{x:.6g}'
        return str(x).replace('|', '/').replace('\n', ' ')
    cols=list(frame.columns)
    return '\n'.join(['| '+' | '.join(cols)+' |', '| '+' | '.join(['---']*len(cols))+' |']+
                     ['| '+' | '.join(cell(x) for x in row)+' |' for row in frame.itertuples(index=False,name=None)])


def _plots(run, dailies, vix, sessions, annualization):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=run/'reports'/'figures'/'intraday'
    folder.mkdir(parents=True,exist_ok=True)
    paths=[]
    def save(fig,name):
        fig.suptitle(fig._suptitle.get_text()+' — provisional source conventions' if fig._suptitle else 'Provisional source conventions',fontsize=11)
        fig.tight_layout()
        path=folder/(name+'.png')
        fig.savefig(path,dpi=150)
        plt.close(fig)
        paths.append(str(path.relative_to(run/'reports')).replace('\\','/'))
    for key,d in dailies.items():
        regular=d.session_kind.eq('regular') & d.rv_eligible
        cols=[f'rv_{f}min' for f in (1,5,10,15)]
        sample=d.loc[regular].dropna(subset=cols)
        fig,ax=plt.subplots(2,1,figsize=(12,7))
        for f in (1,5,10,15):
            ax[0].plot(d.session_date,np.sqrt(d[f'rv_{f}min']*annualization)*100,label=f'{f} min',lw=.65,alpha=.75)
        ax[0].set_ylabel('Annualized intraday RV volatility (%)')
        ax[0].legend(ncol=4)
        ax[1].plot([1,5,10,15],sample[cols].mean(),marker='o')
        ax[1].set(xlabel='Sampling interval (minutes); 10-min has final 5-min interval',ylabel='Mean daily intraday variance (decimal²)')
        ax[1].set_title(f'Signature plot: {len(sample)} matched complete regular sessions')
        fig.suptitle(f'{key.upper()} — RV across frequencies; special days retain actual duration')
        save(fig,key+'_rv_frequencies')
        fig,ax=plt.subplots(2,1,figsize=(12,7))
        ax[0].plot(d.session_date,d.overnight_risk_share*100,lw=.7)
        ax[0].set_ylabel('Overnight / full RV proxy (%)')
        positive=sample[sample.rv_5min.gt(0)]
        ratio=positive.rv_1min/positive.rv_5min
        ax[1].hist(ratio.dropna(),bins=50,color='#2b7489')
        ax[1].set(xlabel='1-minute / 5-minute RV, matched regular sessions',ylabel='Sessions')
        fig.suptitle(f'{key.upper()} — overnight share and sampling sensitivity')
        save(fig,key+'_overnight_signature')
        fig,ax=plt.subplots(2,1,figsize=(12,7))
        if len(sample):
            stressful=sample.nlargest(1,'rv_5min').iloc[0].session_date
            event=d[(d.session_date>=stressful-pd.Timedelta(days=15)) & (d.session_date<=stressful+pd.Timedelta(days=15))]
            for f in (1,5,10,15):
                ax[0].plot(event.session_date,event[f'rv_{f}min'],label=f'{f} min',marker='.',lw=1)
            ax[0].legend(ncol=4)
            ax[0].set_title(f'Window around largest observed regular-session RV: {stressful.date()} (retrospective)')
            ax[1].scatter(positive.rv_5min,positive.rv_1min,s=8,alpha=.4)
        ax[0].set_ylabel('Intraday variance (decimal²)')
        ax[1].set(xlabel='5-minute RV',ylabel='1-minute RV')
        fig.suptitle(f'{key.upper()} — descriptive stress and frequency agreement')
        save(fig,key+'_stress_diagnostics')
    fig,axes=plt.subplots(3,1,figsize=(13,8))
    for ax,(asset,g) in zip(axes,sessions.groupby('asset',sort=True)):
        monthly=g.assign(month=g.session_date.dt.to_period('M').dt.to_timestamp()).groupby('month').agg(
            complete=('session_complete','sum'),observed=('source_rows',lambda x:int((x>0).sum())),expected=('expected_session','sum'))
        ax.plot(monthly.index,monthly.expected,label='Expected/candidate sessions')
        ax.plot(monthly.index,monthly.complete,label='Complete sessions')
        ax.plot(monthly.index,monthly.observed,label='Observed sessions',ls=':')
        ax.set_ylabel(asset)
    axes[0].legend(ncol=3)
    fig.suptitle('Exchange-specific session completeness; unverified schedules cannot pass')
    save(fig,'session_completeness')
    fig,ax=plt.subplots(figsize=(13,5))
    ax.plot(vix.session_date,vix.vix_eod_percent,label='India VIX: annualized %, ~30 calendar days',lw=.8)
    ax.plot(vix.session_date,vix.trailing_full_rv22_annualized_vol_decimal*100,label='Trailing 22-session full RV: annualized %',lw=.8)
    ax.set_ylabel('Annualized volatility (%)')
    ax.legend()
    fig.suptitle('NIFTY / India VIX — comparable units, different forward/backward horizons')
    save(fig,'nifty_vix_comparison')
    fig,ax=plt.subplots(figsize=(13,4))
    for i,(key,d) in enumerate(dailies.items()):
        ax.scatter(d.loc[d.rv_eligible,'session_date'],np.full(int(d.rv_eligible.sum()),i),s=3,label=key+' complete RV')
    valid=vix.vix_eod_available
    ax.scatter(vix.loc[valid,'session_date'],np.full(int(valid.sum()),2),s=3,label='VIX EOD at NIFTY close')
    ax.set_yticks([0,1,2],['NIFTY','SENSEX','India VIX'])
    ax.legend(loc='upper left',ncol=3)
    fig.suptitle('Usable numerical coverage on each native session grid')
    save(fig,'joint_coverage')
    return paths


def build_reports(run, manifest, normalized, dailies, vix, sessions, cov, *, make_figures=True):
    folder=run/'reports'
    annualization=manifest['config']['sessions_per_year']
    sources=pd.DataFrame(manifest['source_files'])
    audit=['# Intraday data audit', '', '**PROVISIONAL — NOT CERTIFIED FOR FORECAST RESEARCH.** '
        'The user does not know the vendor or export conventions. Numerical consistency does not verify source identity. '
        'Asia/Kolkata and start-of-minute OHLC labels are explicit working assumptions. All supplied datasets retain '
        '`research_ready=False`. NIFTY/SENSEX are spot-index candidates; the minute NIFTY series is not treated as NIFTY TRI.',
        '',f'Content-addressed run: `{manifest["run_id"]}`. Imported: {manifest["created_at_utc"]}. '
        'Original download times are unknown; filesystem modification time is recorded separately.', '',
        '## Actual source files', '',table(sources[['filename','rows','first_timestamp','last_timestamp','sorted_in_source','duplicate_timestamps']]),'']
    for source in manifest['source_files']:
        audit += [f'### {source["filename"]}', '', 'OHLC schema: '+', '.join(f'`{c}: {t}`' for c,t in source['dtypes'].items())+'.',
            f'Time column: `{source["timestamp_column"]}`; original timezone: {source["source_timezone"]}. '
            f'Stock codes: {source["stock_codes"] or "not encoded"}; exchanges: {source["exchanges"] or "not encoded"}. '
            f'Invalid timestamps: {source["invalid_timestamps"]}. SHA-256: `{source["sha256"]}`.', '']
    audit += ['The pickle is hashed as opaque bytes only and is never deserialized. Its contents and coverage are unknown. '
              'It can be omitted safely from this workflow because the CSV supplies the VIX observations used here. '
              'Zero volume fields are preserved; index volume is not interpreted as traded share volume.', '',
              '## Canonicalization and flagged observations','',
              'Source files are never rewritten. Sorting is deterministic. Duplicate timestamps with identical market fields '
              '(ignoring export row indices) keep the first filename/row; removed copies are quarantined. All copies of '
              'conflicting timestamps are quarantined. Invalid prices and OHLC, off-grid timestamps and outside-session '
              'rows remain flagged in canonical data. No interpolation, forward-fill, extreme-return deletion or winsorization occurs. '
              'Whole-file MAD is retrospective QC only and never a forecasting feature or exclusion rule. A flag is not proof of error.','']
    counts=[]
    for key,action in manifest['cleaning_actions'].items():
        counts.append({'asset':key,'canonical_rows':action['normalized_rows'],'duplicate_copies_removed':action['identical_duplicates_removed'],
                       'conflicting_timestamps':action['conflicting_timestamps'],**action['flag_counts']})
    audit += [table(pd.DataFrame(counts)), '', 'Quality thresholds (log-return units):', '',
              '```json',json.dumps(manifest['config']['quality'],indent=2),'```','',
              'Exact flagged records and original row/file identifiers are in this run’s `audit/*_flagged_observations.parquet` '
              'and `audit/*_quarantined.parquet`. `intraday_session_quality.csv` lists every missing minute and candidate session.','',
              '## Exchange calendars and gaps', '',
              'NSE dates reuse the existing hash-verified cash-market calendar. BSE dates use independently reviewed BSE-authored '
              'annual/amendment notices, with syndicated/mirrored originals where direct access failed. '
              'The source register below distinguishes indexed extracts from archived PDFs. It is not a claim that every new PDF was downloaded. '
              'Unverified exceptional times have no invented minute grid; unknown weekdays remain candidate sessions and interrupt overnight adjacency. '
              'NSE 2015–2022 Muhurat timing, the 2015 budget session and 2021-02-24 outage schedule remain unverified where present. '
              'BSE special-session times not explicitly verified in configuration, including the January 2024 amendments, remain unverified.','']
    summary=[]
    for key,frame in normalized.items():
        asset=frame.asset.iloc[0]
        s=sessions[sessions.asset.eq(asset)]
        known=s.schedule_verified
        numerical=int(dailies[key].rv_eligible.sum()) if key in dailies else int((s.session_complete & known).sum())
        record={'asset':asset,'raw_rows':int(sum(x['rows'] for x in manifest['source_files'] if x['asset']==asset)),
            'normalized_rows':len(frame),'first':str(frame.timestamp.min()),'last':str(frame.timestamp.max()),
            'observed_sessions':int((s.source_rows>0).sum()),'verified_scheduled_sessions':int(known.sum()),
            'missing_verified_sessions':int((known & s.source_rows.eq(0)).sum()),
            'incomplete_verified_sessions':int((known & ~s.session_complete & s.source_rows.gt(0)).sum()),
            'unverified_candidate_sessions':int((~known & s.expected_session).sum()),
            'complete_numerical_sessions':numerical,'research_ready':False}
        summary.append(record)
        gaps=s[~s.session_complete | ~known]
        gaps.to_csv(folder/f'{key}_session_issues.csv',index=False)
    audit += [table(pd.DataFrame(summary)), '',
              'Complete numerical sessions still depend on unverified source conventions. FAIL in session CSV means unusable '
              'for complete-session RV; WARNING means numerically complete but provisional. Missing/unverified sessions are '
              'retained rather than dropped from feature windows. Missing-session counts are restricted to verified schedules.', '',
              '### Exact missing and unverified sessions', '',
              table(sessions.loc[sessions.schedule_verified & sessions.source_rows.eq(0),
                  ['asset','session_date','session_kind','expected_minutes']]), '',
              'Unverified schedules below are limitations, not established data errors:', '',
              table(sessions.loc[~sessions.schedule_verified,['asset','session_date','session_kind','source_rows']]), '',
              'Incomplete NIFTY sessions (the full SENSEX/VIX lists are in their session-issues CSVs):', '',
              table(sessions.loc[sessions.asset.eq('NIFTY') & sessions.schedule_verified & ~sessions.session_complete,
                  ['session_date','missing_minutes','missing_minute_times']]), '',
              '### File boundaries', '']
    for asset,g in sources.groupby('asset'):
        ordered=g.sort_values('first_timestamp')
        for a,b in zip(ordered.to_dict('records'),ordered.to_dict('records')[1:]):
            lo=pd.Timestamp(a['last_timestamp']).tz_localize(None).normalize()
            hi=pd.Timestamp(b['first_timestamp']).tz_localize(None).normalize()
            between=sessions[sessions.asset.eq(asset)&sessions.session_date.gt(lo)&sessions.session_date.lt(hi)]
            audit.append(f'- {asset}: `{a["filename"]}` ends {a["last_timestamp"]}; `{b["filename"]}` starts {b["first_timestamp"]}. '
                         f'{int(between.schedule_verified.sum())} verified sessions lie strictly between the files. '
                         f'{int((between.schedule_verified & between.source_rows.eq(0)).sum())} of those have no observations.')
    audit += ['', '### Calendar and instrument-convention sources', '']
    audit += [f'- [{e["id"]}]({e["source"]}): {e["finding"]}' for e in manifest['calendar_evidence']]
    audit += ['', '## Audit trail and rerun', '',
              'Existing modules inspected/reused: `data/storage.py`, `data/calendar_audit.py`, '
              '`data/return_audit.py`, `data/returns.py`, the forecasting/evaluation packages, '
              '`config/calendars.json`, its archived evidence/amendments, existing audit/experiment manifests, '
              '`pyproject.toml`, README and the existing test suite. Intraday files live in a separate package; '
              'daily model and dataset outputs are not overwritten.', '',
              'The immutable `manifest.json` records input/code/output SHA-256 hashes, package versions, import timestamps, '
              'source schemas, calendar evidence, cleaning actions and thresholds. `reports/latest_intraday.json` points to it. '
              'Identical inputs/code/configuration reuse the same verified outputs. Changed inputs create a separate run.', '',
              '```powershell',r'.\.venv\Scripts\python.exe -m volrisk.intraday_cli --config config/intraday.toml','```','']
    write_text('\n'.join(audit),folder/'intraday_data_audit.md')
    statistics=[]
    stresses=[]
    for key,d in dailies.items():
        matched=d[d.session_kind.eq('regular')].dropna(subset=[f'rv_{f}min' for f in (1,5,10,15)])
        for f in (1,5,10,15):
            r=matched[f'rv_{f}min']
            statistics.append({'asset':key,'frequency_minutes':f,'matched_regular_sessions':len(r),'mean_rv':r.mean(),
                'median_rv':r.median(),'p95_rv':r.quantile(.95),'max_rv':r.max(),
                'mean_annualized_vol_percent':(np.sqrt(r*annualization)*100).mean()})
        cols=['session_date','rv_1min','rv_5min','rv_10min','rv_15min','overnight_squared_return','overnight_risk_share']
        stresses.append(matched.nlargest(10,'rv_5min')[cols].assign(asset=key))
    stats=pd.DataFrame(statistics)
    stats.to_csv(folder/'realized_frequency_statistics.csv',index=False)
    stress=pd.concat(stresses,ignore_index=True)
    stress.to_csv(folder/'intraday_stress_sessions.csv',index=False)
    nifty=dailies['nifty']; sensex=dailies['sensex']
    joint=int((nifty.rv_eligible.to_numpy() & vix.vix_eod_available.to_numpy()).sum())
    overlap=set(nifty.loc[nifty.rv_eligible,'session_date']) & set(sensex.loc[sensex.rv_eligible,'session_date'])
    findings=['# Realized-volatility integration summary', '', '**Descriptive, provisional results only. No forecasting models or strategies were run.**', '',
        '## Definitions and availability', '',
        'Bars are start-labelled, left-closed/right-open intervals anchored separately to each continuous exchange segment. '
        'A bar is available only at its end. Non-overlapping 1/5/10/15-minute bars require every constituent minute to be valid. '
        'A regular session has 375 minutes: 10-minute sampling therefore ends with a labelled 5-minute interval. '
        'No synthetic bars fill gaps. Each segment’s return path starts with its observed opening price, followed by bar closes. '
        'RV is the sum of squared log returns (decimal-return squared units); realized volatility is its square root. '
        'First-bar open-to-close returns are included. Scheduled-break reopening returns and overnight returns are separate. '
        'Full-session RV adds squared reopening returns; the full RV proxy adds overnight squared return. '
        'Overnight returns require consecutive known session endpoints, including across verified weekends/holidays, '
        f'and never bridge an absent or unverified candidate session. Annualized volatility is sqrt({annualization} × daily variance). '
        'Short sessions are not extrapolated to full-day duration; regular-session frequency comparisons exclude them.', '',
        'Strict completeness is 100% of valid expected minutes. Incomplete-session RV is missing, not zero. '
        'Observed endpoints may still support overnight/c2c returns even if a session’s interior is incomplete. '
        'Positive plus negative semivariance equals intraday RV. Five-minute finite-sample adjusted bipower variation '
        'uses adjacent absolute returns within each segment; max(RV−BPV,0) is a descriptive jump proxy, not a formal jump test. '
        'It requires at least the configured interval count and equal interval lengths within segments.', '',
        'Daily lagged RV features shift by one expected/candidate session, then use full 5/22-session windows. '
        'Missing sessions break windows. Volatility of volatility is the sample standard deviation of sqrt(RV) over 22 past sessions. '
        'Current-day realized measures and VIX features are available at the recorded session close; lagged columns are explicitly named. '
        'Forecast targets must be shifted to the next session by a future modeling workflow.', '',
        '## Frequency comparison on matched complete regular sessions', '',table(stats),'']
    for key,d in dailies.items():
        m=d[d.session_kind.eq('regular') & d.rv_5min.gt(0)].dropna(subset=['rv_1min','rv_5min'])
        share=d[d.session_kind.eq('regular')].dropna(subset=['overnight_risk_share'])
        ratio=(m.rv_1min/m.rv_5min).median()
        aggregate=share.overnight_squared_return.sum()/share.full_rv_proxy_5min.sum() if share.full_rv_proxy_5min.sum()>0 else np.nan
        findings += [f'- {key.upper()}: median paired RV(1m)/RV(5m) = {ratio:.4g}; '
            f'median overnight risk share = {share.overnight_risk_share.median():.2%}; '
            f'aggregate overnight share = {aggregate:.2%} over {len(share)} complete regular sessions with valid overnight endpoints.']
    findings += ['', 'Higher 1-minute RV can reflect sampling sensitivity, noise or genuine within-interval price variation. '
                 'These data alone do not identify microstructure noise. The largest-RV sessions below and the saved plots '
                 'show stress-period agreement/divergence without declaring one frequency the truth. No forecast stability or accuracy claim is made.', '',
                 table(stress.head(5) if stress.empty else stress.groupby('asset',sort=False).head(3)), '',
                 '## India VIX and shared coverage', '',
                 f'VIX EOD is available on **{int(vix.vix_eod_available.sum())} / {len(vix)}** NIFTY candidate sessions. '
                 f'Joint complete NIFTY RV / available VIX: **{joint}** sessions. '
                 f'Complete NIFTY/SENSEX overlap: **{len(overlap)}** sessions. '
                 'These are coverage intersections for diagnostics; native datasets retain their full calendars.', '',
                 'VIX is a separate implied-volatility series. Its minute changes are never NIFTY RV. EOD uses only valid same-session '
                 'observations available at or before the NIFTY close, within the configured 90-second age limit. Missing VIX is not carried forward. '
                 'Levels in percentage points are divided by 100 for annualized decimal volatility. India VIX describes approximately '
                 f'30 calendar days of forward implied volatility. The trailing comparison uses 22 sessions of full RV, annualized with {annualization}. '
                 f'Both 30-calendar-day variance proxies multiply annualized variance by 30/{manifest["config"]["calendar_days_per_year"]}. This assumes linear variance accrual '
                 f'and {annualization} trading sessions/year; forward option-implied and backward realized horizons/measurement remain different. '
                 'The difference is not identified as a volatility risk premium. Percentiles compare the current VIX only with strictly earlier '
                 'observations in a 252-session window (minimum 60); missing observations reduce history and never get filled.', '',
                 'Detailed per-column availability, earliest/latest usable dates and missing counts: `intraday_feature_coverage.csv`.', '',
                 '## Research readiness and next experiments', '',
                 'All outputs are provisional until vendor, instrument identity, timezone and bar labels can be independently established. '
                 'Review duplicate provenance, outside-session rows, invalid VIX OHLC, missing SENSEX minutes and unresolved special schedules. '
                 'Do not certify a series merely because its prices or hours look plausible. The daily NIFTY TRI pipeline remains separate.', '',
                 'After those checks: predeclare sampling-frequency robustness comparisons, then evaluate a HAR-RV baseline, '
                 'overnight/intraday decomposition, lagged VIX ablations and joint-market features using origin timestamps and time-series splits. '
                 'This integration implements none of those forecast models. Descriptive inspection of 2025–2026 here does not create a new untouched holdout.', '']
    paths=_plots(run,dailies,vix,sessions,annualization) if make_figures else []
    findings += ['## Saved figures', '']+[f'- [{p}]({p})' for p in paths]
    write_text('\n'.join(findings)+'\n',folder/'realized_volatility_summary.md')
    return {'assets':summary,'joint_nifty_vix_sessions':joint,'nifty_sensex_overlap':len(overlap),
            'vix_eod_available':int(vix.vix_eod_available.sum()),'figures':paths,'research_ready':False}
