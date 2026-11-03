"""Human-readable companion to the complete machine-readable quality report."""


def quality_markdown(report: dict) -> str:
    lines = ["# NEXUS Sprint 1A data quality", "", f"Run: `{report['run_id']}`", "",
             f"Requested interval (inclusive): {report['start']} through {report['end']}", "",
             "| Asset | Currency | Source | First | Last | Observations | Missing/invalid prices | Extreme returns | Status |",
             "|---|---|---|---|---|---:|---:|---:|---|"]
    for item in report["assets"]:
        values = [item["asset_name"], item["currency"], item["source"], item.get("earliest"), item.get("latest"),
                  item.get("observation_count"), item.get("invalid_price_count", item.get("missing_or_invalid_price_count")),
                  item.get("extreme_return_count"), item["status"]]
        lines.append("| " + " | ".join(str(v) if v is not None else "n/a" for v in values) + " |")
    lines.extend(["", "Warning observations are retained. Assets with errors are not published as processed datasets.",
                  "Weekday gaps include holidays and are not proof of missing exchange sessions.",
                  "See data_quality.json for all flagged dates and manifest.json for provenance and configuration."])
    for item in report["assets"]:
        lines.extend(["", f"## {item['asset']}", ""])
        if not item.get("issues"):
            lines.append("No automatic quality flags.")
        for notice in item.get("issues", []):
            count = f" (count: {notice['count']})" if "count" in notice else ""
            filename = f" [{notice['source_file']}]" if "source_file" in notice else ""
            lines.append(f"- **{notice['severity']} / {notice['code']}**{count}{filename}: {notice['message']}")
            observations = notice.get("observations", [])
            if observations:
                lines.extend(["", "| Date | Row | Daily return |", "|---|---:|---:|"])
                for observation in observations[:20]:
                    change = observation.get("simple_return")
                    change_text = f"{change:.4%}" if change is not None else "n/a"
                    lines.append(f"| {observation.get('date') or 'invalid date'} | {observation['row']} | {change_text} |")
                if len(observations) > 20:
                    lines.append("\nFirst 20 shown; all observations are in data_quality.json.")
                lines.append("")
            for gap in notice.get("gaps", [])[:20]:
                lines.append(f"  - Gap: {gap['previous_date']} to {gap['date']} ({gap['calendar_days']} calendar days).")
            for stale in notice.get("runs", [])[:20]:
                lines.append(f"  - Unchanged price: {stale['start']} to {stale['end']}, {stale['observations']} observations at {stale['price']:.8g}.")
        if item.get("processed"):
            lines.append(f"- Processed snapshot: `{item['processed']['path']}`")
    return "\n".join(lines) + "\n"
