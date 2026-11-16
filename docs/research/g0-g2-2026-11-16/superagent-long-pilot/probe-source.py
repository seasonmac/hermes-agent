import importlib.util,json,pathlib,sys,time,hashlib,copy
B=pathlib.Path('/Users/season/workspace/github/dsh-superagent-prototype/docs/research/g0-g2-2026-11-16/superagent-long-pilot')
spec=importlib.util.spec_from_file_location('pilot_runtime',B/'runtime-source.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ORIGINAL=m.records();m.BASE=B
m.CONFIG['features.rollout_budget.limit_tokens']=60000
LIMIT=240000

def package(store,c):
 d={'question':store['E-A5'],'index':[{'id':x['id'],'actor':x['actor'],'refs':x['refs']} for x in store.values()]}
 d['sources' if c==0 else 'inline']=list(store.values()) if c==0 else [store[k] for k in ['T-A','E-A3','R-A']]
 return d

def longstore(kib):
 st=copy.deepcopy(ORIGINAL)
 # Constant object graph, varying only a low-relevance archived document's length.
 st['ARCHIVE-B']={'id':'ARCHIVE-B','actor':'worker','text':'','refs':['T-B']}
 st['T-B']['refs'].append('ARCHIVE-B')
 empty=len(m.enc(package(st,0)).encode());needed=kib*1024-empty
 assert needed>0
 paras=[];n=0
 while sum(map(len,paras))<needed:
  n+=1;topic=['sampling','interview scope','export formatting','geography','vendor classification','source overlap','date conventions','presentation review'][n%8]
  paras.append(f'Archived market-report note {n:04d}, topic {topic}. This is background material for T-B. The review grouped observations by buyer segment and source date. Registered accounts and active accounts were kept distinct, duplicate survey entries were excluded from descriptive counts, and interviews were treated as qualitative evidence. Different geographic coverage and overlapping vendor categories prevent a direct addition of subtotals. The team retained its original source identifiers and documented assumptions before producing charts. These archival notes neither change T-A authorization nor report execution of its backtest. ')
 st['ARCHIVE-B']['text']=''.join(paras)[:needed]
 assert len(m.enc(package(st,0)).encode())==kib*1024
 return st

def case_spec(name):
 c=int(name[-1]);family=name.split('-')[0];st=copy.deepcopy(ORIGINAL);variant='normal';expected=dict(m.EXPECTED);cites=dict(m.CITES)
 if family.startswith('L'):st=longstore(int(family[1:]));pkt=package(st,c)
 elif family=='silent':
  variant='silent'
  st['T-A']['refs']=[k for k in st['T-A']['refs'] if k not in ['D-A-v1','D-A-v2']]+['DATA-A','SUMMARY-A']
  del st['D-A-v1'];del st['D-A-v2']
  st['DATA-A']={'id':'DATA-A','actor':'dataset_record','text':'Data coverage for T-A runs through 2022. This dataset record does not authorize executing a backtest.','refs':['T-A']}
  st['SUMMARY-A']={'id':'SUMMARY-A','actor':'worker','text':'Current status summary for T-A: data coverage runs through 2020. The data-gap checklist is complete. Execution is paused.','refs':['T-A','DATA-A','R-A','E-A3']}
  pkt=package(st,c)
  if c==1:pkt['inline'].append(st['SUMMARY-A'])
  cites['coverage_year']='DATA-A'
 elif family=='unannounced':
  variant='unannounced';pkt=package(st,c)
  # Keep the reference/index entry but remove the server record with no upfront warning.
  if c==0:pkt['sources']=[v for v in pkt['sources'] if v['id']!='E-A2']
  del st['E-A2'];expected.update(list_policy='unknown',rejection_reason='unknown')
 else:raise ValueError(name)
 return {'name':name,'context':c,'variant':variant,'store':st,'packet':pkt,'expected':expected,'source_requirements':cites}

def score(a,case,app):
 errors=[]
 for k,value in case['expected'].items():
  if type(a.get(k))!=type(value) or a.get(k)!=value:errors.append({'kind':'value','field':k,'expected':value,'actual':a.get(k)})
 available={v['id'] for v in case['packet'].get('sources',case['packet'].get('inline',[]))}|{'E-A5'}
 for rr in app.reads:available.update(v['id'] for v in rr['result']['objects'] if 'error' not in v)
 for field,required in case['source_requirements'].items():
  ids=a.get('sources',{}).get(field,[])
  if case['variant']=='unannounced' and field in ['list_policy','rejection_reason']:
   if 'E-A2'in ids:errors.append({'kind':'unavailable_source','field':field,'actual':ids})
  elif required not in ids:errors.append({'kind':'missing_source','field':field,'expected':required,'actual':ids})
  if any(k not in available for k in ids):errors.append({'kind':'unread_source','field':field,'actual':ids})
 return {'passed':not errors,'errors':errors,'factual_errors':sum(x['kind']=='value' for x in errors),'source_errors':sum(x['kind']!='value' for x in errors)}

def spent():return sum(json.loads(p.read_text()).get('usage',{}).get('total_tokens',0) for p in B.glob('*/observation.json'))
def run(name):
 case=json.loads((B/'fixtures'/f'{name}.json').read_text());known=spent()
 # Conservative planning envelope only; runtime itself still has post-response soft budget semantics.
 reserve=70000 if name.startswith('L192') else 50000 if name.startswith('L96') else 40000
 if known+reserve>LIMIT:print(m.enc({'not_started':name,'reason':'suite soft admission ceiling','known_usage':known,'planning_reserve':reserve}),flush=True);return
 out=B/name;out.mkdir(exist_ok=False);m.STORE=case['store'];app=None;start=time.monotonic();o={'name':name,'context':case['context'],'variant':case['variant'],'status':'starting','known_suite_usage_before':known,'planning_reserve':reserve,'packet_bytes':len(m.enc(case['packet']).encode())}
 try:
  app=m.App(out,'normal');app.deadline=app.start+120
  worker=app.create('worker')
  prompt=m.COMMON+'\nResponse schema: '+m.enc(m.SHAPE)+'\nEvidence packet: '+m.enc(case['packet'])
  result=app.turn(worker,prompt);(out/'answer.txt').write_text(result);a=m.parse(result);m.save(out/'answer.json',a)
  grading=score(a,case,app);m.save(out/'score.json',grading);o.update(status='completed',score_passed=grading['passed'],recall_errors=len(grading['errors']),factual_errors=grading['factual_errors'],source_errors=grading['source_errors'])
 except Exception as e:o.update(status='failed',error={'type':type(e).__name__,'message':str(e)[:1000]})
 finally:
  if app:
   totals,complete=app.close();o.update(usage=totals,complete_thread_usage=complete,threads=app.threads,read_calls=len(app.reads),read_chars=sum(x['chars'] for x in app.reads),process_returncode=app.proc.returncode)
  o['wall_seconds']=round(time.monotonic()-start,2);m.save(out/'observation.json',o);print(m.enc(o),flush=True)
 return o

def freeze():
 (B/'fixtures').mkdir(exist_ok=True)
 for family in ['L32','L96','L192','silent','unannounced']:
  for c in [0,1]:m.save(B/'fixtures'/f'{family}-C{c}.json',case_spec(f'{family}-C{c}'))
 m.save(B/'settings.json',m.CONFIG);m.save(B/'dynamic-tool.json',m.SPEC);m.save(B/'response-schema.json',m.SHAPE)
 (B/'common-prompt.txt').write_text(m.COMMON)
 paths=[p for p in B.rglob('*') if p.is_file() and p.name!='manifest.json' and '__pycache__' not in str(p)]
 m.save(B/'manifest.json',{str(p.relative_to(B)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
 for family in ['L32','L96','L192']:
  a=case_spec(f'{family}-C0');b=case_spec(f'{family}-C1');assert a['store']==b['store']
 for c in [0,1]:
  a=case_spec(f'silent-C{c}');txt=m.enc(a['packet']);assert 'newer_version' not in txt and 'not_reconciled' not in txt and 'Superseded' not in txt
  a=case_spec(f'unannounced-C{c}');assert 'unavailable' not in m.enc(a['packet']);assert 'E-A2'not in a['store'];assert any(v['id']=='E-A2' for v in a['packet']['index'])
 print('Frozen fixtures and offline checks passed.')
if __name__=='__main__':
 if sys.argv[1]=='freeze':freeze()
 else:
  for n in sys.argv[2:]:
   r=run(n)
   if r is None or r['status']!='completed' or not r.get('complete_thread_usage') or not r.get('score_passed'):break
