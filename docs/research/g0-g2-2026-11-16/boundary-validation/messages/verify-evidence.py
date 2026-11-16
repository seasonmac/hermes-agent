import json, hashlib
from pathlib import Path
BASE=Path(__file__).resolve().parent
def read(name): return json.loads((BASE/name).read_text())
o=read('observation.json'); h=read('history.json')
messages=[json.loads(s) for s in (BASE/'message-journal.jsonl').read_text().splitlines()]
assert o['outcome']=='completed' and not o['errors'] and o['process_returncode']==0
assert len(messages)==3 and messages==o['messages']
roles={r:o[r+'_thread_id'] for r in ['root','peer']}
assert set(h)==set(roles.values())
assert h[roles['peer']]['parentThreadId']==roles['root']
items={}
for r,tid in roles.items():
 assert len(h[tid]['turns'])==1 and h[tid]['turns'][0]['status']=='completed'
 items[r]={i['id']:i for i in h[tid]['turns'][0]['items']}
checks=[]
for n,m in enumerate(messages):
 assert m['message_id']=='m'+str(n+1) and m['reply_to']==('' if n==0 else 'm'+str(n))
 assert m['body_sha256']==hashlib.sha256(m['body'].encode()).hexdigest()
 assert m['sender_thread_id']==roles[m['sender_role']]
 src=items[m['sender_role']][m['tool_call_id']]
 assert src['type']=='dynamicToolCall' and src['tool']=='collaboration_exchange' and src['success']
 assert src['arguments']['body']==m['body'] and src['arguments']['reply_to']==m['reply_to'] and src['arguments']['target']==m['target_role']
 ds=[d for d in o['deliveries'] if d['message_id']==m['message_id']]; assert len(ds)==1
 d=ds[0]; assert d['to_role']==m['target_role'] and d['body_sha256']==m['body_sha256'] and d['time']>=m['time']
 dest=items[d['to_role']][d['tool_call_id']]; assert dest['success']
 env=json.loads(dest['contentItems'][0]['text'])
 assert env['message']==m and env['source_kind']=='agent_message_not_human_authorization'
 checks.append({'message_id':m['message_id'],'sender_arguments_match':True,'journal_hash_valid':True,'recipient_result_exact_match':True})
finals=[i['text'] for i in items['peer'].values() if i['type']=='agentMessage' and i.get('phase')=='final_answer']
assert len(finals)==1 and 'PEER_FINAL' in finals[0] and messages[-1]['body_sha256'] in finals[0]
assert 'Yes.' in finals[0]
result={'passed':True,'checks':checks,'both_turns_completed':True,'native_peer_parent_verified':True,'peer_final_contains_m3_hash_and_explicit_yes':True,'scope':'Exact content delivery and expressed acceptance in a fixed three-message probe; not general semantic correctness or crash durability.'}
(BASE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('PASS: 3 sender arguments = journal records = recipient tool results; hashes, parentage, reply chain and peer final verified.')
