"""Browser presentation of the same immutable RF findings used by the app."""

from advisor.presentation import finding_html
from advisor.recommendations import sections, recommendation_kind, empty_recommendation_key
from exporting.html_report import document, disclosure, kpi, safe
from translations.i18n import translate
from survey.measurement_presentation import measurement_html


def browser_report(report, language, overview_data=""):
    tr = lambda key, **kw: translate(language, "advisor_" + key, **kw)
    label = lambda key, **kw: translate(language, "report_" + key, **kw)
    grouped = sections(report)
    data, actions, reviews = grouped.prerequisites, grouped.recommendations, grouped.observations
    body = ['<nav>']
    for identity, title in (("overview", label("overview")), ("actions", tr("recommendations")),
                            ("prerequisites", tr("prerequisites")), ("reviews", tr("observations")),
                            ("map", label("map")), ("parameters", label("parameters"))):
        if identity != "map" or overview_data:
            body.append(f'<a href="#{identity}">{safe(title)}</a>')
    body.append('</nav><section id="overview"><div class="kpis">')
    body.extend((kpi(tr("recommendations"), len(actions)), kpi(tr("prerequisites"), len(data)),
        kpi(tr("observations"), len(reviews)), kpi(label("measured_points"), len(report.points))))
    body.append('</div>')
    body.append(f'<p class="muted">{safe(tr("target"))}: <b>{report.profile.coverage_dbm:g} dBm</b> · '
        f'SSID: {safe(", ".join(report.relevant_ssids))}</p>')
    if data:
        body.append(f'<div class="callout"><strong>{safe(tr("prerequisites"))}</strong>'
            f'<p>{safe(tr("quality_summary", checks=len(data), points=grouped.affected_points))}</p>'
            f'<a href="#prerequisites">{safe(tr("show_prerequisites"))}</a></div>')
    else:
        body.append(f'<p class="muted">{safe(tr("quality_ready"))}</p>')
    if not report.findings:
        body.append(f'<p class="panel">{safe(label("no_issues"))}</p>')
    body.append('</section><section id="actions">' + f'<h2>{safe(tr("recommendations"))}</h2>'
                f'<p class="muted">{safe(tr("order_hint"))}</p>')
    if not actions:
        body.append(f'<p class="panel">{safe(tr(empty_recommendation_key(grouped)))}</p>')
    for rank, finding in enumerate(actions, 1):
        body.append(card(finding, report, language, "action", rank))
    body.append('</section>')
    if overview_data:
        body.append(f'<section id="map"><h2>{safe(label("map"))}</h2><div class="map-frame">'
                    f'<img src="{safe(overview_data)}" alt="{safe(label("map"))}"></div></section>')
    body.append(f'<section id="prerequisites"><h2>{safe(tr("prerequisites"))}</h2>'
                f'<p class="muted">{safe(tr("quality_export"))}</p>')
    body.append(disclosure(tr("prerequisites") + f" ({len(data)})",
        ''.join(card(f, report, language, "data") for f in data) or safe(tr("section_empty")), "prerequisite-details"))
    body.append('</section><section id="reviews">' + f'<h2>{safe(tr("observations"))}</h2>')
    body.append(disclosure(tr("observations") + f" ({len(reviews)})",
        ''.join(card(f, report, language, "review") for f in reviews) or safe(tr("section_empty")), "observation-details"))
    body.append('</section>')
    channels = lambda band: ", ".join(map(str, report.profile.channels(band))) or tr("review_only")
    if report.measurements:
        full_tr = lambda key, **kw: translate(language, key, **kw)
        details = []
        for index, point in enumerate(report.points, 1):
            result = report.measurements.get(point.point_id)
            if result:
                details.append(disclosure(f"{tr('point')} {index} · ({point.x:g}, {point.y:g}) px",
                    measurement_html(result, full_tr), "measurement-" + str(index)))
        body.append(disclosure(full_tr("measurement_details"), "".join(details), "measurement-quality"))
    parameters = (f'<p><b>{safe(tr("target"))}:</b> {report.profile.coverage_dbm:g} dBm</p>'
        f'<p>{safe(tr("min_confidence"))}: {report.profile.minimum_confidence:.0%} · '
        f'{safe(tr("minimum"))}: {report.profile.minimum_points}</p>'
        f'<p>SSID: {safe(", ".join(report.relevant_ssids))}</p>'
        + "".join(f'<p><b>{band} GHz:</b> {safe(channels(band))}</p>' for band in ("2.4", "5", "6"))
        + f'<p>{safe(tr("method", version=report.engine_version, fingerprint=report.fingerprint[:16], created=report.created_at))}</p>')
    body.append(disclosure(label("parameters"), parameters, "parameters"))
    body.append(f'<section class="panel"><h2>{safe(tr("limits"))}</h2><p>{safe(tr("general_limit"))}</p></section>')
    return document(tr("title"), "".join(body), language, report.survey_name)


def card(finding, report, language, kind, rank=None):
    confidence = translate(language, "advisor_confidence") + ": " + translate(language, "advisor_" + finding.confidence)
    badges = [confidence]
    if rank is not None:
        badges.insert(0, translate(language, "advisor_rank", number=rank))
        badges.append(translate(language, "advisor_" + recommendation_kind(finding)))
    return (f'<article class="card {kind}" id="finding-{finding.finding_id}">'
        + '<div class="badges">' + ''.join(f'<span class="badge">{safe(badge)}</span>' for badge in badges) + '</div>'
        + finding_html(finding, report, language, browser=True, compact=True) + '</article>')
