import {useState,useEffect,useLayoutEffect,useRef,useCallback} from 'react';
import {CalendarDays,Folder,Inbox as InboxIcon,Settings as SettingsIcon} from 'lucide-react';
import {useStore} from './hooks/useStore';
import {api} from './api';
import {telegram} from './telegram';
import {getProjectStatuses,roleNames,type Invite,type Notice,type Screen,type Task} from './types';
import {Today} from './screens/Today';
import {Projects,ProjectScreen} from './screens/Projects';
import {NewTask,TaskDetail} from './screens/TaskScreens';
import {Inbox,Settings} from './screens/Other';
import {Back,Heading} from './components/UI';

function screenFromUrl():Screen{const route=location.hash.slice(1)||'/today';if(route==='/projects')return {type:'projects'};if(route==='/inbox')return {type:'inbox'};if(route==='/settings')return {type:'settings'};if(route==='/tasks/new')return {type:'new'};if(route.startsWith('/join/'))return {type:'join',code:decodeURIComponent(route.slice(6))};if(route.startsWith('/tasks/new?project='))return {type:'new',project:decodeURIComponent(route.split('=')[1]||'')};if(route.startsWith('/tasks/'))return {type:'detail',id:decodeURIComponent(route.slice(7))};if(route.startsWith('/projects/'))return {type:'project',id:decodeURIComponent(route.slice(10))};return {type:'today'}}
function urlForScreen(screen:Screen){switch(screen.type){case 'today':return '#/today';case 'projects':return '#/projects';case 'inbox':return '#/inbox';case 'settings':return '#/settings';case 'project':return `#/projects/${encodeURIComponent(screen.id)}`;case 'detail':return `#/tasks/${encodeURIComponent(screen.id)}`;case 'new':return screen.project?`#/tasks/new?project=${encodeURIComponent(screen.project)}`:'#/tasks/new';case 'join':return `#/join/${encodeURIComponent(screen.code)}`}}

function JoinScreen({code,onJoin,onDecline,onBack}:{code:string;onJoin:(code:string)=>Promise<string>;onDecline:(code:string)=>Promise<void>;onBack:()=>void}){
 const [invite,setInvite]=useState<Invite|null>(null);const [message,setMessage]=useState('');const [busy,setBusy]=useState(false);
 useEffect(()=>{let active=true;setInvite(null);setMessage('');api<Invite>(`/invites/${encodeURIComponent(code)}`).then(value=>{if(active)setInvite(value)}).catch(value=>{if(active)setMessage(value.message)});return()=>{active=false}},[code]);
 async function respond(accept:boolean){setBusy(true);setMessage('');try{if(accept)await onJoin(code);else{await onDecline(code);onBack()}}catch(value){setMessage(value instanceof Error?value.message:'Не удалось ответить')}finally{setBusy(false)}}
 return <><Back onClick={onBack}/><Heading title="Приглашение в проект"/>{invite?<section className="team-panel"><h2>{invite.projectName}</h2><p>Вас приглашают в проект с ролью «{roleNames[invite.role||'member']}».</p><div className="settings-row"><button className="primary" disabled={busy} onClick={()=>void respond(true)}>Принять</button><button className="subtle" disabled={busy} onClick={()=>void respond(false)}>Отклонить</button></div></section>:!message&&<p>Проверяем приглашение…</p>}{message&&<p className="form-error" role="alert">{message}</p>}</>
}

function InvitationBanner({invite,onAccept,onDecline}:{invite:Notice;onAccept:(code:string)=>Promise<string>;onDecline:(code:string)=>Promise<void>}){
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');
 async function respond(accept:boolean){if(busy)return;setBusy(true);setError('');try{if(accept)await onAccept(invite.inviteCode!);else await onDecline(invite.inviteCode!)}catch(value){setError(value instanceof Error?value.message:'Не удалось ответить')}finally{setBusy(false)}}
 return <section className="invitation-banner" role="status"><strong>{invite.title}</strong><p>{invite.text} Роль: {roleNames[invite.role||'member']}.</p><div className="settings-row"><button className="primary" disabled={busy} onClick={()=>void respond(true)}>Принять</button><button className="subtle" disabled={busy} onClick={()=>void respond(false)}>Отклонить</button></div>{error&&<p role="alert" className="form-error">{error}</p>}</section>
}

export function App(){
 const {data,loading,error,actions}=useStore();const [screen,setScreen]=useState<Screen>(screenFromUrl);const [stack,setStack]=useState<Screen[]>([]);const [toast,setToast]=useState('');const positions=useRef<Record<string,number>>({});const mainRef=useRef<HTMLElement>(null);
 const scrollKey=(value:Screen)=>value.type+('id'in value?value.id:'code'in value?value.code:'');
 const navigate=useCallback((next:Screen)=>{if(JSON.stringify(screen)===JSON.stringify(next))return;positions.current[scrollKey(screen)]=window.scrollY;setStack(items=>[...items,screen]);window.history.pushState({taskflow:true},'',urlForScreen(next));setScreen(next)},[screen]);
 const back=useCallback(()=>{if(stack.length){window.history.back();return}const fallback:Screen=screen.type==='project'?{type:'projects'}:{type:'today'};window.history.replaceState({taskflow:true},'',urlForScreen(fallback));setScreen(fallback)},[screen.type,stack.length]);
 useLayoutEffect(()=>{window.scrollTo({top:positions.current[scrollKey(screen)]||0,behavior:'instant'});mainRef.current?.focus({preventScroll:true})},[screen]);
 useEffect(()=>{const change=()=>{setScreen(screenFromUrl());setStack(items=>items.slice(0,-1))};window.addEventListener('hashchange',change);return()=>window.removeEventListener('hashchange',change)},[]);
 useEffect(()=>{if(!toast)return;const timer=window.setTimeout(()=>setToast(''),3500);return()=>window.clearTimeout(timer)},[toast]);
 useEffect(()=>{const app=telegram();if(!app)return;app.ready();app.expand();app.setHeaderColor('#12161c');app.setBackgroundColor('#12161c');app.setBottomBarColor?.('#171d25')},[]);
 useEffect(()=>{const app=telegram();if(!app)return;if(['today','projects','inbox'].includes(screen.type))app.BackButton.hide();else app.BackButton.show();app.BackButton.onClick(back);return()=>app.BackButton.offClick(back)},[screen.type,back]);
 const report=useCallback((value:unknown)=>setToast(value instanceof Error?value.message:'Операция не выполнена'),[]);
 const setTasks=(tasks:Task[])=>void actions.reorderTasks(tasks).catch(report);
 const update=(task:Task)=>void actions.updateTask(task).catch(report);
 const toggle=(id:string)=>{const task=data.tasks.find(item=>item.id===id);if(task&&data.projects.find(project=>project.id===task.project)?.members.find(member=>member.id===data.user.id)?.role!=='viewer')update({...task,done:!task.done,status:task.status})};
 const open=(id:string)=>navigate({type:'detail',id});const projectName=(id:string)=>data.projects.find(project=>project.id===id)?.name||'Без проекта';
 async function shareProject(id:string){try{const invite=await actions.createInvite(id);if(navigator.share){await navigator.share({title:invite.projectName,text:`Присоединяйтесь к проекту «${invite.projectName}». Код: ${invite.code}`,url:invite.url});setToast('Приглашение отправлено')}else{await navigator.clipboard.writeText(`${invite.url}\nКод: ${invite.code}`);setToast(`Ссылка скопирована · код ${invite.code}`)}}catch(value){if(value instanceof DOMException&&value.name==='AbortError')return;report(value)}}
 const join=useCallback(async(code:string)=>{const projectId=await actions.joinProject(code);navigate({type:'project',id:projectId});return projectId},[actions,navigate]);
 let content;
 if(loading)content=<div className="loading-card">Загружаем проекты и задачи…</div>;
 else if(error)content=<div className="auth-error" role="alert"><Heading title="Не удалось войти" subtitle={error}/><p>Откройте приложение кнопкой из Telegram-бота. Для локальной разработки включите <code>ALLOW_DEV_AUTH=true</code>.</p></div>;
 else switch(screen.type){
  case 'today':content=<Today data={data} onTasks={setTasks} onOpen={open} onToggle={toggle} onNew={()=>navigate({type:'new'})} onSettings={()=>navigate({type:'settings'})}/>;break;
  case 'projects':content=<Projects data={data} onOpen={id=>navigate({type:'project',id})} onAdd={actions.createProject} onJoin={async code=>{navigate({type:'join',code})}} onShare={id=>void shareProject(id)}/>;break;
  case 'project':content=<ProjectScreen id={screen.id} data={data} onBack={back} onNew={()=>navigate({type:'new',project:screen.id})} onOpen={open} onTasks={setTasks} onToggle={toggle} onShare={()=>void shareProject(screen.id)} onInvite={(identifier,role)=>actions.createInvite(screen.id,identifier,role)} onMember={(identifier,role)=>actions.setMember(screen.id,identifier,role)} onStatuses={(statuses,renames)=>actions.setStatuses(screen.id,statuses,renames)} onAccess={enabled=>actions.setJoinEnabled(screen.id,enabled)}/>;break;
  case 'new':content=<NewTask projects={data.projects.filter(project=>project.members.find(member=>member.id===data.user.id)?.role!=='viewer')} project={screen.project} onBack={back} onCreate={async task=>{await actions.createTask(task);back()}}/>;break;
  case 'detail':{const task=data.tasks.find(item=>item.id===screen.id);const project=data.projects.find(item=>item.id===task?.project);content=<TaskDetail task={task} project={projectName(task?.project||'')} statuses={getProjectStatuses(project)} readOnly={project?.members.find(member=>member.id===data.user.id)?.role==='viewer'} members={project?.members||[]} onBack={back} onUpdate={update} onToggle={()=>toggle(screen.id)}/>;break}
  case 'join':content=<JoinScreen code={screen.code} onJoin={join} onDecline={actions.declineInvite} onBack={back}/>;break;
  case 'inbox':content=<Inbox notices={data.notices} onDecline={actions.declineInvite} onError={report} onAccept={async code=>{const id=await actions.joinProject(code);navigate({type:'project',id})}}/>;break;
  case 'settings':content=<Settings data={data} onBack={back}/>;break;
 }
 const nav=screen.type==='project'||screen.type==='join'?'projects':screen.type;
 return <div id="app"><header className="top"><span className="brand">TASKFLOW</span><button className="icon" onClick={()=>navigate({type:'settings'})} aria-label="Профиль"><SettingsIcon size={19}/></button></header><div className="layout"><nav aria-label="Основная навигация">{([{id:'today',label:'Сегодня',icon:CalendarDays},{id:'projects',label:'Проекты',icon:Folder},{id:'inbox',label:'Входящие',icon:InboxIcon}] as const).map(item=><button key={item.id} className={nav===item.id?'active':''} aria-current={nav===item.id?'page':undefined} onClick={()=>navigate({type:item.id})}><span><item.icon size={21}/></span>{item.label}{item.id==='inbox'&&data.notices.length>0&&<i className="unread-dot"/>}</button>)}</nav><main ref={mainRef} tabIndex={-1}>{!loading&&screen.type!=='join'&&screen.type!=='inbox'&&data.notices.length>0&&<InvitationBanner key={data.notices[0].id} invite={data.notices[0]} onAccept={join} onDecline={actions.declineInvite}/>}{content}</main></div><div className={`toast ${toast?'visible':''}`} role="status" aria-live="polite">{toast}</div></div>
}
