import os,json,time,threading,subprocess,tempfile,queue,http.server,pathlib,traceback,hashlib
OUT=pathlib.Path('/Users/season/workspace/github/dsh-superagent-prototype/docs/research/g0-g2-2026-11-16/boundary-validation/budget');OUT.mkdir(parents=True,exist_ok=True)
BIN='/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex'
BASE='''cli_auth_credentials_store="file"
model="gpt-6.1-sol"
model_provider="budget_fixture"
web_search="disabled"
[model_providers.budget_fixture]
name="Local budget fixture"
base_url="http://127.0.0.1:{port}/v1"
wire_api="responses"
requires_openai_auth=false
request_max_retries=0
stream_max_retries=0
[agents]
enabled=true
max_threads=4
[features]
enable_request_compression=false
respect_system_proxy=true
plugins=false
apps=false
recommended_plugins=false
skill_search=false
multi_agent_v2_dynamic_tools=false
[features.multi_agent_v2]
enabled=true
[features.rollout_budget]
enabled=true
limit_tokens=100
reminder_at_remaining_tokens=[90,50,10]
enforce_limit=true
[skills]
include_instructions=false
[skills.bundled]
enabled=false
[cloud.skills]
enabled=false
[analytics]
enabled=false
'''
def usage(i=0,c=0,o=0,u=None):
 d={'input_tokens':i,'input_tokens_details':{'cached_tokens':c},'output_tokens':o,'total_tokens':i+o}
 if u is not None:d['codex_rollout_budget_units']=u
 return d
def message(text):return {'type':'message','role':'assistant','id':'msg_fixture','content':[{'type':'output_text','text':text}]}
def call(name,args,ns=None):
 d={'type':'function_call','call_id':'call_'+name,'name':name,'arguments':json.dumps(args)}
 if ns:d['namespace']=ns
 return d
class Fixture:
 def __init__(self,case):
  self.case=case;self.requests=[];self.lock=threading.Lock();self.both=threading.Event();self.child_done=threading.Event();self.active=0;self.max_active=0;self.roles={}
  owner=self
  class Handler(http.server.BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
    text=json.dumps(body)
    root_prompt_present=any(x.get('role')=='user' and 'ROOT_BUDGET' in json.dumps(x) for x in body.get('input',[]))
    role='root' if root_prompt_present or owner.case in ['breach','cached','units'] else 'child'
    with owner.lock:
     owner.active+=1;owner.max_active=max(owner.max_active,owner.active)
     n=owner.roles.get(role,0)+1;owner.roles[role]=n
     rec={'index':len(owner.requests)+1,'role':role,'role_request':n,'arrived':time.monotonic(),'route':self.path,'authorization_present':bool(self.headers.get('Authorization')),'user_inputs':[x for x in body.get('input',[]) if x.get('role')=='user'],'request_metadata':body.get('client_metadata'),'budget_messages':[x for x in body.get('input',[]) if '<rollout_budget>' in json.dumps(x)],'tools':[{'type':t.get('type'),'name':t.get('name'),'namespace':t.get('namespace')} for t in body.get('tools',[])]}
     owner.requests.append(rec)
    if owner.case=='breach': us=usage(120 if n<=2 else 1);item=call('budget_probe',{}) if n<=2 else message('RESUME_ONE_TOKEN')
    elif owner.case=='cached':us=usage(1000,990,5) if n==1 else usage(86);item=message('CACHED_OK')
    elif owner.case=='units':us=usage(1000,0,10,5 if n==1 else 96);item=message('UNITS_OK')
    elif role=='root' and n==1:us=usage(10);item=call('spawn_agent',{'task_name':'budget_worker','message':'CHILD_BUDGET','fork_turns':'none'},'collaboration')
    elif owner.case=='shared':us=usage(70 if role=='child' else (10 if n==2 else 20));item=message(role.upper()+'_OK')
    elif owner.case=='inflight':
     if owner.roles.get('child',0)>=1 and owner.roles.get('root',0)>=2:owner.both.set()
     if not owner.both.wait(15):rec['barrier_timeout']=True
     if role=='root':owner.child_done.wait(10);time.sleep(.6)
     us=usage(100);item=message(role.upper()+'_INFLIGHT_OK')
    rec['usage']=us
    events=[{'type':'response.created','response':{'id':'resp_'+str(rec['index'])}},{'type':'response.output_item.done','item':item},{'type':'response.completed','response':{'id':'resp_'+str(rec['index']),'usage':us}}]
    encoded=''.join('data: '+json.dumps(x)+'\n\n' for x in events).encode()
    try:
     self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Content-Length',str(len(encoded)));self.end_headers();self.wfile.write(encoded);self.wfile.flush();rec['sent']=True
    except Exception as e:rec['send_error']=str(e)
    rec['completed']=time.monotonic()
    with owner.lock:owner.active-=1
    if role=='child':owner.child_done.set()
  self.http=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);self.http.daemon_threads=True
  threading.Thread(target=self.http.serve_forever,daemon=True).start()
 def close(self):self.both.set();self.child_done.set();self.http.shutdown();self.http.server_close()
class Client:
 def __init__(self,home,work):
  self.events=[];self.responses={};self.id=0;self.cv=threading.Condition();self.stderr=[];self.tools=0
  self.env={'HOME':os.environ['HOME'],'CODEX_HOME':str(home),'PATH':'/usr/bin:/bin','TMPDIR':'/private/tmp','NO_PROXY':'*','no_proxy':'*'}
  self.p=subprocess.Popen([BIN,'app-server','--strict-config'],cwd=work,env=self.env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
  def read():
   for line in self.p.stdout:
    try:d=json.loads(line)
    except:continue
    with self.cv:
     if 'id'in d and ('result'in d or 'error'in d):self.responses[d['id']]=d
     else:
      self.events.append(d)
      if 'id'in d:
       self.tools+=1;self.send({'id':d['id'],'result':{'contentItems':[{'type':'inputText','text':'PROBE_TOOL_RAN'}],'success':True}})
     self.cv.notify_all()
  threading.Thread(target=read,daemon=True).start();threading.Thread(target=lambda:self.stderr.extend(self.p.stderr.readlines()),daemon=True).start()
  self.rpc('initialize',{'clientInfo':{'name':'budget_boundary_fixture','version':'1'},'capabilities':{'experimentalApi':True}});self.send({'method':'initialized'})
 def send(self,d):self.p.stdin.write(json.dumps(d)+'\n');self.p.stdin.flush()
 def rpc(self,m,p):
  self.id+=1;i=self.id;self.send({'id':i,'method':m,'params':p});end=time.monotonic()+20
  with self.cv:
   while i not in self.responses and time.monotonic()<end:self.cv.wait(.1)
  if i not in self.responses:raise TimeoutError(m)
  return self.responses[i]
 def start(self,work):
  d=self.rpc('thread/start',{'cwd':str(work),'model':'gpt-6.1-sol','modelProvider':'budget_fixture','approvalPolicy':'never','sandbox':'read-only','baseInstructions':'Follow fixture instructions.','dynamicTools':[{'name':'budget_probe','description':'Synthetic fixture tool','inputSchema':{'type':'object','properties':{}}}]})
  if 'error'in d:raise RuntimeError(d)
  return d['result']['thread']['id']
 def turn(self,tid,prompt,timeout=25):
  before=len(self.events);r=self.rpc('turn/start',{'threadId':tid,'input':[{'type':'text','text':prompt}]})
  if 'error'in r:return {'rpc':r}
  turnid=r['result']['turn']['id'];end=time.monotonic()+timeout
  with self.cv:
   while time.monotonic()<end:
    for e in self.events[before:]:
     if e.get('method')=='turn/completed' and e.get('params',{}).get('turn',{}).get('id')==turnid:return {'rpc':r,'terminal':e['params']}
    self.cv.wait(.1)
  return {'rpc':r,'timeout':True}
 def close(self):
  try:self.p.stdin.close();self.p.wait(timeout=5)
  except: self.p.terminate();self.p.wait(timeout=5)
  return self.p.returncode

def run(case):
 f=Fixture(case);c=None;result={'case':case,'limit_tokens':100,'real_model_calls':0,'actual_model_cost':0}
 with tempfile.TemporaryDirectory(prefix='codex-budget-'+case+'-',dir='/private/tmp') as tmp:
  home=pathlib.Path(tmp)/'codex-home';work=pathlib.Path(tmp)/'work';home.mkdir();work.mkdir();(home/'config.toml').write_text(BASE.format(port=f.http.server_port))
  env={'HOME':os.environ['HOME'],'CODEX_HOME':str(home),'PATH':'/usr/bin:/bin','TMPDIR':'/private/tmp','NO_PROXY':'*','no_proxy':'*'}
  check=subprocess.run([BIN,'app-server','--strict-config','--print-startup-config'],env=env,cwd=work,capture_output=True,text=True,timeout=20);result['strict_config']={'exit':check.returncode,'stderr':check.stderr,'stdout':check.stdout}
  try:
   if check.returncode:raise RuntimeError('config invalid')
   c=Client(home,work);tid=c.start(work);result['root_thread_id']=tid;result['stages']=[]
   for i in range(3):
    before=len(f.requests);r=c.turn(tid,'ROOT_BUDGET' if i==0 else 'FOLLOWUP_'+str(i));time.sleep(.3)
    result['stages'].append({'stage':i,'provider_requests_before':before,'provider_requests_after':len(f.requests),'result':r})
    if case=='breach' and i==1:break
   result['tool_calls_received']=c.tools
   result['events']=c.events
   result['rollout_evidence']=[{'file':p.name,'records':[json.loads(line) for line in p.read_text().splitlines() if any(t in line for t in ['task_complete','task_started','session_budget','token_count','collab_spawn','session_meta'])]} for p in home.glob('sessions/**/*.jsonl')]
   result['root_read']=c.rpc('thread/read',{'threadId':tid,'includeTurns':True})
   if case=='breach':
    result['same_process_resume']=c.rpc('thread/resume',{'threadId':tid,'cwd':str(work),'modelProvider':'budget_fixture'});before_resume=len(f.requests);result['same_process_resumed_turn']=c.turn(tid,'SAME_PROCESS_RESUME_BUDGET');result['same_process_resume_request_delta']=len(f.requests)-before_resume;result['first_server_tool_calls']=c.tools;result['events']=list(c.events);result['first_server_exit']=c.close();c=Client(home,work);before=len(f.requests);result['cold_resume']=c.rpc('thread/resume',{'threadId':tid,'cwd':str(work),'modelProvider':'budget_fixture'});result['resumed_turn']=c.turn(tid,'RESUME_BUDGET');result['resume_request_delta']=len(f.requests)-before
  except Exception as e:result['error']=repr(e);result['traceback']=traceback.format_exc()
  finally:
   if c:result['server_exit']=c.close();result['stderr']=''.join(c.stderr)
   f.close();result['requests']=f.requests;result['max_simultaneous_fixture_requests']=f.max_active
  # Only synthetic content is retained; replace ephemeral paths for portable evidence.
  text=json.dumps(result,indent=2).replace(tmp,'<isolated-temp>')
  (OUT/(case+'.json')).write_text(text)
  print(case, 'requests',len(f.requests),'roles',f.roles,'error',result.get('error'),flush=True)
  for s in result.get('stages',[]):print('stage',s['stage'],s['provider_requests_after'],s['result'].get('terminal',s['result']),flush=True)
for case in __import__('sys').argv[1:] or ['breach','cached','units','shared','inflight']:run(case)
