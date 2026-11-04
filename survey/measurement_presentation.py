"""Shared wording for measurement dialogs, tooltips and exported details."""

from html import escape


def measurement_cards(result, tr):
    text = lambda key, **kw: tr("measurement_" + key, **kw)
    collection_detail = text("collection_metrics", completed=result.completed, total=result.total, samples=result.fresh_samples) if result.total is not None else text("note_unknown_capture")
    stability_detail = text("range", spread=f"{result.spread_db:g}") if result.spread_db is not None else text("note_few_samples")
    coverage_detail = text("coverage_reference", reference=f"{result.reference_dbm:g}")
    if result.missing_ssids:
        coverage_detail = text("missing", ssids=", ".join(result.missing_ssids)) + " " + coverage_detail
    elif result.weak_ssids:
        coverage_detail = text("weak", ssids=", ".join(result.weak_ssids)) + ". " + coverage_detail
    elif result.coverage == "unknown":
        coverage_detail = text("note_choose_scope")
    return [
        dict(key="collection", title=text("collection"), value=text("collection_" + result.collection), detail=collection_detail,
             tone="good" if result.collection == "verified" else "danger" if result.collection == "invalid" else "warning"),
        dict(key="stability", title=text("stability"), value=text("stability_" + result.stability), detail=stability_detail,
             tone="good" if result.stability == "stable" else "warning" if result.stability == "variable" else "muted"),
        dict(key="coverage", title=text("coverage"), value=text("coverage_" + result.coverage), detail=coverage_detail,
             tone="good" if result.coverage == "within" and result.collection == "verified" else "warning" if result.coverage != "unknown" else "muted"),
    ]


def measurement_text(result, tr):
    return "\n".join(card["title"] + ": " + card["value"] for card in measurement_cards(result, tr))


def measurement_html(result, tr):
    cards = measurement_cards(result, tr)
    return "<section><h3>" + escape(tr("measurement_details")) + "</h3>" + "".join(
        "<p><b>" + escape(card["title"]) + ": " + escape(card["value"]) + "</b><br>" + escape(card["detail"]) + "</p>"
        for card in cards) + "<p>" + escape(tr("measurement_review_hint")) + "</p></section>"
