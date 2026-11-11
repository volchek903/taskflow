import {useEffect,useMemo,useRef,useState} from 'react';
import {CalendarDays,Folder,Inbox,Search,Settings} from 'lucide-react';
import type {Project,Screen} from '../types';

interface Command {value:string;label:string;hint:string;icon:typeof Search;screen:Screen}

export function CommandPalette({open,onClose,onNavigate,projects}:{open:boolean;onClose:()=>void;onNavigate:(screen:Screen)=>void;projects:Project[]}){
 const [query,setQuery]=useState('/');const [active,setActive]=useState(0);const input=useRef<HTMLInputElement>(null);
 const commands=useMemo<Command[]>(()=>[
  {value:'/today',label:'Сегодня',hint:'Задачи на сегодня',icon:CalendarDays,screen:{type:'today'}},
  {value:'/projects',label:'Проекты',hint:'Все проекты',icon:Folder,screen:{type:'projects'}},
  {value:'/inbox',label:'Входящие',hint:'Уведомления',icon:Inbox,screen:{type:'inbox'}},
  {value:'/settings',label:'Настройки',hint:'Параметры приложения',icon:Settings,screen:{type:'settings'}},
  ...projects.map(project=>({value:`/project ${project.name}`,label:project.name,hint:'Открыть проект',icon:Folder,screen:{type:'project',id:project.id} as Screen}))
 ],[projects]);
 const normalized=query.toLowerCase().trim();
 const filtered=commands.filter(command=>`${command.value} ${command.label}`.toLowerCase().includes(normalized));
 useEffect(()=>{if(open){setQuery('/');setActive(0);requestAnimationFrame(()=>input.current?.focus())}},[open]);
 useEffect(()=>setActive(index=>Math.min(index,Math.max(filtered.length-1,0))),[filtered.length]);
 if(!open)return null;
 const choose=(command:Command)=>{onNavigate(command.screen);onClose()};
 return <div className="command-scrim" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget)onClose()}}>
  <section className="command-palette" role="dialog" aria-modal="true" aria-label="Быстрый переход">
   <div className="command-input"><Search size={19}/><input ref={input} value={query} onChange={event=>{setQuery(event.target.value.startsWith('/')?event.target.value:`/${event.target.value}`);setActive(0)}} onKeyDown={event=>{if(event.key==='Escape')onClose();if(event.key==='ArrowDown'){event.preventDefault();setActive(index=>Math.min(index+1,filtered.length-1))}if(event.key==='ArrowUp'){event.preventDefault();setActive(index=>Math.max(index-1,0))}if(event.key==='Enter'&&filtered[active])choose(filtered[active])}} aria-label="Введите slash-команду" placeholder="/projects"/>
    <kbd>Esc</kbd>
   </div>
   <div className="command-results" role="listbox" aria-label="Доступные команды">{filtered.map((command,index)=><button key={command.value} role="option" aria-selected={index===active} className={index===active?'active':''} onMouseEnter={()=>setActive(index)} onClick={()=>choose(command)}><command.icon size={18}/><span><strong>{command.value}</strong><small>{command.hint}</small></span></button>)}{!filtered.length&&<p className="command-empty">Команда не найдена</p>}</div>
   <footer><span><kbd>↑</kbd><kbd>↓</kbd> выбор</span><span><kbd>Enter</kbd> перейти</span></footer>
  </section>
 </div>
}
