import {useState,useEffect,useLayoutEffect,useRef,useCallback} from 'react';
import {CalendarDays,Folder,Inbox as InboxIcon,Settings as SettingsIcon} from 'lucide-react';
import {useStore} from './hooks/useStore';
import {telegram} from './telegram';
import type {Screen,Task} from './types';
import {Today} from './screens/Today';
import {Projects,ProjectScreen,SharedProjectScreen} from './screens/Projects';
import {NewTask,TaskDetail} from './screens/TaskScreens';
import {Inbox,Settings} from './screens/Other';
import {CommandPalette} from './components/CommandPalette';
import {projectShareUrl,readSharedProject,sharedProjectHash} from './share';

function screenFromUrl():Screen{
 const route=location.hash.slice(1)||'/today';
 if(route==='/projects')return {type:'projects'};
 if(route==='/inbox')return {type:'inbox'};
 if(route==='/settings')return {type:'settings'};
 if(route==='/tasks/new')return {type:'new'};
 if(route.startsWith('/tasks/new?project='))return {type:'new',project:decodeURIComponent(route.split('=')[1]||'')};
 if(route.startsWith('/tasks/'))return {type:'detail',id:decodeURIComponent(route.slice(7))};
 if(route.startsWith('/projects/'))return {type:'project',id:decodeURIComponent(route.slice(10))};
 if(route.startsWith('/shared/')){const snapshot=readSharedProject(route.slice(8));if(snapshot)return {type:'shared',snapshot}}
 return {type:'today'};
}

function urlForScreen(screen:Screen){
 switch(screen.type){
  case 'today':return '#/today';case 'projects':return '#/projects';case 'inbox':return '#/inbox';case 'settings':return '#/settings';
  case 'project':return `#/projects/${encodeURIComponent(screen.id)}`;case 'detail':return `#/tasks/${encodeURIComponent(screen.id)}`;
  case 'new':return screen.project?`#/tasks/new?project=${encodeURIComponent(screen.project)}`:'#/tasks/new';
  case 'shared':return sharedProjectHash(screen.snapshot);
 }
}

export function App(){
 const {data,setData,error}=useStore();const [screen,setScreen]=useState<Screen>(screenFromUrl);const [stack,setStack]=useState<Screen[]>([]);const [palette,setPalette]=useState(false);const [toast,setToast]=useState('');const positions=useRef<Record<string,number>>({});const mainRef=useRef<HTMLElement>(null);
 const scrollKey=(value:Screen)=>value.type+('id'in value?value.id:value.type==='shared'?value.snapshot.project.id:'');
 const navigate=useCallback((next:Screen)=>{if(JSON.stringify(screen)===JSON.stringify(next))return;positions.current[scrollKey(screen)]=window.scrollY;setStack(items=>[...items,screen]);window.history.pushState({taskflow:true},'',urlForScreen(next));setScreen(next)},[screen]);
 const back=useCallback(()=>{if(stack.length){window.history.back();return}const fallback:Screen=screen.type==='project'||screen.type==='shared'?{type:'projects'}:{type:'today'};window.history.replaceState({taskflow:true},'',urlForScreen(fallback));setScreen(fallback)},[screen.type,stack.length]);
 useLayoutEffect(()=>{window.scrollTo({top:positions.current[scrollKey(screen)]||0,behavior:'instant'});mainRef.current?.focus({preventScroll:true})},[screen]);
 useEffect(()=>{const onRouteChange=()=>{setScreen(screenFromUrl());setStack(items=>items.slice(0,-1))};window.addEventListener('hashchange',onRouteChange);return()=>window.removeEventListener('hashchange',onRouteChange)},[]);
 useEffect(()=>{const onKey=(event:KeyboardEvent)=>{const target=event.target as HTMLElement;if(event.key==='/'&&!palette&&!['INPUT','TEXTAREA','SELECT'].includes(target.tagName)){event.preventDefault();setPalette(true)}if(event.key==='Escape'&&palette)setPalette(false)};window.addEventListener('keydown',onKey);return()=>window.removeEventListener('keydown',onKey)},[palette]);
 useEffect(()=>{if(!toast)return;const timer=window.setTimeout(()=>setToast(''),3500);return()=>window.clearTimeout(timer)},[toast]);
 useEffect(()=>{const tg=telegram();if(!tg)return;tg.ready();tg.expand();tg.setHeaderColor('#12161c');tg.setBackgroundColor('#12161c');tg.setBottomBarColor?.('#171d25')},[]);
 useEffect(()=>{const tg=telegram();if(!tg)return;if(['today','projects','inbox'].includes(screen.type))tg.BackButton.hide();else tg.BackButton.show();tg.BackButton.onClick(back);return()=>tg.BackButton.offClick(back)},[screen.type,back]);
 const setTasks=(tasks:Task[])=>setData(current=>({...current,tasks}));
 const update=(task:Task)=>setData(current=>({...current,tasks:current.tasks.map(item=>item.id===task.id?task:item)}));
 const toggle=(id:string)=>setData(current=>({...current,tasks:current.tasks.map(task=>task.id===id?{...task,done:!task.done,status:task.done?'В работе':'Готово'}:task)}));
 const open=(id:string)=>navigate({type:'detail',id});const projectName=(id:string)=>data.projects.find(project=>project.id===id)?.name||'Без проекта';
 async function shareProject(id:string){
  const project=data.projects.find(item=>item.id===id);if(!project)return;const url=projectShareUrl(project,data.tasks);
  try{if(navigator.share){await navigator.share({title:project.name,text:`Проект «${project.name}» в Taskflow`,url});setToast('Ссылка отправлена')}else{await navigator.clipboard.writeText(url);setToast('Ссылка на проект скопирована')}}catch(error){if(error instanceof DOMException&&error.name==='AbortError')return;try{const field=document.createElement('textarea');field.value=url;field.style.position='fixed';field.style.opacity='0';document.body.append(field);field.select();document.execCommand('copy');field.remove();setToast('Ссылка на проект скопирована')}catch{setToast('Не удалось скопировать ссылку')}}
 }
 let content;
 switch(screen.type){
  case 'today':content=<Today data={data} onTasks={setTasks} onOpen={open} onToggle={toggle} onNew={()=>navigate({type:'new'})} onSettings={()=>navigate({type:'settings'})}/>;break;
  case 'projects':content=<Projects data={data} onOpen={id=>navigate({type:'project',id})} onAdd={name=>setData(current=>({...current,projects:[...current.projects,{id:crypto.randomUUID(),name}]}))} onShare={id=>void shareProject(id)}/>;break;
  case 'project':content=<ProjectScreen id={screen.id} data={data} onBack={back} onNew={()=>navigate({type:'new',project:screen.id})} onOpen={open} onTasks={setTasks} onToggle={toggle} onShare={id=>void shareProject(id)}/>;break;
  case 'shared':content=<SharedProjectScreen snapshot={screen.snapshot} onBack={back}/>;break;
  case 'new':content=<NewTask projects={data.projects} project={screen.project} onBack={back} onCreate={task=>{setData(current=>({...current,tasks:[...current.tasks,task]}));back()}}/>;break;
  case 'detail':{const task=data.tasks.find(item=>item.id===screen.id);content=<TaskDetail task={task} project={projectName(task?.project||'')} onBack={back} onUpdate={update} onToggle={()=>toggle(screen.id)}/>;break}
  case 'inbox':content=<Inbox notices={data.notices} onRead={id=>setData(current=>({...current,notices:current.notices.map(notice=>notice.id===id?{...notice,read:true}:notice)}))}/>;break;
  case 'settings':content=<Settings data={data} onBack={back}/>;break;
 }
 const nav=screen.type==='project'||screen.type==='shared'?'projects':screen.type;
 return <div id="app">{error&&<div className="storage-warning" role="alert">Не удалось сохранить данные. Скачайте резервную копию в настройках.</div>}<header className="top"><span className="brand">TASKFLOW</span><button className="slash-trigger" onClick={()=>setPalette(true)} aria-label="Открыть быстрый переход"><kbd>/</kbd><span>Быстрый переход</span></button><button className="icon" onClick={()=>navigate({type:'settings'})} aria-label="Настройки"><SettingsIcon size={19}/></button></header><div className="layout"><nav aria-label="Основная навигация">{([{id:'today',label:'Сегодня',icon:CalendarDays},{id:'projects',label:'Проекты',icon:Folder},{id:'inbox',label:'Входящие',icon:InboxIcon}] as const).map(item=><button key={item.id} className={nav===item.id?'active':''} aria-current={nav===item.id?'page':undefined} onClick={()=>navigate({type:item.id})}><span><item.icon size={21}/></span>{item.label}{item.id==='inbox'&&data.notices.some(notice=>!notice.read)&&<i className="unread-dot"/>}</button>)}</nav><main ref={mainRef} tabIndex={-1}>{content}</main></div><CommandPalette open={palette} onClose={()=>setPalette(false)} onNavigate={navigate} projects={data.projects}/><div className={`toast ${toast?'visible':''}`} role="status" aria-live="polite">{toast}</div></div>
}
