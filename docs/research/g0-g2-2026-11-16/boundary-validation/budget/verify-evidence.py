import pathlib,json,hashlib,shutil
p=pathlib.Path(__file__).resolve().parent
ds={k:json.loads((p/(k+'.json')).read_text()) for k in ['breach','cached','units','shared','inflight']}
for k,d in ds.items():
 assert not d.get('error'),(k,d.get('error'))
 assert d['strict_config']['exit']==0 and d['server_exit']==0,k
 assert all(not r['authorization_present'] and r['sent'] for r in d['requests']),k
 assert all(not s['result'].get('timeout') for s in d['stages']),k
b=ds['breach'];assert len(b['requests'])==4 and b['first_server_tool_calls']==2
assert b['same_process_resumed_turn']['terminal']['turn']['status']=='failed'
assert b['resumed_turn']['terminal']['turn']['status']=='completed'
assert b['requests'][2]['usage']['input_tokens']==b['requests'][3]['usage']['input_tokens']==1
c=ds['cached'];assert c['stages'][0]['result']['terminal']['turn']['status']=='completed'
assert '85 weighted tokens' in json.dumps(c['requests'][1]['budget_messages'])
s=ds['shared'];assert [r['role'] for r in s['requests']].count('child')==1
assert '10 weighted tokens' in json.dumps(s['requests'][3]['budget_messages'])
assert s['stages'][1]['result']['terminal']['turn']['error']['codexErrorInfo']=='sessionBudgetExceeded'
i=ds['inflight'];assert i['max_simultaneous_fixture_requests']==2
assert sum(r['usage']['input_tokens'] for r in i['requests'][:3])==210
rroot=next(r for r in i['requests'] if r['role']=='root' and r['role_request']==2)
rchild=next(r for r in i['requests'] if r['role']=='child')
assert rroot['arrived']<rchild['completed']<rroot['completed']
assert not any(r.get('barrier_timeout') for r in i['requests'])
for roll in i['rollout_evidence']:
 completions=[r['payload'] for r in roll['records'] if r['type']=='event_msg' and r['payload'].get('type')=='task_complete']
 assert completions and completions[0]['error']['codex_error_info']=='session_budget_exceeded'
print('PASS: all five budget evidence files satisfy the recorded assertions; 20 fixture requests, 0 real model calls.')
