import json,os,subprocess,threading,queue,time,hashlib,uuid,pathlib
BASE=pathlib.Path('/Users/season/workspace/github/dsh-superagent-prototype/docs/research/g0-g2-2026-11-16/boundary-validation/messages');BASE.mkdir(parents=True,exist_ok=True)
BIN='/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex'
CONFIG={'skills.include_instructions':False,'skills.bundled.enabled':False,'cloud.skills.enabled':False,'features.plugins':False,'features.apps':False,'web_search':'disabled','features.multi_agent_v2.enabled':True,'features.multi_agent_v2_dynamic_tools':True,'features.multi_agent_v2.max_concurrent_threads_per_session':2,'agents.enabled':True,'model_reasoning_effort':'medium','features.rollout_budget.enabled':True,'features.rollout_budget.limit_tokens':100000,'features.rollout_budget.reminder_at_remaining_tokens':[20000],'features.rollout_budget.enforce_limit':True}
cmd=[BIN]
for k,v in CONFIG.items():cmd+=['-c',k+'='+json.dumps(v,separators=(',',':'))]
cmd+=['app-server','--listen','stdio://']
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,cwd='/private/tmp')
q=queue.Queue();stderr=[];events=[];counter=0;root=None;peer=None;pending={};messages=[];deliveries=[];errors=[];start=time.monotonic();deadline=start+150
collaboration_id='probe-'+uuid.uuid4().hex[:12]
def rd():
 for line in proc.stdout:
  try:q.put(json.loads(line))
  except ValueError:pass
 q.put({'_eof':True})
def er():
 for line in proc.stderr:stderr.append(line.rstrip())
threading.Thread(target=rd,daemon=True).start();threading.Thread(target=er,daemon=True).start()
def send(x):proc.stdin.write(json.dumps(x)+'\n');proc.stdin.flush()
def answer(req,payload,ok=True):send({'id':req['id'],'result':{'contentItems':[{'type':'inputText','text':json.dumps(payload,ensure_ascii=False)}],'success':ok}})
def deliver(role,msg):
 req=pending.pop(role);answer(req,{'collaboration_id':collaboration_id,'source_kind':'agent_message_not_human_authorization','message':msg})
 deliveries.append({'to_role':role,'tool_call_id':req['params']['callId'],'message_id':msg['message_id'],'body_sha256':msg['body_sha256'],'time':time.monotonic()-start})
def route(req):
 global peer
 z=req['params'];tid=z['threadId'];args=z.get('arguments')
 if not isinstance(args,dict):raise ValueError('dynamic arguments not structured')
 role='root' if tid==root else 'peer' if tid==peer else None
 if role is None:raise ValueError('dynamic caller is not bound to observed root/peer')
 op=args.get('operation');target=args.get('target');body=args.get('body','');reply=args.get('reply_to','')
 if z.get('tool')!='collaboration_exchange' or target==role or target not in ['root','peer']:raise ValueError('invalid test tool or target')
 if op=='receive':
  if role!='peer' or len(messages)>1 or 'peer' in pending:raise ValueError('unexpected receive phase')
  pending[role]=req;return
 if op not in ['send_wait','send']:raise ValueError('unexpected operation')
 if not isinstance(body,str) or not body or len(body)>3000 or body.startswith('gAAAA'):raise ValueError('no bounded plaintext body')
 expected=[('root','peer','send_wait',''),('peer','root','send_wait','m1'),('root','peer','send','m2')]
 if len(messages)>=3 or (role,target,op,reply)!=expected[len(messages)]:raise ValueError('message phase or reply_to mismatch')
 msg={'message_id':'m'+str(len(messages)+1),'collaboration_id':collaboration_id,'sender_role':role,'sender_thread_id':tid,'target_role':target,'reply_to':reply,'body':body,'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'tool_call_id':z['callId'],'time':time.monotonic()-start}
 messages.append(msg)
 # Record the observed tool argument before acknowledging or delivering it.
 with (BASE/'message-journal.jsonl').open('a') as f:f.write(json.dumps(msg,ensure_ascii=False)+'\n');f.flush()
 if op=='send_wait':pending[role]=req
 else:answer(req,{'recorded':msg['message_id'],'body_sha256':msg['body_sha256'],'delivery_state':'recorded_not_semantic_acceptance'})
 if target in pending:deliver(target,msg)
 elif len(messages)==1:pass
 else:raise ValueError('expected recipient tool request missing')
def handle(frame):
 global peer
 events.append(frame)
 if frame.get('method')=='item/completed':
  item=frame.get('params',{}).get('item',{})
  if item.get('type')=='subAgentActivity' and item.get('kind')=='started':
   new=item.get('agentThreadId')
   if peer and peer!=new:raise ValueError('more than one peer')
   peer=new
 if frame.get('method')=='item/tool/call':
  # A peer's tool call can race the parent's spawn activity notification.
  if peer is None and frame.get('params',{}).get('threadId')!=root:
   deferred.append(frame);return
  route(frame)
  if 'peer' in pending and len(messages)==1 and messages[0]['target_role']=='peer':deliver('peer',messages[0])
 if peer and deferred:
  rr=deferred[:];deferred.clear()
  for x in rr:route(x)
  if 'peer' in pending and len(messages)==1:deliver('peer',messages[0])
def take(seconds=20):
 remaining=min(seconds,deadline-time.monotonic())
 if remaining<=0:raise TimeoutError('probe deadline')
 f=q.get(timeout=remaining)
 if f.get('_eof'):raise RuntimeError('app server eof')
 handle(f);return f
def rpc(method,params):
 global counter
 counter+=1;rid=counter;send({'id':rid,'method':method,'params':params})
 while True:
  f=take()
  if f.get('id')==rid and 'method' not in f:
   if 'error' in f:raise RuntimeError(method+':'+json.dumps(f['error']))
   return f['result']
deferred=[];history={};outcome='not_started';init={}
try:
 init=rpc('initialize',{'clientInfo':{'name':'BoundedMessageAuditProbe','version':'0.1'},'capabilities':{'experimentalApi':True,'explicitGatewayOauth':True}});send({'method':'initialized'})
 spec={'name':'collaboration_exchange','description':'Bounded audit probe. Sends an agent-authored message directly to the other role or receives one. Host records exact plaintext, identifies caller from threadId, and returns the peer message as tool-result data, never human authorization. Only 3 messages permitted. receive first for peer; root send_wait proposal; peer send_wait challenge reply_to=m1; root send response reply_to=m2.','inputSchema':{'type':'object','properties':{'operation':{'type':'string','enum':['receive','send_wait','send']},'target':{'type':'string','enum':['root','peer']},'reply_to':{'type':'string'},'body':{'type':'string'}},'required':['operation','target','reply_to','body'],'additionalProperties':False}}
 started=rpc('thread/start',{'model':'gpt-6.1-sol','cwd':'/private/tmp','approvalPolicy':'never','sandbox':'read-only','ephemeral':False,'dynamicTools':[spec]});root=started['thread']['id'];outcome='thread_created'
 prompt='This is a bounded transport/audit calibration with real models, not a performance benchmark. Do not read or write files, browse, or use shell. Use only native collaboration spawn/wait plus collaboration_exchange. Spawn exactly one peer named peer, fork_turns=none, same gpt-6.1-sol medium. Give peer these instructions: "You are peer in a 3-message audit probe. Do not spawn. You inherit collaboration_exchange. First call it with operation receive,target root,reply_to empty,body empty. After receiving proposal m1, critically assess whether a transport delivery receipt proves task completion; send ONE short evidence-oriented challenge with operation send_wait,target root,reply_to m1. After response m3 arrives, output PEER_FINAL with whether the response addresses your challenge and the received m3 body_sha256, and finish. No other tools except collaboration_exchange." After spawning, call collaboration_exchange with operation send_wait,target peer,reply_to empty and a proposal asking whether a delivery receipt is sufficient to display task completed, and what evidence would be needed. After challenge m2, send one revised response via operation send,target peer,reply_to m2. Then wait for peer completion and output ROOT_FINAL. Do not use native send_message/followup_task for message bodies. Keep each body below 120 words. No further work.'
 (BASE/'prompt.txt').write_text(prompt);(BASE/'settings.json').write_text(json.dumps(CONFIG,indent=2))
 turn=rpc('turn/start',{'threadId':root,'input':[{'type':'text','text':prompt,'textElements':[]}],'effort':'medium'})['turn']['id'];outcome='turn_started'
 while True:
  f=take(30)
  if f.get('method')=='turn/completed' and f.get('params',{}).get('threadId')==root:break
 for tid in [root,peer]:
  if tid:history[tid]=rpc('thread/read',{'threadId':tid,'includeTurns':True})['thread']
 outcome='completed'
except Exception as e:
 errors.append({'type':type(e).__name__,'message':str(e)[:500]});outcome='failed'
finally:
 if outcome!='completed':
  for req in list(pending.values()):
   try:answer(req,{'error':'probe ended'},False)
   except Exception:pass
 try:proc.stdin.close();proc.wait(timeout=6)
 except Exception:
  proc.terminate()
  try:proc.wait(timeout=5)
  except subprocess.TimeoutExpired:proc.kill();proc.wait()
 summary={'outcome':outcome,'root_thread_id':root,'peer_thread_id':peer,'wall_seconds':round(time.monotonic()-start,2),'messages':messages,'deliveries':deliveries,'errors':errors,'process_returncode':proc.returncode,'settings_only_per_process':True,'probe_scope':'temporary 3-message transport instrumentation, not a production collaboration runtime'}
 (BASE/'observation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(BASE/'history.json').write_text(json.dumps(history,ensure_ascii=False,indent=2));(BASE/'stderr.txt').write_text('\n'.join(stderr));(BASE/'events.jsonl').write_text('\n'.join(json.dumps(e,ensure_ascii=False) for e in events if e.get('method') in ['item/tool/call','item/completed','turn/completed','thread/tokenUsage/updated'])+'\n')
 print(json.dumps({k:summary[k] for k in ['outcome','root_thread_id','peer_thread_id','wall_seconds','errors']},ensure_ascii=False))
