from .rules import replay_audit,receipt_register
from app.normalize import number
from app.catalog import ownership
def execute(ctx):
    late=number(ctx['params']['late_minutes'])
    ctx['audit']=replay_audit(ctx['records'],ctx['quarantine'],ctx['input_count'],late)
    inbox=ctx.pop('inbox',ctx['records']);switch=ctx['catalog_switch']
    ctx['receipts']=receipt_register(inbox,ctx['records'],ctx['quarantine'],late,switch,ctx['observation_end'])
    ctx['ownership']=ownership(ctx['observation_end'],switch)
    failed=sum(1 for x in ctx['receipts'] if x['added']==0)
    ctx['stages'].append({'title':'补传重算','rows':ctx['audit']['late'],'metrics':{'迟到事件':len(ctx['audit']['late']),'采信事件':len(ctx['records']),'迟到回执':len(ctx['receipts']),'切换失败':failed,'水位':str(ctx['audit']['watermark'])}})
    return ctx
