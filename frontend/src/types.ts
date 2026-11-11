export type Status = 'Запланировано' | 'В работе' | 'Готово';
export const statuses: Status[] = ['Запланировано', 'В работе', 'Готово'];
export interface User {id:string;telegramId:string;username?:string|null;firstName:string;lastName:string;name:string;photoUrl?:string|null;role?:'owner'|'member'}
export interface Task {id:string;title:string;project:string;done:boolean;status:Status;due:string;time:string;priority:string;description:string;assigneeId:string;checklist:{text:string;done:boolean}[]}
export interface Project {id:string;name:string;ownerId:string;joinEnabled:boolean;memberCount:number;members:User[]}
export interface Notice {id:string;title:string;text:string;read:boolean;inviteCode?:string}
export interface Store {user:User;tasks:Task[];projects:Project[];notices:Notice[]}
export interface Invite {id:string;code:string;url:string;projectName:string}
export type Screen = {type:'today'}|{type:'projects'}|{type:'project';id:string}|{type:'detail';id:string}|{type:'new';project?:string}|{type:'join';code:string}|{type:'inbox'}|{type:'settings'};
