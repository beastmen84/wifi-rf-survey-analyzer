"""Browser presentation of the same immutable RF findings used by the app."""

from advisor.presentation import finding_html, wording
from exporting.html_report import document, disclosure, kpi, safe
from translations.i18n import translate


def browser_report(report, language, overview_data=""):
    tr = lambda key, **kw: translate(language, "advisor_" + key, **kw)
    label = lambda key, **kw: translate(language, "report_" + key, **kw)
    data = [f for f in report.findings if f.category == "data"]
    actions = [f for f in report.findings if f.rule == "channel_change" or f.action == "power_trial"]
    reviews = [f for f in report.findings if f not in data and f not in actions]
    body = ['<nav>']
    for identity, key in (("overview", "overview"), ("actions", "actions"), ("map", "map"),
                          ("reviews", "reviews"), ("parameters", "parameters")):
        if identity != "map" or overview_data:
            body.append(f'<a href="#{identity}">{safe(label(key))}</a>')
    body.append('</nav><section id="overview"><div class="kpis">')
    body.extend((kpi(label("measured_points"), len(report.points)), kpi(label("actions"), len(actions)),
        kpi(label("data_checks"), len(data)), kpi(label("reviews"), len(reviews))))
    body.append('</div>')
    body.append(f'<p class="muted">{safe(tr("target"))}: <b>{report.profile.coverage_dbm:g} dBm</b> · '
        f'SSID: {safe(", ".join(report.relevant_ssids))}</p>')
    if data:
        body.append(f'<div class="callout"><strong>{safe(label("data_first"))}</strong><p>{safe(label("data_warning"))}</p><ul>')
        for finding in data:
            body.append(f'<li><a href="#finding-{finding.finding_id}">{safe(wording(finding, report, language))}</a></li>')
        body.append('</ul></div>')
    if not report.findings:
        body.append(f'<p class="panel">{safe(label("no_issues"))}</p>')
    body.append('</section><section id="actions">' + f'<h2>{safe(label("actions"))}</h2>')
    if not actions:
        body.append(f'<p class="panel">{safe(label("no_actions"))}</p>')
    for finding in actions:
        body.append(card(finding, report, language, "action"))
    body.append('</section>')
    if overview_data:
        body.append(f'<section id="map"><h2>{safe(label("map"))}</h2><div class="map-frame">'
                    f'<img src="{safe(overview_data)}" alt="{safe(label("map"))}"></div></section>')
    body.append(f'<section id="reviews"><h2>{safe(label("reviews"))}</h2>')
    # Quality/model constraints remain readable without opening evidence tables.
    for finding in data + reviews:
        body.append(card(finding, report, language, "data" if finding.category == "data" else "review"))
    body.append('</section>')
    channels = lambda band: ", ".join(map(str, report.profile.channels(band))) or tr("review_only")
    parameters = (f'<p><b>{safe(tr("target"))}:</b> {report.profile.coverage_dbm:g} dBm</p>'
        f'<p>{safe(tr("min_confidence"))}: {report.profile.minimum_confidence:.0%} · '
        f'{safe(tr("minimum"))}: {report.profile.minimum_points}</p>'
        f'<p>SSID: {safe(", ".join(report.relevant_ssids))}</p>'
        + "".join(f'<p><b>{band} GHz:</b> {safe(channels(band))}</p>' for band in ("2.4", "5", "6"))
        + f'<p>{safe(tr("method", version=report.engine_version, fingerprint=report.fingerprint[:16], created=report.created_at))}</p>')
    body.append(disclosure(label("parameters"), parameters, "parameters"))
    body.append(f'<section class="panel"><h2>{safe(tr("limits"))}</h2><p>{safe(tr("general_limit"))}</p></section>')
    return document(tr("title"), "".join(body), language, report.survey_name)


def card(finding, report, language, kind):
    confidence = translate(language, "advisor_confidence") + ": " + translate(language, "advisor_" + finding.confidence)
    return (f'<article class="card {kind}" id="finding-{finding.finding_id}">'
        f'<span class="badge">{safe(confidence)}</span>'
        + finding_html(finding, report, language, browser=True) + '</article>')
