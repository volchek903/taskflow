import {useEffect,useId,useLayoutEffect,useRef,useState,type KeyboardEvent} from 'react';
import {createPortal} from 'react-dom';
import {Check,ChevronDown} from 'lucide-react';

interface Option {value:string;label:string}
interface Props {
 id?:string;name?:string;value?:string;defaultValue?:string;options:Option[];
 onChange?:(value:string)=>void;disabled?:boolean;className?:string;'aria-label'?:string;
}

export function Select({id,name,value,defaultValue,options,onChange,disabled,className='',...aria}:Props){
 const generatedId=useId();const triggerId=id||generatedId;const listId=`${generatedId}-list`;
 const [internal,setInternal]=useState(defaultValue??options[0]?.value??'');
 const selected=value??internal;const selectedIndex=options.findIndex(option=>option.value===selected);
 const [open,setOpen]=useState(false);const [active,setActive]=useState(0);
 const [position,setPosition]=useState({top:0,left:0,width:0,maxHeight:288});
 const trigger=useRef<HTMLButtonElement>(null);const menu=useRef<HTMLDivElement>(null);
 const search=useRef({text:'',time:0});
 const expanded=open&&!disabled;
 function show(index=selectedIndex){setActive(Math.max(0,index));setOpen(true)}
 function choose(index:number){const option=options[index];if(!option)return;setInternal(option.value);onChange?.(option.value);setOpen(false);trigger.current?.focus()}
 useLayoutEffect(()=>{
  if(!expanded)return;
  function place(){
   const rect=trigger.current?.getBoundingClientRect();if(!rect)return;
   const viewport=window.visualViewport;const top=viewport?.offsetTop??0;const height=viewport?.height??window.innerHeight;
   const width=Math.min(rect.width,window.innerWidth-16);const below=top+height-rect.bottom-14;const above=rect.top-top-14;
   const upwards=below<Math.min(288,options.length*44+14)&&above>below;
   const maxHeight=Math.max(0,Math.min(288,upwards?above:below));
   const menuHeight=Math.min(maxHeight,options.length*44+14);
   setPosition({top:upwards?rect.top-menuHeight-6:rect.bottom+6,left:Math.max(8,Math.min(rect.left,window.innerWidth-width-8)),width,maxHeight});
  }
  place();window.addEventListener('resize',place);window.addEventListener('scroll',place,true);window.visualViewport?.addEventListener('resize',place);
  return()=>{window.removeEventListener('resize',place);window.removeEventListener('scroll',place,true);window.visualViewport?.removeEventListener('resize',place)};
 },[expanded,options.length]);
 useEffect(()=>{
  if(!expanded)return;
  function outside(event:PointerEvent){if(!trigger.current?.contains(event.target as Node)&&!menu.current?.contains(event.target as Node))setOpen(false)}
  document.addEventListener('pointerdown',outside);return()=>document.removeEventListener('pointerdown',outside);
 },[expanded]);
 useEffect(()=>{if(expanded)menu.current?.querySelector('[data-active="true"]')?.scrollIntoView({block:'nearest'})},[active,expanded]);
 function keyDown(event:KeyboardEvent<HTMLButtonElement>){
  if(event.key==='Tab'){setOpen(false);return}
  if(event.key==='Escape'){event.preventDefault();setOpen(false);return}
  if(['ArrowDown','ArrowUp','Home','End'].includes(event.key)){
   event.preventDefault();
   const next=event.key==='Home'?0:event.key==='End'?options.length-1:!expanded?Math.max(0,selectedIndex):(active+(event.key==='ArrowDown'?1:-1)+options.length)%options.length;
   show(next);return;
  }
  if(event.key==='Enter'||event.key===' '){event.preventDefault();if(expanded)choose(active);else show();return}
  if(event.key.length===1&&!event.ctrlKey&&!event.metaKey&&!event.altKey){
   event.preventDefault();const now=Date.now();const text=(now-search.current.time<600?search.current.text:'')+event.key.toLocaleLowerCase();search.current={text,time:now};
   const index=options.findIndex(option=>option.label.toLocaleLowerCase().startsWith(text));if(index>=0)show(index);
  }
 }
 return <div className={`custom-select ${className}`}>
  {name&&<input type="hidden" name={name} value={selected} disabled={disabled}/>}
  <button ref={trigger} id={triggerId} type="button" className="select-trigger" role="combobox" aria-label={aria['aria-label']} aria-haspopup="listbox" aria-expanded={expanded} aria-controls={expanded?listId:undefined} aria-activedescendant={expanded?`${listId}-${active}`:undefined} disabled={disabled||!options.length} onClick={()=>expanded?setOpen(false):show()} onKeyDown={keyDown} onBlur={()=>setOpen(false)}>
   <span>{options[selectedIndex]?.label||'Выберите значение'}</span><ChevronDown size={17} aria-hidden="true"/>
  </button>
  {expanded&&createPortal(<div ref={menu} id={listId} role="listbox" aria-label={aria['aria-label']||trigger.current?.labels?.[0]?.textContent||'Варианты'} className="select-menu" style={position} onMouseDown={event=>event.preventDefault()}>
   {options.map((option,index)=><div key={option.value} id={`${listId}-${index}`} role="option" aria-selected={option.value===selected} data-active={index===active} className="select-option" onPointerMove={()=>setActive(index)} onClick={()=>choose(index)}><span>{option.label}</span>{option.value===selected&&<Check size={17} aria-hidden="true"/>}</div>)}
  </div>,document.body)}
 </div>
}
