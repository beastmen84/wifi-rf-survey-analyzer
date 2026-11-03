"""Escaped, localized presentation of one immutable analysis snapshot."""

from html import escape
from translations.i18n import translate


def wording(finding, report, language):
    values = dict(ssid=finding.ssid, ap=report.ap_labels.get(finding.group_ids[0], finding.group_ids[0])
                  if finding.group_ids else "", **finding.metrics)
    return translate(language, "advisor_rule_" + finding.rule, **values)


def finding_html(finding, report, language, interactive=False):
    tr = lambda key, **kwargs: translate(language, "advisor_" + key, **kwargs)
    safe = lambda text: escape(str(text))
    title = wording(finding, report, language)
    body = [f"<h2>{safe(title)}</h2>",
        f"<p>{safe(tr(finding.severity))} · {safe(tr('confidence'))}: {safe(tr(finding.confidence))}",
        f"{' · ' + safe(finding.band) + ' GHz' if finding.band else ''}</p>",
        f"<h3>{safe(tr('action'))}</h3><p>{safe(tr('action_' + finding.action))}</p>",
        f"<h3>{safe(tr('evidence'))}</h3><table width='100%' cellspacing='0' cellpadding='5'>"]
    for metric, value in finding.metrics.items():
        if metric == "neighbor_ids":
            continue
        if isinstance(value, float):
            value = f"{value:.1f}"
        body.append(f"<tr><td>{safe(tr('metric_' + metric))}</td><td><b>{safe(value)}</b></td></tr>")
    body.append("</table>")
    if finding.point_ids:
        body.append("<p>")
        index = {p.point_id: i + 1 for i, p in enumerate(report.points)}
        for point_id in finding.point_ids:
            label = f"{tr('point')} {index.get(point_id, '?')}"
            body.append(f"<a href='point:{index[point_id] - 1}'>{safe(label)}</a> · "
                        if interactive and point_id in index else safe(label) + " · ")
        body.append("</p>")
        refs = set(finding.point_ids)
        groups = set(finding.group_ids) | set(finding.metrics.get("neighbor_ids", ()))
        readings = {}
        for row in report.readings:
            if (row.point_id not in refs or (finding.band and row.band != finding.band
                    and not (finding.rule == "channel_evidence" and not row.band))
                    or (finding.ssid and row.ssid != finding.ssid and finding.rule != "missing_network")
                    or (groups and row.group_id not in groups)):
                continue
            key = (row.point_id, row.group_id, row.band)
            if key not in readings or row.signal_dbm > readings[key].signal_dbm:
                readings[key] = row
        body.append("<table width='100%' cellspacing='0' cellpadding='5'><thead><tr>"
            f"<th>{safe(tr('point'))}<br>x/y (px)</th><th>{safe(tr('ap'))} / SSID</th>"
            f"<th>dBm</th><th>CH / MHz</th><th>{safe(tr('confidence'))}</th></tr></thead><tbody>")
        by_id = {p.point_id: p for p in report.points}
        for key in sorted(readings):
            r = readings[key]
            p = by_id[r.point_id]
            body.append(f"<tr><td>{index[r.point_id]}<br>({p.x:g}, {p.y:g})</td>"
                f"<td>{safe(report.ap_labels.get(r.group_id, r.group_id))}<br>{safe(r.ssid)} · {safe(r.band or '?')} GHz</td>"
                f"<td>{r.signal_dbm:g}</td><td>{r.channel if r.channel is not None else '-'} / "
                f"{r.width if r.width is not None else '-'}</td><td>{r.confidence:.0%}</td></tr>")
        body.append("</tbody></table>")
    if finding.limitations:
        body.append(f"<h3>{safe(tr('limits'))}</h3><ul>" + "".join(
            f"<li>{safe(tr(limit))}</li>" for limit in finding.limitations) + "</ul>")
    body.append(f"<h3>{safe(tr('check'))}</h3><p>{safe(tr('check_text'))}</p>")
    html = "".join(body)
    # Leave room for QTextBrowser's document margins at native Windows DPI.
    return html.replace("width='100%'", "width='98%'") if interactive else html


def report_html(report, language="en", overview_data="", palette=None):
    tr = lambda key, **kwargs: translate(language, "advisor_" + key, **kwargs)
    safe = lambda text: escape(str(text))
    palette = palette or dict(text="#25313D", panel="#FFFFFF", border="#D5DEE8", title="#1F2A36")
    channels = lambda band: ", ".join(map(str, report.profile.channels(band))) or tr("review_only")
    body = [f"<h1>{safe(tr('title'))}</h1><p><b>{safe(report.survey_name)}</b></p>",
        f"<p>{safe(tr('hint'))}</p><p>{safe(tr('summary', points=len(report.points), findings=len(report.findings), actions=sum(f.rule == 'channel_change' for f in report.findings)))}</p>",
        f"<p>{safe(tr('target'))}: {report.profile.coverage_dbm:g} dBm · "
        f"{safe(tr('min_confidence'))}: {report.profile.minimum_confidence:.0%} · "
        f"{safe(tr('minimum'))}: {report.profile.minimum_points}</p>",
        "<p>SSID: " + safe(", ".join(report.relevant_ssids)) + "</p>",
        f"<p>{safe(tr('policy'))}: 2.4 GHz {safe(channels('2.4'))}; "
        f"5 GHz {safe(channels('5'))}; 6 GHz {safe(channels('6'))}</p>"]
    changes = [f for f in report.findings if f.rule == "channel_change"]
    if changes:
        body.append(f"<h2>{safe(tr('action'))}</h2><ul>" + "".join(
            f"<li>{safe(wording(f, report, language))} ({safe(f.band)} GHz)</li>" for f in changes) + "</ul>")
    if overview_data:
        body.append(f"<p style='line-height:100%'><img src='{overview_data}'></p>")
    if not report.findings:
        body.append(f"<p>{safe(tr('clear'))}</p>")
    for finding in report.findings:
        body.append(finding_html(finding, report, language))
        body.append("<hr>")
    body.extend((f"<h2>{safe(tr('limits'))}</h2><p>{safe(tr('general_limit'))}</p>",
        f"<p>{safe(tr('method', version=report.engine_version, fingerprint=report.fingerprint[:16], created=report.created_at))}</p>"))
    return wrap_html("".join(body), palette)


def wrap_html(body, palette=None):
    p = palette or dict(text="#25313D", panel="#FFFFFF", border="#D5DEE8", title="#1F2A36")
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
        f"body {{font-family:'Segoe UI',sans-serif;font-size:10pt;color:{p['text']};background:{p['panel']};}}"
        f"h1,h2,h3 {{color:{p['title']};}} h1{{font-size:22pt}} h2{{font-size:15pt;margin-top:22px}}"
        "h3{font-size:11pt;margin-top:14px} p{line-height:1.35} table{border-collapse:collapse}"
        f"td,th{{border-bottom:1px solid {p['border']};text-align:left;vertical-align:top}}"
        "a{color:#3A6EA5} img{max-width:100%} hr{margin:20px 0}</style></head><body>" + body + "</body></html>")
