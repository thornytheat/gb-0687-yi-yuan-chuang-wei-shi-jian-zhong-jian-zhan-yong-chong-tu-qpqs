from app.errors import DomainError
from app.catalog import catalog_at
from decimal import Decimal as D
from datetime import timedelta
from collections import defaultdict
import hashlib,json
from app.normalize import serial
def late_arrivals(rows,late_minutes):
    """按文件行序推进水位,事件时刻早于水位阈值即判迟到"""
    threshold=timedelta(minutes=float(late_minutes));watermark=None;late=[]
    for row in sorted(rows,key=lambda r:r['_line']):
        if watermark is not None and row['time']<watermark-threshold:
            late.append((row,D(str((watermark-row['time']).total_seconds()))/60))
        watermark=max(watermark,row['time']) if watermark else row['time']
    return late,watermark
def replay_audit(rows,bad,total,late_minutes):
    if len(rows)+len(bad)!=total: raise DomainError('INCOMPLETE','事件行数不平衡')
    pairs,watermark=late_arrivals(rows,late_minutes)
    late=[{'id':row['id'],'patient':row['patient'],'time':row['time'],'late_minutes':minutes,'state':'已重算'} for row,minutes in pairs]
    return {'watermark':watermark,'late':late,'fingerprint':hashlib.sha256(json.dumps(serial(sorted(rows,key=lambda r:r['id'])),sort_keys=True).encode()).hexdigest()}
def receipt_register(inbox,retained,quarantine,late_minutes,switch,now):
    """迟到回执登记:保留回执身份,按入住时目录归属,重试不新增,失败保持上一版轨迹"""
    pairs,_=late_arrivals(inbox,late_minutes)
    arrivals=defaultdict(list)
    for row,_ in pairs: arrivals[row['id']].append(row)
    kept={row['id']:row for row in retained}
    failed=defaultdict(list)
    for q in quarantine: failed[q['key']].append(q)
    register=[]
    for rid in sorted(arrivals):
        rows=arrivals[rid];first=rows[0];adopted=kept.get(rid)
        owner=catalog_at(now,switch).get(first['bed'],'未登记')
        if adopted and adopted['_line'] in {row['_line'] for row in rows}:
            resolved=adopted.get('resolved',adopted['ward'])
            state='采信·按入住时目录归属' if resolved!=adopted['ward'] else '采信'
            if len(rows)>1: state+='·重试未新增'
            register.append({'receipt':rid,'patient':adopted['patient'],'bed':adopted['bed'],'time':adopted['time'],
                             'stated':adopted['ward'],'resolved':resolved,'owner_now':owner,'copies':len(rows),
                             'added':1,'adopted':f"{rid}/v{adopted['version']}",'check':'通过','state':state})
        elif adopted:
            register.append({'receipt':rid,'patient':adopted['patient'],'bed':adopted['bed'],'time':adopted['time'],
                             'stated':adopted['ward'],'resolved':adopted.get('resolved',adopted['ward']),'owner_now':owner,
                             'copies':len(rows),'added':0,'adopted':f"{rid}/v{adopted['version']}",'check':'通过','state':'重试未新增事件'})
        else:
            code=failed[rid][0]['code'] if failed.get(rid) else 'STATE'
            register.append({'receipt':rid,'patient':first['patient'],'bed':first['bed'],'time':first['time'],
                             'stated':first['ward'],'resolved':first.get('resolved','—'),'owner_now':owner,
                             'copies':len(rows),'added':0,'adopted':'—','check':code,'state':'切换失败·保持上一版轨迹'})
    return register
