export type Status = string;
const defaultStatuses = ['Запланировано', 'В работе', 'Готово'];
export function getProjectStatuses(project?:{statuses?:string[]|null}):string[]{
 return Array.isArray(project?.statuses)&&project.statuses.length?project.statuses:defaultStatuses;
}
export type Role = 'admin'|'member'|'viewer';
export const roleNames = {owner:'Владелец',admin:'Администратор',member:'Участник',viewer:'Наблюдатель'};
export interface User {id:string;telegramId:string;username?:string|null;firstName:string;lastName:string;name:string;photoUrl?:string|null;role?:'owner'|Role}
export interface Task {id:string;title:string;project:string;done:boolean;status:Status;due:string;time:string;priority:string;description:string;assigneeId:string;checklist:{text:string;done:boolean}[]}
export interface Project {id:string;name:string;ownerId:string;joinEnabled:boolean;statuses:string[];memberCount:number;members:User[]}
export interface Notice {id:string;title:string;text:string;read:boolean;role?:Role;inviteCode?:string}
export interface Store {user:User;tasks:Task[];projects:Project[];notices:Notice[]}
export interface Invite {id:string;code:string;url:string;projectName:string;role?:Role}
export type Screen = {type:'today'}|{type:'projects'}|{type:'project';id:string}|{type:'detail';id:string}|{type:'new';project?:string}|{type:'join';code:string}|{type:'inbox'}|{type:'settings'};
