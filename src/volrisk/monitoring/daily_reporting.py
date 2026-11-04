"""Self-contained HTML and Markdown reports. No network resources or JavaScript."""
from html import escape


def pct(value):
    return f'{value:.2%}' if value is not None else 'Unavailable'


def render_markdown(r):
    rows = '\n'.join(f"| {f['model']} | {pct(f['annualized_volatility'])} | {f['status']} | {f['message'].replace('|','/')} |"
                     for f in r['forecasts'])
    issues = '\n'.join(f"- {i['severity'].upper()}: {i['message']}" for i in r['quality_issues']) or '- No structural issues detected.'
    return f"""# NEXUS daily risk brief — {r['as_of']}

**{r['mode'].upper()} — {r['level']}** · NIFTY 50 TRI · Target session: {r['target_session'] or 'Unverified'}

{r['reason']}

**Review task:** {r['review_action']}

| Measure | Value |
| --- | --- |
| Next-session volatility, annualized | {pct(r['annualized_volatility'])} |
| Next-session volatility, daily | {pct(r['daily_volatility'])} |
| Elevated / critical thresholds | {pct(r['thresholds']['elevated'])} / {pct(r['thresholds']['critical'])} |
| Previous issued level | {r['previous_level'] or 'No earlier report'} |

## Comparison models

| Model | Annualized volatility | Fit status | Diagnostics |
| --- | --- | --- | --- |
{rows or '| — | Unavailable | No forecast | Resolve input issues |'}

## Large-move estimates

{r['probability_method']}. These estimates are for absolute log returns, in either direction.

- Probability of |return| > {pct(r['thresholds']['event_elevated'])}: {pct(r['probability_elevated'])}
- Probability of |return| > {pct(r['thresholds']['event_critical'])}: {pct(r['probability_critical'])}

## Data quality

{issues}

- Latest input session: {r['source_metadata'].get('last_return_date','Unavailable')}
- Source: {r['source_name']}
- Source identity confirmed by importer: {r['source_confirmed']}
- Retrieved at: {r['retrieved_at'] or 'Unknown — import time is not retrieval time'}
- Imported at: {r['imported_at']}
- Source SHA-256: {r['source_sha256'] or 'Unavailable'}
- Run ID: {r['run_id']}

## Scope

""" + '\n'.join(f'- {x}' for x in r['limitations'])+'\n'


def render_html(r):
    h = lambda x: escape(str(x),quote=True)
    state = r['level']; operational = state not in {'NORMAL','ELEVATED','CRITICAL'}
    color = {'NORMAL':'#176654','ELEVATED':'#946000','CRITICAL':'#a83037'}.get(state,'#5f6170')
    mode_note = {'demo':'SYNTHETIC DEMO · Generated sample prices. No market evidence.',
        'preview':'HISTORICAL PREVIEW · Pipeline check only. Not a live forecast.',
        'live':'REGISTERED ADVISORY REPORT · Forecast performance remains unvalidated.'}[r['mode']]
    rows=''.join(f"<tr><td>{h(f['model'])}{' <span class=small>· alert model</span>' if f['model']==r['alert_model'] else ''}</td>"
        f"<td>{h(pct(f['annualized_volatility']))}</td><td>{h(f['status'])}</td><td>{h(f['message'] or 'No fit warning')}</td></tr>"
        for f in r['forecasts']) or '<tr><td colspan="4">No forecast issued. Resolve the data or calendar issue below.</td></tr>'
    issues=''.join(f"<li><strong>{h(i['severity'].upper())}</strong> {h(i['message'])}</li>" for i in r['quality_issues'])
    issues=issues or '<li>No structural input issues detected. This does not establish provider accuracy.</li>'
    limited=''.join(f'<li>{h(t)}</li>' for t in r['limitations'])
    width=min(100,100*r['annualized_volatility']/0.4) if r['annualized_volatility'] is not None else 0
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEXUS risk brief · {h(r['as_of'])}</title>
<style>
:root{{color-scheme:light;--ink:#173c58;--muted:#52697b;--line:#d5e1e9;--state:{color}}}
*{{box-sizing:border-box}}body{{margin:0;background:#f4f8fc;color:var(--ink);font:16px/1.55 "Segoe UI",system-ui,sans-serif;font-variant-numeric:tabular-nums}}
main{{max-width:1120px;margin:auto;padding:36px 28px 60px}}header{{display:flex;justify-content:space-between;gap:16px;align-items:end;border-bottom:1px solid var(--line);padding-bottom:20px}}
.brand{{font-size:15px;font-weight:650}}h1{{font-size:clamp(26px,4vw,40px);letter-spacing:-.04em;margin:4px 0}}h2{{font-size:18px;margin:0 0 18px}}
.muted,.small{{color:var(--muted)}}.small{{font-size:13px}}.mode{{padding:10px 14px;background:#e4edf6;font-size:13px;margin:20px 0}}
.hero{{display:grid;grid-template-columns:1.2fr 1fr;gap:30px;padding:26px 0}}.level{{display:inline-block;color:var(--state);border:1px solid currentColor;padding:4px 12px;font-size:13px;font-weight:700;letter-spacing:.08em}}
.reason{{font-size:22px;line-height:1.4;max-width:600px}}.action{{padding:18px;border-left:3px solid var(--state);background:white}}.action strong{{display:block;margin-bottom:8px}}
.metrics{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.metric{{padding:20px;background:white;border:1px solid var(--line)}}.number{{font-size:36px;font-weight:650;letter-spacing:-.04em;display:block}}
.track{{height:6px;background:#dbe5ef;margin-top:18px}}.fill{{height:100%;width:{width:.2f}%;background:var(--state)}}
section{{border-top:1px solid var(--line);padding:25px 0}}.table-wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px;text-align:left}}th{{color:var(--muted);font-weight:500}}th,td{{padding:12px;border-bottom:1px solid var(--line);vertical-align:top}}td:last-child{{max-width:420px;overflow-wrap:anywhere}}
.columns{{display:grid;grid-template-columns:1fr 1fr;gap:30px}}ul{{padding-left:20px}}li{{margin-bottom:10px}}dl{{display:grid;grid-template-columns:130px 1fr;font-size:13px;gap:8px}}dt{{color:var(--muted)}}dd{{margin:0;overflow-wrap:anywhere}}footer{{font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:18px;overflow-wrap:anywhere}}a{{color:var(--ink)}}
@media(max-width:720px){{main{{padding:22px 16px}}header,.hero,.columns{{display:block}}.hero>div{{margin-bottom:20px}}.number{{font-size:28px}}th,td{{padding:8px}}}}
@media print{{body{{background:white;font-size:12px}}main{{padding:0}}.mode,.action,.metric{{break-inside:avoid}}a{{text-decoration:none}}}}
</style></head><body><main>
<header><div><div class="brand">Nexus Risk Research</div><h1>Daily risk brief</h1><div class="muted">NIFTY 50 TRI · Market-index risk</div></div>
<div class="muted">As of {h(r['as_of'])}<br>Next session {h(r['target_session'] or 'not verified')}</div></header>
<div class="mode">{h(mode_note)}</div>
<div class="hero"><div><span class="level">{h(state.replace('_',' '))}</span><p class="reason">{h(r['reason'])}</p>
<div class="action"><strong>{'Resolve before use' if operational else 'Review before the next open'}</strong>{h(r['review_action'])}</div></div>
<div><div class="metrics"><div class="metric"><span class="small">Next-session vol, annualized</span><span class="number">{h(pct(r['annualized_volatility']))}</span></div>
<div class="metric"><span class="small">Next-session vol, daily</span><span class="number">{h(pct(r['daily_volatility']))}</span></div></div>
<div class="track" aria-hidden="true"><div class="fill"></div></div><p class="small">Annualized scale: 0–40%. Elevated {h(pct(r['thresholds']['elevated']))} · Critical {h(pct(r['thresholds']['critical']))}.<br>
Previous issued level: {h(r['previous_level'] or 'No earlier report')}. Thresholds are fixed development estimates.</p></div></div>
<section><h2>Model comparison</h2><p class="small">Only {h(r['alert_model'])} sets the alert. Comparison models never replace a failed alert model.</p>
<div class="table-wrap"><table><thead><tr><th>Model</th><th>Annualized volatility</th><th>Fit</th><th>Diagnostics</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section class="columns"><div><h2>Large-move estimates</h2><p class="small">{h(r['probability_method'])}. A move can be positive or negative.</p>
<table><thead><tr><th>Absolute daily log return</th><th>Estimated probability</th></tr></thead><tbody>
<tr><td>Above {h(pct(r['thresholds']['event_elevated']))}</td><td>{h(pct(r['probability_elevated']))}</td></tr>
<tr><td>Above {h(pct(r['thresholds']['event_critical']))}</td><td>{h(pct(r['probability_critical']))}</td></tr></tbody></table></div>
<div><h2>Data checks</h2><ul>{issues}</ul><dl><dt>Last input session</dt><dd>{h(r['source_metadata'].get('last_return_date','Unavailable'))}</dd>
<dt>Official identity</dt><dd>{'Importer confirmed' if r['source_confirmed'] else 'Not independently confirmed'}</dd>
<dt>Retrieved</dt><dd>{h(r['retrieved_at'] or 'Unknown; import time is not retrieval time')}</dd><dt>Imported</dt><dd>{h(r['imported_at'])}</dd></dl></div></section>
<section><h2>Scope and interpretation</h2><ul class="small">{limited}</ul></section>
<footer>Run {h(r['run_id'])}<br>Source {h(r['source_name'])} · SHA-256 {h(r['source_sha256'] or 'Unavailable')}<br>
<a href="report.json">Report JSON</a> · <a href="report.md">Markdown version</a> · Print this page for a portable copy.</footer>
</main></body></html>'''
