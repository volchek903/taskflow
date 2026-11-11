import type {Project,SharedProject,Task} from './types';

function toBase64Url(value:string){
 const bytes=new TextEncoder().encode(value);let binary='';
 for(const byte of bytes)binary+=String.fromCharCode(byte);
 return btoa(binary).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
}

function fromBase64Url(value:string){
 const base64=value.replaceAll('-','+').replaceAll('_','/').padEnd(Math.ceil(value.length/4)*4,'=');
 const binary=atob(base64),bytes=new Uint8Array(binary.length);
 for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);
 return new TextDecoder().decode(bytes);
}

export function projectShareUrl(project:Project,tasks:Task[]){
 const snapshot:SharedProject={version:1,project,tasks:tasks.filter(task=>task.project===project.id),sharedAt:new Date().toISOString()};
 return `${location.origin}${location.pathname}${sharedProjectHash(snapshot)}`;
}

export const sharedProjectHash=(snapshot:SharedProject)=>`#/shared/${toBase64Url(JSON.stringify(snapshot))}`;

export function readSharedProject(value:string):SharedProject|null{
 try{
  const snapshot=JSON.parse(fromBase64Url(value)) as SharedProject;
  if(snapshot.version!==1||typeof snapshot.project?.id!=='string'||typeof snapshot.project?.name!=='string'||!Array.isArray(snapshot.tasks))return null;
  if(!snapshot.tasks.every(task=>typeof task.id==='string'&&typeof task.title==='string'&&Array.isArray(task.checklist)))return null;
  return snapshot;
 }catch{return null}
}
