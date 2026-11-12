import {useCallback,useEffect,useState} from 'react';
import {api} from '../api';
import type {Invite,Store,Task,Role} from '../types';
export const localDate=(date=new Date())=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
const empty:Store={user:{id:'',telegramId:'',firstName:'',lastName:'',name:'Пользователь'},projects:[],tasks:[],notices:[]};
export function useStore(){
 const [data,setData]=useState<Store>(empty);const [loading,setLoading]=useState(true);const [error,setError]=useState('');
 const reload=useCallback(async()=>{try{setError('');setData(await api<Store>('/bootstrap'))}catch(value){setError(value instanceof Error?value.message:'Не удалось загрузить данные')}finally{setLoading(false)}},[]);
 useEffect(()=>{void reload();const timer=window.setInterval(()=>{if(document.visibilityState==='visible')void reload()},30000);const refresh=()=>{if(document.visibilityState==='visible')void reload()};document.addEventListener('visibilitychange',refresh);return()=>{window.clearInterval(timer);document.removeEventListener('visibilitychange',refresh)}},[reload]);
 async function createProject(name:string){await api('/projects',{method:'POST',body:JSON.stringify({name})});await reload()}
 async function setJoinEnabled(id:string,joinEnabled:boolean){await api(`/projects/${id}`,{method:'PATCH',body:JSON.stringify({joinEnabled})});await reload()}
 async function createInvite(id:string,identifier?:string,role:Role="member"){return api<Invite>(`/projects/${id}/invites`,{method:'POST',body:JSON.stringify({identifier,role})})}
 async function joinProject(code:string){const result=await api<{projectId:string}>('/invites/join',{method:'POST',body:JSON.stringify({code})});await reload();return result.projectId}
 async function declineInvite(code:string){await api('/invites/decline',{method:'POST',body:JSON.stringify({code})});await reload()}
 async function setMember(id:string,identifier:string,role:Role){await api(`/projects/${id}/members`,{method:'POST',body:JSON.stringify({identifier,role})});await reload()}
 async function setStatuses(id:string,statuses:string[],renames:Record<string,string>){await api(`/projects/${id}`,{method:'PATCH',body:JSON.stringify({statuses,renames})});await reload()}
 async function createTask(task:Task){await api('/tasks',{method:'POST',body:JSON.stringify(task)});await reload()}
 async function updateTask(task:Task){setData(current=>({...current,tasks:current.tasks.map(item=>item.id===task.id?task:item)}));try{await api(`/tasks/${task.id}`,{method:'PATCH',body:JSON.stringify(task)})}catch(value){await reload();throw value}}
 async function reorderTasks(tasks:Task[]){setData(current=>({...current,tasks}));try{await api('/tasks/reorder',{method:'POST',body:JSON.stringify({tasks:tasks.filter(task=>data.projects.find(project=>project.id===task.project)?.members.find(member=>member.id===data.user.id)?.role!=='viewer').map((task,index)=>({id:task.id,status:task.status,done:task.done,position:index}))})})}catch(value){await reload();throw value}}
 return {data,loading,error,reload,actions:{declineInvite,setMember,setStatuses,createProject,setJoinEnabled,createInvite,joinProject,createTask,updateTask,reorderTasks}};
}
