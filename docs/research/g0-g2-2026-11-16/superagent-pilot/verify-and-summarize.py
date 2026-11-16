import json,hashlib
from pathlib import Path
B=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def hashed(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
for name,h in read(B/'manifest.json').items():assert hashlib.sha256((B/name).read_bytes()).hexdigest()==h,name
allrows=[];surfaces=[]
for d in sorted(B.iterdir()):
 if not d.is_dir() or not(d/'observation.json').exists():continue
 o=read(d/'observation.json');h=read(d/'history.json');u=read(d/'usage-evidence.json');summ=read(d/'usage-summary.json');reads=read(d/'reads.json');score=read(d/'score.json');answer=read(d/'answer.json')
 assert o['status']=='completed' and o['process_returncode']==0 and summ['complete_thread_usage'],d.name
 assert len(h)==len(o['threads'])==len(u)
 sums={k:0 for k in ['input_tokens','cached_input_tokens','output_tokens','total_tokens']}
 for role,v in u.items():
  prev={k:0 for k in sums}
  for e in v['usage_events']:
   a=e['info']['total_token_usage'];inc=e['info']['last_token_usage']
   assert all(a[k]-prev[k]==inc[k] for k in sums),(d.name,role)
   prev={k:a[k] for k in sums}
  for k in sums:sums[k]+=prev[k]
  t=h[v['thread_id']];assert all(tr['status']=='completed' for tr in t['turns'])
  items=[it for tr in t['turns'] for it in tr['items']]
  assert all(it['type'] in ['userMessage','agentMessage','reasoning','dynamicToolCall'] for it in items)
  for it in items:
   if it['type']=='dynamicToolCall':
    assert it['tool']=='evidence_read' and it['success']
    rr=[r for r in reads if r['call_id']==it['id']];assert len(rr)==1
    assert it['arguments']['ids']==rr[0]['ids']
    assert json.loads(it['contentItems'][0]['text'])==rr[0]['result']
  rs=[json.loads(line) for line in Path(t['path']).read_text().splitlines()]
  assert hashlib.sha256(Path(t['path']).read_bytes()).hexdigest()==v['rollout_sha256']
  ws=[r['payload']['state'] for r in rs if r['type']=='world_state'];meta=next(r['payload'] for r in rs if r['type']=='session_meta')
  contexts=[r['payload'] for r in rs if r['type']=='turn_context']
  assert contexts and all(c['model']=='gpt-6.1-sol' and c['effort']=='medium' for c in contexts)
  surface={'case':d.name,'role':role,'cli_version':meta['cli_version'],'base_instructions':hashed(meta.get('base_instructions')),'dynamic_tools':hashed(meta.get('dynamic_tools'))}
  for key in ['tools','top_level_tools','skills','host_skills','managed_developer_instructions']:
   vals=sorted(set(hashed(w.get(key)) for w in ws));assert len(vals)==1,(d.name,key);surface[key]=vals[0]
  surfaces.append(surface)
 assert all(sums[k]==summ['totals'][k] for k in sums)
 # Independently recheck required values and source accessibility, including unknown in broken-source cases.
 exp=read(B/'expected.json');expected=dict(exp['normal'])
 if o['variant']=='broken':expected.update(exp['broken_overrides'])
 assert all(type(answer.get(k))==type(value) and answer.get(k)==value for k,value in expected.items()),(d.name,'facts')
 packet=read(B/f"packet-{o['variant']}-C{o['context']}.json")
 available={x['id'] for x in packet.get('sources',packet.get('inline',[]))}|{'E-A5'}
 for rr in reads:available.update(x['id'] for x in rr['result']['objects'] if 'error' not in x)
 for field,required in exp['source_requirements'].items():
  ids=answer['sources'][field];assert set(ids)<=available
  if o['variant']=='broken' and field in exp['broken_overrides']:assert 'E-A2' not in ids
  else:assert required in ids,(d.name,field)
 assert score['passed'] and not score['errors']
 allrows.append({'case':d.name,**summ['totals'],'model_usage_increments':summ['usage_increments'],'read_calls':len(reads),'read_chars':o['read_chars'],'wall_seconds':o['wall_seconds'],'recall_errors':len(score['errors']),'passed':score['passed']})
keys=['base_instructions','dynamic_tools','tools','top_level_tools','skills','host_skills','managed_developer_instructions']
comparability={k:len({s[k] for s in surfaces})==1 for k in keys}
assert all(comparability.values()),comparability
sums={k:sum(r[k] for r in allrows) for k in ['input_tokens','cached_input_tokens','output_tokens','total_tokens','model_usage_increments']}
save(B/'surface-audit.json',{'threads':surfaces,'same_across_all_threads':comparability})
save(B/'results.json',{'rows':allrows,'aggregate':sums,'verification_passed':True,'count':len(allrows),'limitations':['one sample per condition','uncontrolled cache warmth','synthetic enum-answer task','fresh-session reconstruction, not native compaction or month-long run','currency costs unavailable']})
print(json.dumps({'count':len(allrows),'aggregate':sums,'same_surfaces':comparability,'verified':True},indent=2))
