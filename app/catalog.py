from app.normalize import instant
from app.config import DEFAULTS
BEDS={**{f'{i:03d}':'一病区' for i in range(1,5)},**{f'{i:03d}':'二病区' for i in range(101,105)}}
MERGE={'101':'一病区'}  # 病区合并:101床划归一病区
def switch_time(value=None):
    return instant(value if value is not None else DEFAULTS['catalog_switch'])
def catalog_at(moment,switch):
    """时刻moment生效的床位目录:合并后101床归属一病区"""
    beds=dict(BEDS)
    if moment>=switch: beds.update(MERGE)
    return beds
def known_owners(bed):
    """床号在任一目录版本下的归属集合,用于识别旧字样回执"""
    return {BEDS.get(bed),MERGE.get(bed)}-{None}
def versions(switch):
    return [{'version':'v1 合并前','effective':None,'beds':dict(BEDS)},
            {'version':'v2 合并后','effective':switch,'beds':catalog_at(switch,switch)}]
def ownership(moment,switch):
    current=catalog_at(moment,switch)
    return [{'bed':bed,'ward':current[bed],'switched':BEDS[bed]!=current[bed]} for bed in sorted(current)]
