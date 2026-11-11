import {useCallback,useEffect,useState} from 'react';
import {api} from '../api';
import type {Invite,Store,Task} from '../types';
export const localDate=(date=new Date())=>`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
const empty:Store={user:{id:'',telegramId:'',firstName:'',lastName:'',name:'Пользователь'},projects:[],tasks:[],notices:[]};
export function useStore(){
 const [data,setData]=useState<Store>(empty);const [loading,setLoading]=useState(true);const [error,setError]=useState('');
 const reload=useCallback(async()=>{try{setError('');setData(await api<Store>('/bootstrap'))}catch(value){setError(value instanceof Error?value.message:'Не удалось загрузить данные')}finally{setLoading(false)}},[]);
 useEffect(()=>{void reload()},[reload]);
 async function createProject(name:string){await api('/projects',{method:'POST',body:JSON.stringify({name})});await reload()}
 async function setJoinEnabled(id:string,joinEnabled:boolean){await api(`/projects/${id}`,{method:'PATCH',body:JSON.stringify({joinEnabled})});await reload()}
 async function createInvite(id:string,identifier?:string){return api<Invite>(`/projects/${id}/invites`,{method:'POST',body:JSON.stringify({identifier})})}
 async function joinProject(code:string){const result=await api<{projectId:string}>('/invites/join',{method:'POST',body:JSON.stringify({code})});await reload();return result.projectId}
 async function createTask(task:Task){await api('/tasks',{method:'POST',body:JSON.stringify(task)});await reload()}
 async function updateTask(task:Task){setData(current=>({...current,tasks:current.tasks.map(item=>item.id===task.id?task:item)}));try{await api(`/tasks/${task.id}`,{method:'PATCH',body:JSON.stringify(task)})}catch(value){await reload();throw value}}
 async function reorderTasks(tasks:Task[]){setData(current=>({...current,tasks}));try{await api('/tasks/reorder',{method:'POST',body:JSON.stringify({tasks:tasks.map((task,index)=>({id:task.id,status:task.status,done:task.done,position:index}))})})}catch(value){await reload();throw value}}
 return {data,loading,error,reload,actions:{createProject,setJoinEnabled,createInvite,joinProject,createTask,updateTask,reorderTasks}};
}
