import {useState} from 'react';
import {Check,ChevronRight,Folder,Plus,Share2,ShieldCheck} from 'lucide-react';
import {Heading,Empty,Back,Tabs} from '../components/UI';
import {TaskDragList} from '../components/TaskDragList';
import {statuses,type SharedProject,type Store,type Task} from '../types';

export function Projects({data,onOpen,onAdd,onShare}:{data:Store;onOpen:(id:string)=>void;onAdd:(name:string)=>void;onShare:(id:string)=>void}){
 const [search,setSearch]=useState('');const [adding,setAdding]=useState(false);const [name,setName]=useState('');
 const projects=data.projects.filter(project=>project.name.toLowerCase().includes(search.toLowerCase()));
 return <>
  <Heading title="Проекты" subtitle="От больших планов к маленьким шагам" action={<button className="icon" onClick={()=>setAdding(value=>!value)} aria-label={adding?'Закрыть форму':'Добавить проект'}><Plus/></button>}/>
  {adding&&<form className="inline-form project-create" onSubmit={event=>{event.preventDefault();if(name.trim()){onAdd(name.trim());setName('');setAdding(false)}}}>
   <div><strong>Новый проект</strong><small>Создайте пространство для связанных задач</small></div>
   <label htmlFor="project-name">Название проекта</label><input id="project-name" value={name} onChange={event=>setName(event.target.value)} autoFocus required maxLength={100} placeholder="Например, Запуск сайта"/>
   <button className="primary wide">Создать проект</button>
  </form>}
  <label className="sr-only" htmlFor="project-search">Поиск проекта</label><input id="project-search" className="search" value={search} onChange={event=>setSearch(event.target.value)} placeholder="Поиск проекта"/>
  <div className="project-list">{projects.map(project=>{const tasks=data.tasks.filter(task=>task.project===project.id),done=tasks.filter(task=>task.done).length;return <article key={project.id} className="card project">
   <button className="project-open" onClick={()=>onOpen(project.id)}>
    <div className="project-title"><Folder size={20}/><strong>{project.name}</strong><ChevronRight size={17}/></div>
    <span className="meta">{done} из {tasks.length} задач выполнено</span><div className="track"><i style={{width:`${tasks.length?done/tasks.length*100:0}%`}}/></div>
   </button>
   <button className="share-action" onClick={()=>onShare(project.id)} aria-label={`Поделиться проектом ${project.name}`}><Share2 size={17}/>Поделиться</button>
  </article>})}{!projects.length&&<Empty>Проекты не найдены</Empty>}</div>
 </>
}

export function ProjectScreen({id,data,onBack,onNew,onOpen,onToggle,onTasks,onShare}:{id:string;data:Store;onBack:()=>void;onNew:()=>void;onOpen:(id:string)=>void;onToggle:(id:string)=>void;onTasks:(tasks:Task[])=>void;onShare:(id:string)=>void}){
 const [tab,setTab]=useState('Список');const tasks=data.tasks.filter(task=>task.project===id);const project=data.projects.find(item=>item.id===id);
 const groups=tab==='Доска'?statuses.map(status=>({id:status,title:status,tasks:tasks.filter(task=>task.status===status),status})):[{id:'all',title:'Все задачи',tasks}];
 return <><Back onClick={onBack} label="Все проекты"/><div className="project-heading"><Heading title={project?.name||'Проект'} subtitle={`${tasks.length} задач`} action={<button className="icon" onClick={onNew} aria-label="Создать задачу"><Plus/></button>}/><button className="subtle share-project" onClick={()=>onShare(id)}><Share2 size={17}/>Поделиться проектом</button></div><Tabs items={['Список','Доска']} value={tab} onChange={setTab}/><TaskDragList key={tab} board={tab==='Доска'} groups={groups} allTasks={data.tasks} onChange={onTasks} onOpen={onOpen} onToggle={onToggle} projectName={projectId=>data.projects.find(item=>item.id===projectId)?.name||'Без проекта'}/></>
}

export function SharedProjectScreen({snapshot,onBack}:{snapshot:SharedProject;onBack:()=>void}){
 const [expanded,setExpanded]=useState<string|null>(null);const done=snapshot.tasks.filter(task=>task.done).length;
 return <><Back onClick={onBack} label="В Taskflow"/><div className="shared-banner"><ShieldCheck size={20}/><div><strong>Проект открыт по ссылке</strong><small>Режим просмотра · изменения доступны только владельцу</small></div></div><Heading title={snapshot.project.name} subtitle={`${done} из ${snapshot.tasks.length} задач выполнено`}/><div className="track shared-progress"><i style={{width:`${snapshot.tasks.length?done/snapshot.tasks.length*100:0}%`}}/></div><section className="shared-tasks" aria-label="Задачи общего проекта"><h2>Задачи</h2>{snapshot.tasks.map(task=><article key={task.id} className={`card shared-task ${task.done?'is-done':''}`}><button className="shared-task-main" onClick={()=>setExpanded(value=>value===task.id?null:task.id)} aria-expanded={expanded===task.id}><span className="readonly-check">{task.done&&<Check size={15}/>}</span><span><strong>{task.title}</strong><small>{task.status} · {task.priority}{task.due?` · ${new Date(task.due+'T12:00:00').toLocaleDateString('ru',{day:'numeric',month:'short'})}`:''}</small></span><ChevronRight className={expanded===task.id?'rotated':''} size={17}/></button>{expanded===task.id&&<div className="shared-task-details">{task.description&&<p>{task.description}</p>}{task.checklist.length>0&&<ul>{task.checklist.map((item,index)=><li key={index} className={item.done?'done-text':''}>{item.done?'✓':'○'} {item.text}</li>)}</ul>}{!task.description&&!task.checklist.length&&<p className="muted">У задачи нет дополнительного описания.</p>}</div>}</article>)}{!snapshot.tasks.length&&<Empty>В этом проекте пока нет задач</Empty>}</section><p className="shared-date">Снимок проекта создан {new Date(snapshot.sharedAt).toLocaleString('ru',{dateStyle:'medium',timeStyle:'short'})}</p></>
}
