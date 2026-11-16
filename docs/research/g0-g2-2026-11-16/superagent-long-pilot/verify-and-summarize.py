import json,hashlib
from pathlib import Path
B=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def hashed(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
for name,h in read(B/'manifest.json').items():assert hashlib.sha256((B/name).read_bytes()).hexdigest()==h,name
rows=[];surfaces=[]
for d in sorted(B.iterdir()):
 if not d.is_dir() or not(d/'observation.json').exists():continue
 o=read(d/'observation.json');assert o['status']=='completed' and o['process_returncode']==0,d.name
 f=read(B/'fixtures'/f'{d.name}.json');h=read(d/'history.json');u=read(d/'usage-evidence.json');su=read(d/'usage-summary.json');a=read(d/'answer.json');rr=read(d/'reads.json');score=read(d/'score.json');prompts=read(d/'prompts.json')
 assert len(prompts)==1 and json.loads(prompts[0]['text'].split('Evidence packet: ',1)[1])==f['packet']
 assert len(h)==len(u)==len(o['threads'])==1 and su['complete_thread_usage']
 totals={k:0 for k in ['input_tokens','cached_input_tokens','output_tokens','total_tokens']}
 for role,v in u.items():
  prev={k:0 for k in totals}
  for e in v['usage_events']:
   current=e['info']['total_token_usage'];inc=e['info']['last_token_usage']
   assert all(current[k]-prev[k]==inc[k] for k in totals)
   prev={k:current[k] for k in totals}
  totals=prev
  t=h[v['thread_id']];assert all(tr['status']=='completed' for tr in t['turns'])
  items=[i for tr in t['turns'] for i in tr['items']]
  assert all(i['type'] in ['userMessage','agentMessage','reasoning','dynamicToolCall'] for i in items)
  for i in items:
   if i['type']=='dynamicToolCall':
    assert i['tool']=='evidence_read' and i['success'];r=next(x for x in rr if x['call_id']==i['id'])
    assert i['arguments']['ids']==r['ids']
    assert json.loads(i['contentItems'][0]['text'])==r['result']
    expected=[f['store'].get(k,{'id':k,'error':'unavailable'}) for k in r['ids']]
    assert r['result']['objects']==expected
  path=Path(t['path']);assert hashlib.sha256(path.read_bytes()).hexdigest()==v['rollout_sha256']
  records=[json.loads(s) for s in path.read_text().splitlines()];meta=next(r['payload'] for r in records if r['type']=='session_meta');ws=[r['payload']['state'] for r in records if r['type']=='world_state'];contexts=[r['payload'] for r in records if r['type']=='turn_context']
  assert all(c['model']=='gpt-6.1-sol' and c['effort']=='medium' for c in contexts)
  sf={'case':d.name,'version':meta['cli_version'],'base_instructions':hashed(meta['base_instructions']),'dynamic_tools':hashed(meta['dynamic_tools'])}
  for k in ['tools','top_level_tools','skills','host_skills','managed_developer_instructions']:
   vals={hashed(w.get(k)) for w in ws};assert len(vals)==1;sf[k]=next(iter(vals))
  surfaces.append(sf)
 assert all(totals[k]==su['totals'][k] for k in totals)
 accessible={v['id'] for v in f['packet'].get('sources',f['packet'].get('inline',[]))}|{'E-A5'}
 for r in rr:accessible.update(v['id'] for v in r['result']['objects'] if 'error' not in v)
 errors=[]
 for k,value in f['expected'].items():
  if type(a.get(k))!=type(value) or a.get(k)!=value:errors.append({'kind':'value','field':k})
 for field,required in f['source_requirements'].items():
  ids=a.get('sources',{}).get(field,[])
  if f['variant']=='unannounced' and field in ['list_policy','rejection_reason']:
   if 'E-A2'in ids:errors.append({'kind':'unavailable_source','field':field})
  elif required not in ids:errors.append({'kind':'missing_source','field':field})
  if any(k not in accessible for k in ids):errors.append({'kind':'unread_source','field':field})
 assert sorted((e['kind'],e['field']) for e in errors)==sorted((e['kind'],e['field']) for e in score['errors'])
 assert score['passed']==(len(errors)==0)
 rows.append({'case':d.name,'context':o['context'],'variant':o['variant'],**su['totals'],'usage_increments':su['usage_increments'],'packet_bytes':o['packet_bytes'],'read_calls':len(rr),'read_chars':o['read_chars'],'wall_seconds':o['wall_seconds'],'factual_errors':score['factual_errors'],'source_errors':score['source_errors'],'passed':score['passed'],'errors':score['errors']})
keys=['version','base_instructions','dynamic_tools','tools','top_level_tools','skills','host_skills','managed_developer_instructions'];same={k:len({x[k] for x in surfaces})==1 for k in keys};assert all(same.values())
aggregate={k:sum(r[k] for r in rows) for k in ['input_tokens','cached_input_tokens','output_tokens','total_tokens','usage_increments']}
aggregate['uncached_input_plus_output']=aggregate['input_tokens']-aggregate['cached_input_tokens']+aggregate['output_tokens']
save(B/'surface-audit.json',{'threads':surfaces,'same':same});save(B/'results.json',{'count':len(rows),'rows':rows,'aggregate':aggregate,'evidence_verified':True,'passing_cases':sum(r['passed'] for r in rows)})
print(json.dumps({'count':len(rows),'aggregate':aggregate,'passing_cases':sum(r['passed'] for r in rows),'evidence_verified':True},indent=2))
