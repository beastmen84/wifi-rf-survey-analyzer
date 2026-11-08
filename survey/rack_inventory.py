"""Optional rack inventory, independent of plan geometry and RF analysis."""
from copy import deepcopy

MAX_SWITCHES = 32
MAX_SWITCH_PORTS = 512
MAX_RACK_PORTS = 4096
MAX_DOCUMENT_SWITCHES = 512
MAX_DOCUMENT_PORTS = 16384
MAX_DOCUMENT_TEXT = 1_000_000


def validate_rack(value):
    if not isinstance(value,dict) or not set(value) <= {'name','switches'}:
        raise ValueError('Invalid rack inventory')
    name, switches = value.get('name',''), value.get('switches',[])
    if not isinstance(name,str) or len(name)>80 or any(ord(c)<32 for c in name):
        raise ValueError('Invalid rack name')
    if not isinstance(switches,list) or len(switches)>MAX_SWITCHES:
        raise ValueError('Invalid rack switch count')
    result, total = [], 0
    for switch in switches:
        if not isinstance(switch,dict) or set(switch)!={'ports'} or not isinstance(switch['ports'],list):
            raise ValueError('Invalid switch inventory')
        ports=switch['ports']
        if len(ports)>MAX_SWITCH_PORTS or any(not isinstance(v,str) or len(v)>2000 or '\0' in v for v in ports):
            raise ValueError('Invalid switch ports')
        total+=len(ports)
        result.append(dict(ports=list(ports)))
    if total>MAX_RACK_PORTS:
        raise ValueError('rack_inventory_limit')
    result=dict(switches=result)
    if name.strip():
        result['name']=name.strip()
    return result if switches or name.strip() else {}


def resize_switches(value,count):
    if type(count) is not int or not 0<=count<=MAX_SWITCHES:
        raise ValueError('Invalid rack switch count')
    value=deepcopy(value)
    value['switches']=value.get('switches',[])[:count]
    value['switches'].extend(dict(ports=[]) for _ in range(count-len(value['switches'])))
    return value


def validate_inventory_totals(items):
    switches=ports=text=0
    for item in items:
        rack=item.get('rack',{})
        text+=len(rack.get('name',''))
        for switch in rack.get('switches',[]):
            switches+=1
            ports+=len(switch['ports'])
            text+=sum(len(v) for v in switch['ports'])
    if switches>MAX_DOCUMENT_SWITCHES or ports>MAX_DOCUMENT_PORTS or text>MAX_DOCUMENT_TEXT:
        raise ValueError('rack_document_limit')


def rack_label(entry,tr):
    return entry.get('rack_name') or tr('rack_reference').format(number=entry.get('rack_index',1))


def table_title(entry,tr):
    return tr('rack_switch_title').format(rack=rack_label(entry,tr),number=entry['switch']+1)


def inventory_tables(document,visible_only=True):
    """Port numbers are derived; only descriptions are stored with the symbol."""
    result=[]
    # Include hidden racks in ordinal allocation so visibility changes do not
    # relabel the remaining racks. Names are preferable for enduring references.
    for ordinal,(layer,item) in enumerate(rack_records(document),1):
        if visible_only and not layer['visible']:
            continue
        rack=item.get('rack',{})
        for index,switch in enumerate(rack.get('switches',[])):
            result.append(dict(kind='rack_ports',rack_index=ordinal,rack_name=rack.get('name',''),switch=index,
                layer=layer['id'],layer_name=layer['name'],id=item['id'],
                rows=[dict(number=p+1,port=p,switch=index,id=item['id'],layer=layer['id'],
                           description=description,ap='') for p,description in enumerate(switch['ports'])]))
    return result


def rack_records(document):
    return sorted([(layer,item) for layer in document['layers'] for item in layer['drawing']['annotations']
                   if item['kind']=='symbol' and item['variant']=='rack'],key=lambda r:(r[0]['id'],r[1]['id']))
