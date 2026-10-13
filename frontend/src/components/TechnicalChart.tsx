import { useMemo, useRef, useState } from "react";
import type { HistoricalPrice, TechnicalAnalysis } from "../services/market";

type Props={data:HistoricalPrice[]; analysis:TechnicalAnalysis|null};
function finite(v:number|null):v is number{return v!=null&&Number.isFinite(v)}
function pathFor(values:(number|null)[],visible:HistoricalPrice[],width:number,height:number,min:number,max:number){
  const n=Math.max(visible.length-1,1), span=Math.max(max-min,1e-9);
  return values.map((v,i)=>v==null||!visible[i]?"":(i===0||values[i-1]==null?"M":"L")+" "+(i/n*width)+" "+(height-((v-min)/span)*height)).filter(Boolean).join(" ");
}
export default function TechnicalChart({data,analysis}:Props){
  const [zoom,setZoom]=useState(1),[offset,setOffset]=useState(0),[crosshair,setCrosshair]=useState<number|null>(null);
  const [showSma,setShowSma]=useState(true),[showEma,setShowEma]=useState(true);
  const drag=useRef<{x:number;offset:number}|null>(null);
  const width=1000,height=430,volumeHeight=80;
  const valid=data.filter(b=>finite(b.open)&&finite(b.high)&&finite(b.low)&&finite(b.close));
  const count=valid.length,windowSize=Math.max(25,Math.min(count,Math.floor(count/zoom)));
  const maxOffset=Math.max(0,count-windowSize),start=Math.min(Math.max(offset,0),maxOffset),visible=valid.slice(start,start+windowSize);
  const prices=visible.flatMap(b=>[b.low!,b.high!]),min=Math.min(...prices),max=Math.max(...prices),span=Math.max(max-min,.01);
  const y=(price:number)=>height-((price-min)/span)*height,x=(i:number)=>(i/Math.max(visible.length-1,1))*width;
  const volumeMax=Math.max(...visible.map(b=>b.volume??0),1);
  const sma=analysis?.indicators.sma20.slice(start,start+windowSize)??[],ema=analysis?.indicators.ema21.slice(start,start+windowSize)??[];
  const selected=crosshair==null?null:visible[crosshair];
  const label=useMemo(()=>selected?new Date(selected.timestamp).toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short"}):"Move over a candle",[selected]);
  return <div className="overflow-hidden rounded-xl border border-white/10 bg-slate-950/70">
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
      <span>{label}</span><span className="flex items-center gap-3 normal-case tracking-normal">
        <label><input type="checkbox" checked={showSma} onChange={e=>setShowSma(e.target.checked)} /> SMA 20</label>
        <label><input type="checkbox" checked={showEma} onChange={e=>setShowEma(e.target.checked)} /> EMA 21</label>
        <button type="button" onClick={()=>{setZoom(1);setOffset(0)}} className="rounded bg-white/5 px-2 py-1">Reset</button>
      </span>
    </div>
    <svg viewBox={"0 0 "+width+" "+(height+volumeHeight)} className="h-[520px] w-full touch-none select-none"
      onWheel={e=>{e.preventDefault();setZoom(z=>Math.max(1,Math.min(8,z*(e.deltaY<0?1.15:.87))))}}
      onPointerDown={e=>{drag.current={x:e.clientX,offset:start};(e.currentTarget as SVGElement).setPointerCapture(e.pointerId)}}
      onPointerMove={e=>{const rect=(e.currentTarget as SVGElement).getBoundingClientRect(),px=e.clientX-rect.left;setCrosshair(Math.max(0,Math.min(visible.length-1,Math.round((px/rect.width)*(visible.length-1)))));if(drag.current){const dx=e.clientX-drag.current.x,step=rect.width/Math.max(windowSize-1,1);setOffset(Math.max(0,Math.min(maxOffset,Math.round(drag.current.offset-dx/step))))}}}
      onPointerUp={()=>{drag.current=null}} onPointerLeave={()=>setCrosshair(null)}>
      <rect x="0" y="0" width={width} height={height} fill="transparent"/>
      {visible.map((b,i)=>{const xx=x(i),candleW=Math.max(2,width/Math.max(windowSize*1.8,1)),bullish=(b.close??0)>=(b.open??0);return <g key={b.timestamp+i}>
        <line x1={xx} x2={xx} y1={y(b.high!)} y2={y(b.low!)} stroke="currentColor" className={bullish?"text-emerald-300":"text-rose-300"} strokeWidth="1"/>
        <rect x={xx-candleW/2} y={Math.min(y(b.open!),y(b.close!))} width={candleW} height={Math.max(1,Math.abs(y(b.open!)-y(b.close!)))} className={bullish?"fill-emerald-300":"fill-rose-300"}/>
        {b.volume!=null&&<rect x={xx-candleW/2} y={height+volumeHeight-(b.volume/volumeMax)*volumeHeight} width={candleW} height={(b.volume/volumeMax)*volumeHeight} className="fill-slate-600/60"/>}
      </g>})}
      {showSma&&<path d={pathFor(sma,visible,width,height,min,max)} fill="none" stroke="currentColor" className="text-amber-300" strokeWidth="2"/>}
      {showEma&&<path d={pathFor(ema,visible,width,height,min,max)} fill="none" stroke="currentColor" className="text-sky-300" strokeWidth="2"/>}
      {crosshair!=null&&<line x1={x(crosshair)} x2={x(crosshair)} y1="0" y2={height+volumeHeight} stroke="currentColor" className="text-white/20" strokeDasharray="4 4"/>}
    </svg>
    <div className="flex justify-between border-t border-white/5 px-3 py-2 text-[10px] text-slate-600"><span>Drag to pan</span><span>Wheel to zoom · {count} candles</span></div>
    {selected&&<div className="grid grid-cols-5 gap-2 border-t border-white/5 px-3 py-2 text-[10px] font-semibold text-slate-400">{[["O",selected.open],["H",selected.high],["L",selected.low],["C",selected.close],["V",selected.volume]].map(([k,v])=><span key={String(k)}>{k} <b className="text-slate-200">{typeof v==="number"?v.toLocaleString("en-IN",{maximumFractionDigits:2}):"—"}</b></span>)}</div>}
  </div>
}
