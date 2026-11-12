import {useRef,useState,type CSSProperties} from 'react';
import {DndContext,DragOverlay,MouseSensor,TouchSensor,KeyboardSensor,useSensor,useSensors,useDroppable,closestCenter,pointerWithin,rectIntersection,MeasuringStrategy,type CollisionDetection,type DragEndEvent,type DragOverEvent,type DragStartEvent} from '@dnd-kit/core';
import {SortableContext,useSortable,verticalListSortingStrategy,sortableKeyboardCoordinates,arrayMove} from '@dnd-kit/sortable';
import {CSS} from '@dnd-kit/utilities';
import type {Task} from '../types';
import {TaskCard} from './TaskCard';
import {telegram} from '../telegram';
// First select the containing list, then a card inside that list. Include
// the active card's measured slot: excluding it makes neighbours oscillate
// when their transformed rectangles move under the pointer.
const taskCollision: CollisionDetection = args => {
 const containers=args.droppableContainers.filter(item=>String(item.id).startsWith('group:'));
 const containerArgs={...args,droppableContainers:containers};
 const hits=args.pointerCoordinates?pointerWithin(containerArgs):rectIntersection(containerArgs);
 const container=hits[0];
 if(!container)return [];
 const groupId=String(container.id).slice(6);
 const cards=args.droppableContainers.filter(item=>!String(item.id).startsWith('group:')&&item.data.current?.group===groupId);
 return cards.length?closestCenter({...args,droppableContainers:cards}):[container];
};
export interface TaskGroup {id:string;title:string;tasks:Task[];status?:Task['status'];done?:boolean}
interface Props {groups:TaskGroup[];board?:boolean;readOnly?:boolean;isReadOnly?:(task:Task)=>boolean;onChange:(tasks:Task[])=>void;allTasks:Task[];projectName:(id:string)=>string;onOpen:(id:string)=>void;onToggle:(id:string)=>void}
function SortableCard({task,group,props}:{task:Task;group:string;props:Props}){const {attributes,listeners,setNodeRef,transform,transition,isDragging}=useSortable({disabled:props.readOnly||props.isReadOnly?.(task),id:task.id,data:{group},transition:{duration:220,easing:'cubic-bezier(.2,.8,.2,1)'}});const style:CSSProperties={transform:CSS.Transform.toString(transform),transition,opacity:isDragging?.2:1};return <div ref={setNodeRef} style={style} {...attributes} {...listeners} className={`sortable-card ${isDragging?'is-dragging':''}`} aria-label={`Переместить: ${task.title}`}><TaskCard readOnly={props.readOnly||props.isReadOnly?.(task)} task={task} project={props.projectName(task.project)} board={props.board} onOpen={()=>props.onOpen(task.id)} onToggle={()=>props.onToggle(task.id)}/></div>}
function Group({group,tasks,props}:{group:TaskGroup;tasks:Task[];props:Props}){const {setNodeRef,isOver}=useDroppable({id:`group:${group.id}`,data:{group:group.id}});return <section ref={setNodeRef} className={`${props.board?'column':'task-group'} ${isOver?'drop-zone':''}`}><h2>{group.title}<small> · {tasks.length}</small></h2><SortableContext items={tasks.map(t=>t.id)} strategy={verticalListSortingStrategy}>{tasks.map(task=><SortableCard key={task.id} task={task} group={group.id} props={props}/>)}</SortableContext>{!tasks.length&&<div className="drop-empty">{props.board?'Перетащите задачу сюда':'Нет задач'}</div>}</section>}
export function TaskDragList(props:Props){const {groups,allTasks,onChange}=props;const [active,setActive]=useState<string|null>(null);const [preview,setPreview]=useState<Record<string,string[]>|null>(null);const previewRef=useRef<Record<string,string[]>|null>(null);const updatePreview=(value:Record<string,string[]>|null)=>{previewRef.current=value;setPreview(value)};const sensors=useSensors(useSensor(MouseSensor,{activationConstraint:{distance:7}}),useSensor(TouchSensor,{activationConstraint:{delay:220,tolerance:7}}),useSensor(KeyboardSensor,{coordinateGetter:sortableKeyboardCoordinates}));
 const initial=()=>Object.fromEntries(groups.map(g=>[g.id,g.tasks.map(t=>t.id)]));
 const reset=()=>{setActive(null);updatePreview(null)};
 const findGroup=(id:string,map:Record<string,string[]>)=>id.startsWith('group:')?id.slice(6):Object.keys(map).find(key=>map[key].includes(id));
 function start(event:DragStartEvent){setActive(String(event.active.id));updatePreview(initial());telegram()?.HapticFeedback?.impactOccurred('light')}
 function over(event:DragOverEvent){
  if(!event.over)return;
  const previous=previewRef.current;if(!previous)return;
  const activeId=String(event.active.id),overId=String(event.over.id);
  const from=findGroup(activeId,previous),to=findGroup(overId,previous);
  if(!from||!to||from===to)return;
  const overIndex=previous[to].indexOf(overId);
  const translated=event.active.rect.current.translated;
  const below=translated?translated.top>event.over.rect.top+event.over.rect.height:false;
  const index=overIndex<0?previous[to].length:overIndex+(below?1:0);
  updatePreview({...previous,[from]:previous[from].filter(id=>id!==activeId),[to]:[...previous[to].slice(0,index),activeId,...previous[to].slice(index)]});
 }
 function end(event:DragEndEvent){const preview=previewRef.current;if(!event.over||!preview){reset();return}const id=String(event.active.id),overId=String(event.over.id),group=findGroup(id,preview),to=findGroup(overId,preview);if(!group||!to){reset();return}let map={...preview};if(group===to&&!overId.startsWith('group:'))map[group]=arrayMove(map[group],map[group].indexOf(id),map[group].indexOf(overId));const visible=new Set(groups.flatMap(g=>g.tasks.map(t=>t.id)));const ordered=groups.flatMap(g=>map[g.id].map(taskId=>{const task=allTasks.find(t=>t.id===taskId)!;return {...task,...(g.status?{status:g.status}:g.done!==undefined?{done:g.done}:{})}}));let i=0;const result=allTasks.map(task=>visible.has(task.id)?ordered[i++]:task);onChange(result);reset()}
 const moving=allTasks.find(t=>t.id===active);
 return <DndContext sensors={sensors} collisionDetection={taskCollision} measuring={{droppable:{strategy:MeasuringStrategy.Always}}} onDragStart={start} onDragOver={over} onDragEnd={end} onDragCancel={reset}><div className={props.board?'board':'task-lists'}>{groups.map(group=><Group key={group.id} group={group} tasks={preview?preview[group.id].map(id=>allTasks.find(t=>t.id===id)!):group.tasks} props={props}/>)}</div><DragOverlay dropAnimation={{duration:180,easing:'ease-out'}}>{moving&&<TaskCard task={moving} board={props.board} project={props.projectName(moving.project)} onOpen={()=>{}} onToggle={()=>{}} overlay/>}</DragOverlay></DndContext>}
