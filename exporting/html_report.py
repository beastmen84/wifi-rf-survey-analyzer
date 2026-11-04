"""Common offline report layout. All dynamic text is escaped by its callers."""

from base64 import b64encode
from html import escape
from io import BytesIO

from translations.i18n import translate, normalize_language


def safe(value):
    return escape(str(value), quote=True)


def image_data(image):
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return "data:image/png;base64," + b64encode(buffer.getvalue()).decode("ascii")


def disclosure(label, body, identity=""):
    identity = f' id="{safe(identity)}"' if identity else ""
    return f'<details{identity}><summary>{safe(label)}</summary><div class="details-body">{body}</div></details>'


def kpi(label, value):
    return f'<div class="kpi"><strong>{safe(value)}</strong><span>{safe(label)}</span></div>'


def document(title, body, language="en", subtitle=""):
    tr = lambda key: translate(language, "report_" + key)
    return (f'<!DOCTYPE html><html lang="{normalize_language(language)}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &apos;none&apos;; '
        'img-src data:; style-src &apos;unsafe-inline&apos;; script-src &apos;unsafe-inline&apos;">'
        f'<title>{safe(title)}</title><style>{STYLE}</style></head><body><main>'
        '<header><div class="eyebrow">WI-FI RF SURVEY ANALYZER</div>'
        f'<h1>{safe(title)}</h1><p class="subtitle">{safe(subtitle)}</p>'
        f'<div class="tools"><button type="button" data-command="print">{safe(tr("print"))}</button>'
        f'<button type="button" data-command="expand">{safe(tr("expand"))}</button>'
        f'<button type="button" data-command="collapse">{safe(tr("collapse"))}</button></div></header>'
        + body + f'<footer>{safe(tr("offline"))}</footer></main><script>{SCRIPT}</script></body></html>')


STYLE = """
:root{color-scheme:light;--ink:#203246;--muted:#566578;--line:#dce4eb;--blue:#235f99}
*{box-sizing:border-box}body{margin:0;background:#eef3f7;color:var(--ink);font:16px/1.6 'Segoe UI',Arial,sans-serif}
main{max-width:1180px;margin:auto;padding:42px 30px}header{padding:0 0 24px;border-bottom:1px solid var(--line)}
.eyebrow{font-size:12px;font-weight:750;letter-spacing:.14em;color:var(--blue)}h1{font-size:clamp(27px,4vw,42px);line-height:1.15;margin:10px 0}
h2{font-size:23px;line-height:1.3;margin:0 0 14px}h3{font-size:18px;line-height:1.4;margin:14px 0 8px}
p{margin:9px 0}.subtitle,.muted{color:var(--muted)}.tools,nav,.badges{display:flex;gap:10px;flex-wrap:wrap}
h1,h2,h3,p,li{overflow-wrap:anywhere}
.tools{margin-top:18px}button,nav a{font:inherit;border:1px solid #bacbd9;border-radius:8px;padding:7px 13px;background:white;color:var(--blue);cursor:pointer;text-decoration:none}
button:hover,nav a:hover{background:#e7f0f8}a{color:var(--blue)}a:focus-visible,button:focus-visible,summary:focus-visible{outline:3px solid #2679c2;outline-offset:3px}
nav{margin:22px 0}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:24px 0}
.kpi{border:1px solid var(--line);border-radius:12px;padding:17px 20px;background:white}.kpi strong{display:block;font-size:30px;line-height:1.3}.kpi span{color:var(--muted);font-size:14px}
section{margin-top:30px}.card,.panel{background:white;border:1px solid var(--line);border-radius:12px;padding:22px;margin:14px 0}
.card{border-left:5px solid #8293a5}.card.action{border-left-color:#267d6b}.card.data,.callout{border-left-color:#b87716}
.callout{background:#fff5df;border:1px solid #e5c992;border-left-width:5px;border-radius:8px;padding:15px 19px;margin:18px 0}
.badge{display:inline-block;background:#edf2f6;border-radius:5px;padding:3px 9px;font-size:13px;font-weight:650}.action .badge{background:#e6f3ef;color:#256454}
.card h2{font-size:21px;margin-top:10px}.card h3{font-size:16px}.card>p:first-of-type{color:var(--muted)}
details{background:white;border:1px solid var(--line);border-radius:9px;margin:15px 0;scroll-margin-top:18px}summary{cursor:pointer;font-weight:650;padding:14px 17px;overflow-wrap:anywhere}
details[open]>summary{border-bottom:1px solid var(--line)}.details-body{padding:16px 18px;overflow:auto}.details-body>details{margin-top:0}
.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#f2f6f9;font-weight:650}
td:first-child{min-width:90px}td code,code{overflow-wrap:anywhere;font-size:12px}table p{margin:0}img{max-width:100%;height:auto;display:block;margin:auto}
.map-frame{background:white;border:1px solid var(--line);border-radius:12px;padding:16px}.map-frame svg{display:block;width:100%;height:auto;max-height:78vh}
.legend{display:flex;gap:12px 20px;flex-wrap:wrap;margin:15px 0}.swatch{display:inline-block;width:14px;height:14px;border:1px solid #576472;margin-right:7px;vertical-align:middle}
.gradient{height:18px;width:260px;max-width:100%;border-radius:3px}.scale-labels{display:flex;justify-content:space-between;width:260px;max-width:100%}
.point-link{font-weight:650}.map-point:hover{stroke:#235f99;stroke-width:4}.small{font-size:13px}.columns{display:grid;grid-template-columns:1fr 1fr;gap:20px}
footer{margin-top:35px;border-top:1px solid var(--line);padding-top:18px;font-size:13px;color:var(--muted)}section,article{scroll-margin-top:18px}article:target,details:target{outline:3px solid #70a2cf}
@media(max-width:650px){main{padding:24px 14px}.card,.panel{padding:16px}.columns{grid-template-columns:1fr}th,td{padding:8px}.kpis{gap:8px}.map-frame{padding:5px}}
@media print{body{background:white;font-size:10pt}main{max-width:none;padding:0}.tools,nav{display:none}.card,details{break-inside:auto;border-radius:0}.card,.panel{padding:12px;margin:10px 0}h2,h3,summary{break-after:avoid}.map-frame svg{max-height:160mm}.kpi{padding:10px}h1{font-size:25pt}a{color:inherit;text-decoration:none}.details-body{overflow:visible;padding:8px}table{font-size:9pt}th,td{padding:6px 8px}.table-scroll{overflow:visible}thead{display:table-header-group}tr{break-inside:avoid}}
"""

SCRIPT = """
let printState=null;
function revealHash(){
 const target=document.getElementById(decodeURIComponent(location.hash.slice(1)));
 if(!target)return;
 for(let node=target;node;node=node.parentElement)if(node.tagName==='DETAILS')node.open=true;
 requestAnimationFrame(()=>target.scrollIntoView({block:'start'}));
}
document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>{
 const command=button.dataset.command;
 if(command==='print'){window.print();return;}
 document.querySelectorAll('details').forEach(item=>item.open=command==='expand');
}));
window.addEventListener('hashchange',revealHash);
window.addEventListener('beforeprint',()=>{
 if(printState)return;
 printState=Array.from(document.querySelectorAll('details'),item=>[item,item.open]);
 printState.forEach(([item])=>item.open=true);
});
window.addEventListener('afterprint',()=>{if(printState){printState.forEach(([item,open])=>item.open=open);printState=null;}});
revealHash();
"""
