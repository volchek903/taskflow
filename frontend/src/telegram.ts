interface TelegramApp {initData:string;version:string;ready():void;expand():void;setHeaderColor(color:string):void;setBackgroundColor(color:string):void;setBottomBarColor?(color:string):void;BackButton:{show():void;hide():void;onClick(fn:()=>void):void;offClick(fn:()=>void):void};HapticFeedback?:{impactOccurred(style:'light'):void}}
declare global {interface Window {Telegram?:{WebApp:TelegramApp}}}
export const telegram=()=>window.Telegram?.WebApp.initData?window.Telegram.WebApp:undefined;
