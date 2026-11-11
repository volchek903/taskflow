import type {ReactNode} from 'react';
import {ArrowLeft} from 'lucide-react';
import type {User} from '../types';
export function Heading({title,subtitle,action}:{title:string;subtitle?:string;action?:ReactNode}){return <div className="heading"><div><h1>{title}</h1>{subtitle&&<small>{subtitle}</small>}</div>{action}</div>}
export function Tabs<T extends string>({items,value,onChange}:{items:T[];value:T;onChange:(value:T)=>void}){return <div className="tabs" role="tablist">{items.map(item=><button key={item} role="tab" aria-selected={value===item} className={item===value?'active':''} onClick={()=>onChange(item)}>{item}</button>)}</div>}
export function Back({onClick,label='Назад'}:{onClick:()=>void;label?:string}){return <button className="back" onClick={onClick}><ArrowLeft size={16}/>{label}</button>}
export function Empty({children}:{children:ReactNode}){return <div className="empty">{children}</div>}
export function UserAvatar({user,size=34}:{user:User;size?:number}){const initials=`${user.firstName?.[0]||''}${user.lastName?.[0]||''}`.toUpperCase()||'?';return user.photoUrl?<img className="user-avatar" src={user.photoUrl} width={size} height={size} alt={user.name}/>:<span className="user-avatar fallback" style={{width:size,height:size}} aria-label={user.name}>{initials}</span>}
