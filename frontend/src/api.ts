import {telegram} from './telegram';
export class ApiError extends Error {constructor(message:string,public status:number){super(message)}}
export async function api<T>(path:string,options:RequestInit={}):Promise<T>{
 const initData=telegram()?.initData||'';const headers=new Headers(options.headers);headers.set('Content-Type','application/json');
 if(initData)headers.set('X-Telegram-Init-Data',initData);else if(['localhost','127.0.0.1'].includes(location.hostname))headers.set('X-Taskflow-Dev-User',localStorage.getItem('taskflow-dev-user')||'900000001');
 const response=await fetch(`/api${path}`,{...options,headers});let body:unknown={};try{body=await response.json()}catch{/* handled below */}
 if(!response.ok){const message=typeof body==='object'&&body&&'error'in body?String((body as {error:unknown}).error):`Ошибка сервера ${response.status}`;throw new ApiError(message,response.status)}return body as T;
}
