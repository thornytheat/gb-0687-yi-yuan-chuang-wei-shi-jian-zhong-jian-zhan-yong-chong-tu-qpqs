import pytest
from app.config import SAMPLES
from app.pipeline import run
from app.normalize import instant
from app.errors import DomainError
from app.catalog import catalog_at,known_owners
from app.modules.m2_mapping.rules import normalize
SWITCH=instant('2026-11-16T12:00:00+08:00')
@pytest.fixture
def merged(): return (SAMPLES/"merge.csv").read_bytes()
def row(**kw):
    x=dict(id='T1',patient='P1',bed='101',ward='W2',time='2026-11-16T13:00:00+08:00',type='transfer',version='1');x.update(kw);return x

def test_catalog_versions():
    assert catalog_at(instant('2026-11-16T11:59:59+08:00'),SWITCH)['101']=='二病区'
    assert catalog_at(SWITCH,SWITCH)['101']=='一病区'
    assert catalog_at(SWITCH,SWITCH)['102']=='二病区'

def test_known_owners():
    assert known_owners('101')=={'一病区','二病区'} and known_owners('001')=={'一病区'}

def test_stale_receipt_keeps_identity():
    item=normalize(row())
    assert item['ward']=='二病区' and item['resolved']=='一病区' and item['drift']

def test_never_owned_ward_unmapped():
    with pytest.raises(DomainError): normalize(row(bed='001'))

def test_unknown_bed_unmapped():
    with pytest.raises(DomainError): normalize(row(bed='999'))

def test_receipt_identity_preserved(merged):
    kept=[x for x in run(merged,persist=False)['records'] if x['id']=='M002']
    assert len(kept)==1 and kept[0]['ward']=='二病区' and kept[0]['resolved']=='一病区'

def test_occupancy_lands_on_current_bed(merged):
    seg=[x for x in run(merged,persist=False)['intervals'] if x['source']=='M002']
    assert len(seg)==1 and seg[0]['bed']=='101' and seg[0]['ward']=='一病区' and seg[0]['stated']=='二病区' and seg[0]['open'] is True

def test_retry_adds_no_event(merged):
    result=run(merged,persist=False)
    assert sum(1 for x in result['records'] if x['id']=='M002')==1
    assert any(q['key']=='M002' and q['code']=='DUPLICATE' for q in result['quarantine'])
    reg={x['receipt']:x for x in result['receipts']}
    assert reg['M002']['copies']==2 and reg['M002']['added']==1

def test_failed_switch_keeps_previous_trajectory(merged):
    result=run(merged,persist=False)
    assert any(q['key']=='M009' and q['code']=='ORPHAN' for q in result['quarantine'])
    assert all(x['source']!='M009' and x['patient']!='P1005' for x in result['intervals'])
    reg={x['receipt']:x for x in result['receipts']}
    assert reg['M009']['added']==0 and reg['M009']['check']=='ORPHAN' and '上一版' in reg['M009']['state']

def test_register_shows_current_ownership(merged):
    result=run(merged,persist=False)
    reg={x['receipt']:x for x in result['receipts']}
    assert reg['M002']['owner_now']=='一病区' and reg['M002']['adopted']=='M002/v1' and reg['M002']['check']=='通过'
    board={x['bed']:x for x in result['ownership']}
    assert board['101']=={'bed':'101','ward':'一病区','switched':True}
    assert board['102']=={'bed':'102','ward':'二病区','switched':False}

def test_merge_reconcile_balanced(merged):
    result=run(merged,persist=False)
    assert all(x['state']=='通过' for x in result['reconciliation'])
    assert result['input_count']==len(result['records'])+len(result['quarantine'])

def test_merge_pages(client,merged):
    reply=client.post('/api/runs',json={'text':merged.decode()})
    assert reply.status_code==200
    page=client.get('/m/7',query_string={'run':reply.json['manifest']['run_id']})
    html=page.get_data(as_text=True)
    assert '床位当前归属' in html and '采用的回执' in html and '校验结果' in html and 'M002' in html
