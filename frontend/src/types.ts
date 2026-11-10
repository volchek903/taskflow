export type Status = 'Запланировано' | 'В работе' | 'Готово';
export const statuses: Status[] = ['Запланировано', 'В работе', 'Готово'];
export interface Task { id:string; title:string; project:string; done:boolean; status:Status; due:string; time:string; priority:string; description:string; checklist:{text:string;done:boolean}[] }
export interface Project {id:string;name:string}
export interface Notice {id:string;title:string;text:string;read:boolean}
export interface Store {tasks:Task[];projects:Project[];notices:Notice[]}
export type Screen = {type:'today'}|{type:'projects'}|{type:'project';id:string}|{type:'detail';id:string}|{type:'new';project?:string}|{type:'inbox'}|{type:'settings'};
