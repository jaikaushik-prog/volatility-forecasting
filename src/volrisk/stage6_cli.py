"""Stage 6 economic failure diagnosis: read-only analysis of the saved Stage 5 run.

Writes diagnostic tables and figures only. It never trades, never simulates a new
allocation rule, never refits a model and never reads observations after 2024.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from volrisk.data.storage import sha256, write_json, write_text
from volrisk.economics import diagnosis

CODE = ['src/volrisk/economics/diagnosis.py','src/volrisk/stage6_cli.py']
PALETTE = {'ewma':'#2a78d6','garch':'#eb6834','har_daily':'#1baf7a','log_har_daily':'#eda100','log_har_vix_daily':'#e87ba4'}
MARKERS = {'ewma':'o','garch':'s','har_daily':'^','log_har_daily':'D','log_har_vix_daily':'v'}
LABEL = {'ewma':'EWMA','garch':'GARCH','har_daily':'HAR','log_har_daily':'Log-HAR','log_har_vix_daily':'Log-HAR+VIX'}
INK, MUTED, GRID = '#0b0b0b', '#52514e', '#e4e3df'
TITLE = 'EXPLORATORY / PROVISIONAL / NON-EXECUTABLE NIFTY TRI 2024 - retrospective diagnosis'


def snapshot(paths):
    out = {}
    for base in paths:
        for p in sorted(Path(base).rglob('*')):
            if p.is_file() and 'stage6' not in p.as_posix():
                out[p.as_posix()] = sha256(p)
    return out


def _style(ax):
    ax.grid(axis='y',color=GRID,linewidth=.6); ax.set_axisbelow(True)
    for side in ('top','right'): ax.spines[side].set_visible(False)
    for side in ('left','bottom'): ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED,labelsize=8)


def _finish(fig, path):
    fig.suptitle(TITLE,fontsize=9,color=MUTED); fig.tight_layout(rect=(0,0,1,.95))
    fig.savefig(path,dpi=150,facecolor='#fcfcfb'); plt.close(fig)


def figures(tables, out):
    out.mkdir(parents=True,exist_ok=True)
    models = diagnosis.PRIMARY_MODELS
    # 1. Terminal-wealth decomposition: one panel per model (no stacked colour ambiguity).
    d = tables['terminal_decomposition'].set_index('model')
    comps = [('avoided_loss_total','Avoided losses'),('missed_rebound','Missed rebounds'),('missed_positive_other','Other missed upside'),
             ('transaction_cost','Transaction costs'),('wealth_scale','Compounding'),('forecast_failure_holding','Failure holdings')]
    fig, axes = plt.subplots(1,len(models),figsize=(15,4.2),sharey=True)
    for ax,m in zip(axes,models):
        vals = [100*d.loc[m,c] for c,_ in comps]
        ax.barh(range(len(comps)),vals,color=PALETTE[m],height=.6,edgecolor='#fcfcfb',linewidth=2)
        ax.axvline(0,color=MUTED,linewidth=.8); ax.invert_yaxis()
        ax.set_yticks(range(len(comps)),[n for _,n in comps],fontsize=8,color=INK)
        ax.set_title(f"{LABEL[m]}  total {100*d.loc[m,'terminal_return_difference']:+.2f} pp",fontsize=9,color=INK)
        ax.set_xlabel('pp of initial capital vs buy-and-hold',fontsize=8,color=MUTED); _style(ax); ax.grid(axis='x',color=GRID,linewidth=.6)
        lo, hi = min(vals+[0]), max(vals+[0]); pad = .3*(hi-lo)
        ax.set_xlim(lo-pad,hi+pad)
        for y,v in enumerate(vals):
            if abs(v) > .05: ax.text(v,y,f' {v:+.1f} ',va='center',ha='left' if v>=0 else 'right',fontsize=7,color=INK)
    _finish(fig,out/'terminal_decomposition.png')
    # 2. Forecast and exposure around the largest shock (2024-06-04): two small multiples, one axis each.
    paths = tables['shock_event_paths']; paths = paths[paths.shock_date.astype(str).eq('2024-06-04')]
    fig, axes = plt.subplots(2,1,figsize=(11,7),sharex=True)
    for m in models:
        p = paths[paths.model.eq(m)]
        axes[0].plot(p.offset,100*p.forecast_vol,color=PALETTE[m],linewidth=2,marker=MARKERS[m],markersize=5,label=LABEL[m])
        axes[1].plot(p.offset,100*p.exposure,color=PALETTE[m],linewidth=2,marker=MARKERS[m],markersize=5,label=LABEL[m])
    axes[0].axhline(12,color=MUTED,linestyle='--',linewidth=1); axes[0].text(p.offset.iloc[0],12.5,'12% target',fontsize=7,color=MUTED)
    axes[0].set_ylabel('Forecast stored on row (annualized %)',fontsize=8,color=MUTED)
    axes[1].set_ylabel('Equity exposure for session (%)',fontsize=8,color=MUTED)
    axes[1].set_xlabel('Sessions relative to 2024-06-04 (NIFTY TRI -5.86%)',fontsize=8,color=MUTED)
    r = paths[paths.model.eq(models[0])]
    for ax in axes:
        _style(ax); ax.axvline(0,color=MUTED,linewidth=.8)
    ax2 = axes[1]
    for x,v in zip(r.offset,r.equity_return):
        if abs(v) >= .015: ax2.text(x,ax2.get_ylim()[0]+2,f'{100*v:+.1f}%',fontsize=6.5,color=MUTED,ha='center')
    for ax in axes: ax.legend(fontsize=8,frameon=False,ncol=5,loc='upper right' if ax is axes[0] else 'lower right')
    _finish(fig,out/'june_shock_forecast_and_exposure.png')
    # 3. Exposure versus Sharpe: constants share one Sharpe, dynamics fall below it.
    c = tables['constant_benchmarks']; cx = tables['complexity'].set_index('model')
    fig, ax = plt.subplots(figsize=(9,5.5))
    ax.scatter(100*c.average_equity_exposure,c.net_sharpe,color=MUTED,s=28,marker='x',label='Constant allocations (all deployable and ex-post)')
    for m in models:
        ax.scatter(100*cx.loc[m,'average_equity_exposure'],cx.loc[m,'net_sharpe'],color=PALETTE[m],s=70,marker=MARKERS[m],edgecolor='#fcfcfb',linewidth=1.5,zorder=3)
        dy = 8 if m == 'garch' else -10 if m == 'ewma' else -3
        ax.annotate(LABEL[m],(100*cx.loc[m,'average_equity_exposure'],cx.loc[m,'net_sharpe']),xytext=(6,dy),textcoords='offset points',fontsize=8,color=INK)
    ax.set_xlabel('Average equity exposure (%)',fontsize=8,color=MUTED); ax.set_ylabel('Net Sharpe, 0% cash scenario',fontsize=8,color=MUTED)
    ax.set_ylim(0,.9); _style(ax); ax.legend(fontsize=8,frameon=False,loc='lower left')
    _finish(fig,out/'exposure_vs_sharpe.png')
    return sorted(p.name for p in out.glob('*.png'))


def run(root='.'):
    root = Path(root).resolve()
    protected_dirs = [root/'reports',root/'experiments/stage5']
    before = snapshot(protected_dirs)
    data, tables = diagnosis.run_diagnosis(root)
    code_hashes = {rel:sha256(root/rel) for rel in CODE}
    identity = hashlib.sha256(json.dumps(dict(stage5=data['manifest']['run_id'],code=code_hashes),sort_keys=True).encode()).hexdigest()[:24]
    out = root/'experiments/stage6/runs'/identity
    (out/'tables').mkdir(parents=True,exist_ok=True)
    for name,frame in tables.items():
        frame.to_csv(out/'tables'/f'{name}.csv',index=False)
    names = figures(tables,out/'figures')
    published = root/'reports/figures/stage6'; published.mkdir(parents=True,exist_ok=True)
    for n in names: (published/n).write_bytes((out/'figures'/n).read_bytes())
    for name in ('terminal_decomposition','shock_event_study','forecast_bias','event_concentration'):
        (root/'reports'/f'stage6_{name}.csv').write_bytes((out/'tables'/f'{name}.csv').read_bytes())
    after = snapshot(protected_dirs)
    changed = sorted(k for k in before if before[k] != after.get(k))
    if changed:
        raise RuntimeError(f'Stage 6 modified protected artifacts: {changed[:5]}')
    d = tables['terminal_decomposition']
    manifest = dict(stage='6',status='EXPLORATORY_RETROSPECTIVE_DIAGNOSIS',created_utc=datetime.now(timezone.utc).isoformat(),
        run_id=identity,stage5_run=data['manifest']['run_id'],stage5_manifest_sha256=sha256(data['run']/'manifest.json'),
        stage5_output_files_verified=data['verified_files'],protected_files_unchanged=len(before),
        code_hashes=code_hashes,future_period_evaluated=False,new_policies_simulated=0,trades_executed=0,
        cutoff=str(diagnosis.CUTOFF.date()),max_reconciliation_error=float(d.reconciliation_error.abs().max()),
        reconciles_to_stage5=bool(d.matches_stage5.all()),
        output_hashes={p.relative_to(out).as_posix():sha256(p) for p in out.rglob('*') if p.is_file()})
    write_json(manifest,out/'manifest.json')
    write_json(dict(run=str(out.relative_to(root)),manifest_sha256=sha256(out/'manifest.json'),status=manifest['status']),root/'reports/latest_stage6.json')
    print('Stage 6 diagnosis written:',out.relative_to(root))
    return out, tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['run'])
    parser.add_argument('--root',default='.')
    args = parser.parse_args()
    run(args.root)


if __name__ == '__main__':
    main()
