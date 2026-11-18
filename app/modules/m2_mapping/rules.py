from app.normalize import instant,number
from app.errors import DomainError
from app.catalog import catalog_at,known_owners,switch_time
WARD={'W1':'一病区','一病区':'一病区','W2':'二病区','二病区':'二病区'}
def normalize(row,switch=None):
    out=dict(row);ward=WARD.get(row['ward'])
    out['time']=instant(row['time'])
    if switch is None: switch=switch_time()
    owner=catalog_at(out['time'],switch).get(row['bed'])
    if ward is None or owner is None or ward not in known_owners(row['bed']): raise DomainError('UNMAPPED','床号与病区不匹配')
    out['ward']=ward  # 保留回执签发字样,不改写身份
    out['resolved']=owner  # 入住时刻床位目录归属
    if owner!=ward: out['drift']='回执字样与入住时目录不符'
    version=number(row['version'])
    if version<1 or version!=version.to_integral(): raise DomainError('RANGE','版本无效')
    out['version']=int(version)
    if out['type'] not in ('admit','transfer','discharge'): raise DomainError('STATE','未知事件类型')
    return out
