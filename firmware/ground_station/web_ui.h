// Phone control page served by the ground station at http://192.168.4.1
// Left pad: amplitude ("throttle", drag up/down, stays where you leave it).
// Right pad: steering (drag left/right from where you touch, springs back to centre).
// HẠ CÁNH: the butterfly flies its auto-landing sequence; it also starts by itself when the
// page goes to the background or loses the station while flapping. Tap again to take control back.
// The page mixes throttle + steering into per-wing amplitude and polls /c every 50 ms;
// the reply carries the butterfly telemetry. Settings are kept in the phone (localStorage).
#pragma once

static const char PAGE[] = R"HTML(<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#101418">
<title>Butterfly RC</title>
<style>
:root{--bg:#101418;--panel:#1b2128;--line:#2a323b;--fg:#e8eef3;--mut:#8a97a3;--acc:#f59e0b;--ok:#22c55e;--bad:#ef4444}
*{box-sizing:border-box;-webkit-user-select:none;user-select:none;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;background:var(--bg);color:var(--fg);font:15px system-ui,-apple-system,sans-serif;overflow:hidden;touch-action:none;overscroll-behavior:none}
button{font:inherit;color:inherit}
#bar{display:flex;gap:8px;align-items:center;padding:6px 10px;height:54px}
.pill{background:var(--panel);border-radius:8px;padding:7px 10px;white-space:nowrap;font-size:14px}
.ok{color:var(--ok)}.bad{color:var(--bad)}.mut{color:var(--mut)}
#arm{margin-left:auto;font-weight:700;border:0;border-radius:10px;padding:0 22px;height:42px;font-size:16px;background:#374151}
#arm.on{background:var(--bad)}
#land{font-weight:700;border:0;border-radius:10px;padding:0 16px;height:42px;font-size:15px;background:#374151}
#land.on{background:var(--acc);color:#111}
#land:disabled{opacity:.35}
#mode{display:none;color:#111;background:var(--acc);font-weight:700;font-size:17px}
body.landing .pad{opacity:.35}
#gear{border:0;background:var(--panel);border-radius:10px;height:42px;width:46px;font-size:20px}
#main{display:flex;gap:10px;padding:0 10px 10px;height:calc(100% - 54px)}
.pad{position:relative;background:var(--panel);border-radius:14px;touch-action:none;overflow:hidden;border:1px solid var(--line)}
#thr{width:28%}#ste{width:40%}
#mid{flex:1;display:flex;flex-direction:column;gap:10px;justify-content:center;align-items:stretch}
.fill{position:absolute;left:0;right:0;bottom:0;background:rgba(245,158,11,.30)}
.knob{position:absolute;top:0;bottom:0;width:8px;margin-left:-4px;left:50%;background:var(--acc);border-radius:4px}
.ctr{position:absolute;top:0;bottom:0;left:50%;border-left:1px dashed var(--line)}
.lbl{position:absolute;top:8px;left:12px;color:var(--mut);font-size:13px}
.big{position:absolute;bottom:12px;left:0;right:0;text-align:center;font-size:30px;font-weight:700;pointer-events:none}
#steV{bottom:auto;top:34px}
.box{background:var(--panel);border-radius:12px;padding:10px;text-align:center;border:1px solid var(--line)}
.row{display:flex;align-items:center;justify-content:space-between;gap:8px}
.step{border:0;background:#2a323b;border-radius:8px;width:48px;height:44px;font-size:22px}
.num{font-size:24px;font-weight:700}
#msg{position:fixed;left:50%;top:64px;transform:translateX(-50%);background:var(--bad);padding:8px 14px;border-radius:8px;display:none;z-index:5}
#set{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;align-items:center;justify-content:center;z-index:9}
#set .card{background:var(--panel);border-radius:14px;padding:14px 16px;width:min(420px,92vw);max-height:92vh;overflow:auto;touch-action:pan-y}
#set label{display:flex;justify-content:space-between;align-items:center;padding:6px 0;gap:10px}
#set input[type=number]{width:90px;font-size:16px;padding:6px;background:#0f1317;color:var(--fg);border:1px solid var(--line);border-radius:6px}
#set .hint{color:var(--mut);font-size:12px;margin:2px 0 8px}
#set button{border:0;border-radius:8px;padding:10px 16px;background:#2a323b;margin-top:8px}
@media (orientation:portrait){#main{flex-direction:column}#thr,#ste{width:auto;flex:1}#mid{flex:0 0 auto}}
</style></head><body>
<div id="bar">
  <span class="pill" id="stn">Trạm: …</span>
  <span class="pill" id="lnk">Bướm: …</span>
  <span class="pill" id="bat">Pin: –</span>
  <button id="gear" aria-label="Cài đặt">⚙</button>
  <button id="land" disabled>HẠ CÁNH</button>
  <button id="arm">BẬT VỖ</button>
</div>
<div id="main">
  <div class="pad" id="thr"><div class="fill" id="thrF" style="height:0"></div>
    <div class="lbl">Biên độ (ga) · kéo lên/xuống</div><div class="big" id="thrV">0°</div></div>
  <div id="mid">
    <div class="box" id="mode"></div>
    <div class="box"><div class="mut">Tần số vỗ</div>
      <div class="row"><button class="step" id="fM">−</button><span class="num" id="fV">2.5 Hz</span><button class="step" id="fP">+</button></div></div>
    <div class="box"><div class="row"><span class="mut">Trái</span><span class="num" id="aL">0°</span>
      <span class="num" id="aR">0°</span><span class="mut">Phải</span></div></div>
  </div>
  <div class="pad" id="ste"><div class="ctr"></div><div class="knob" id="steK"></div>
    <div class="lbl">Lái · kéo trái/phải</div><div class="big" id="steV">0</div></div>
</div>
<div id="msg"></div>
<div id="set"><div class="card">
  <b>Cài đặt</b> <span class="mut">(lưu trong điện thoại)</span>
  <label>Biên độ tối đa (°)<input type="number" id="s_maxAmp" step="1" min="5" max="35"></label>
  <label>Lệch biên độ khi lái tối đa (°)<input type="number" id="s_steer" step="0.5" min="0" max="10"></label>
  <div class="hint">Mô phỏng: lệch chỉ 1° đã làm bướm nghiêng 32° sau 2,4 s. Bắt đầu với 2–3°.</div>
  <label>Góc lượn / nhị diện (°)<input type="number" id="s_glide" step="0.5" min="-15" max="15"></label>
  <div class="hint">Tâm hành trình của cả 2 cánh, + là cánh nâng lên. Khi tắt vỗ hoặc mất sóng, cánh dừng ở góc này.</div>
  <label>Trim cánh phải (°)<input type="number" id="s_trimR" step="0.5" min="-10" max="10"></label>
  <label>Trim cánh trái (°)<input type="number" id="s_trimL" step="0.5" min="-10" max="10"></label>
  <div class="hint">Chỉnh để 2 cánh nằm đúng ngang khi tắt vỗ.</div>
  <label>Đảo chiều lái<input type="checkbox" id="s_rev"></label>
  <b>Tự hạ cánh</b>
  <label>Vỗ nhẹ khi hạ (°)<input type="number" id="s_landAmp" step="0.5" min="0" max="8"></label>
  <label>Thời gian vỗ nhẹ (s)<input type="number" id="s_landTime" step="1" min="0" max="120"></label>
  <div class="hint">Mất sóng quá 0,5 s, hoặc bấm HẠ CÁNH: vỗ giảm dần (10°/s) rồi giữ 2 cánh yên lượn xuống; 30 s sau, nếu vẫn mất sóng, servo thả lỏng. Mặc định 0° = lượn luôn. Mô phỏng: ±10° đã giữ được độ cao, nên vỗ nhẹ bị giới hạn 8° và chỉ giảm tốc độ chìm một chút.</div>
  <div class="row"><button id="sReset">Mặc định</button><button id="sClose">Xong</button></div>
</div></div>
<script>
const $=id=>document.getElementById(id);
const D={maxAmp:30,steer:3,glide:0,trimR:0,trimL:0,rev:false,freq:2.5,landAmp:0,landTime:20};
let S=Object.assign({},D);
try{Object.assign(S,JSON.parse(localStorage.getItem('bfly')||'{}'))}catch(e){}
const save=()=>{try{localStorage.setItem('bfly',JSON.stringify(S))}catch(e){}};
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
let thr=0,ste=0,armed=false,land=false,lastOk=0,busy=false;

function flash(t){const m=$('msg');m.textContent=t;m.style.display='block';clearTimeout(flash.t);flash.t=setTimeout(()=>m.style.display='none',1800)}

function drag(el,onMove,onEnd){
  let id=null,x0=0,y0=0,ctx=null;
  el.addEventListener('pointerdown',e=>{if(id!==null)return;id=e.pointerId;try{el.setPointerCapture(id)}catch(_){}x0=e.clientX;y0=e.clientY;ctx=onMove(0,0,null);e.preventDefault()});
  el.addEventListener('pointermove',e=>{if(e.pointerId!==id)return;onMove(e.clientX-x0,e.clientY-y0,ctx)});
  const up=e=>{if(e.pointerId!==id)return;id=null;onEnd&&onEnd()};
  el.addEventListener('pointerup',up);el.addEventListener('pointercancel',up);
}
// throttle: relative drag, a full pad height = 0..100 %
drag($('thr'),(dx,dy,c)=>{if(c===null)return thr;thr=clamp(c-dy/$('thr').clientHeight,0,1);draw();return c});
// steering: relative to the touch point, 40 % of the pad width = full deflection
drag($('ste'),(dx,dy,c)=>{if(c===null)return 0;ste=clamp(dx/($('ste').clientWidth*0.4),-1,1);draw();return c},()=>{ste=0;draw()});

function mix(){
  const base=thr*S.maxAmp, st=(S.rev?-1:1)*ste, d=st*Math.min(S.steer,base);
  // steer right -> left wing flaps harder, right wing less
  return {aL:base+d,aR:base-d,oR:S.glide+S.trimR,oL:S.glide+S.trimL};
}
function draw(){
  const m=mix();
  $('thrF').style.height=(thr*100)+'%';$('thrV').textContent=(thr*S.maxAmp).toFixed(0)+'°';
  $('steK').style.left=(50+ste*45)+'%';$('steV').textContent=(ste*100).toFixed(0);
  const aL=land?S.landAmp:m.aL,aR=land?S.landAmp:m.aR;
  $('aL').textContent=aL.toFixed(land?1:0)+'°';$('aR').textContent=aR.toFixed(land?1:0)+'°';
  $('fV').textContent=S.freq.toFixed(1)+' Hz';
  const a=$('arm');a.classList.toggle('on',armed);a.textContent=armed?'TẮT VỖ':'BẬT VỖ';
  const l=$('land');l.disabled=!armed;l.classList.toggle('on',land);l.textContent=land?'HỦY HẠ CÁNH':'HẠ CÁNH';
  document.body.classList.toggle('landing',land);
}
function autoLand(why){if(armed&&!land){land=true;draw();flash(why)}}
$('arm').onclick=()=>{
  if(!armed&&thr>0.03){flash('Hạ ga về 0 trước khi bật vỗ');return}
  armed=!armed;land=false;draw();
};
$('land').onclick=()=>{if(armed){land=!land;draw()}};
$('fM').onclick=()=>{S.freq=Math.round(clamp(S.freq-0.1,1.0,4.0)*10)/10;save();draw()};
$('fP').onclick=()=>{S.freq=Math.round(clamp(S.freq+0.1,1.0,4.0)*10)/10;save();draw()};
document.addEventListener('visibilitychange',()=>{if(document.hidden)autoLand('Đã rời trang: bướm tự hạ cánh')});

const keys=['maxAmp','steer','glide','trimR','trimL','landAmp','landTime'];
function openSet(){keys.forEach(k=>$('s_'+k).value=S[k]);$('s_rev').checked=S.rev;$('set').style.display='flex'}
function readSet(){
  keys.forEach(k=>{const el=$('s_'+k),v=parseFloat(el.value);if(!isNaN(v))S[k]=clamp(v,+el.min,+el.max)});
  S.rev=$('s_rev').checked;save();draw();
}
$('gear').onclick=openSet;
$('set').addEventListener('input',readSet);
$('sClose').onclick=()=>{readSet();$('set').style.display='none'};
$('sReset').onclick=()=>{const f=S.freq;S=Object.assign({},D,{freq:f});save();openSet();draw()};

function show(j){
  $('stn').innerHTML=j.r?'<span class="ok">Trạm OK</span>':'<span class="bad">Trạm: lỗi NRF24</span>';
  $('lnk').innerHTML=j.l?'<span class="ok">Bướm '+j.q+'%</span>'+(j.fs?' <span class="mut">mất sóng '+j.fs+'×</span>':'')
                        :'<span class="bad">Bướm: MẤT SÓNG</span>';
  if(j.v>0){const v=j.v/1000;$('bat').innerHTML='<span class="'+(j.fl&2?'bad':'ok')+'">'+v.toFixed(2)+' V</span> <span class="mut">'+(v/2).toFixed(2)+'/cell</span>'}
  else $('bat').innerHTML='<span class="mut">Pin: –</span>';
  const M=['','Tự hạ cánh: vỗ nhẹ ','Tự hạ cánh: lượn ','Đã hạ cánh, servo nghỉ '],md=$('mode');
  if(j.l&&j.m){md.textContent=M[j.m]+j.ls+' s';md.style.display='block'}else md.style.display='none';
}
async function tick(){
  if(busy)return;busy=true;
  const m=mix(),r=x=>Math.round(x*10);
  const q='/c?a='+(armed?1:0)+'&l='+(land?1:0)+'&f='+r(S.freq)+'&ar='+r(m.aR)+'&al='+r(m.aL)+'&or='+r(m.oR)+'&ol='+r(m.oL)
    +'&la='+r(S.landAmp)+'&lt='+Math.round(S.landTime);
  const ac=new AbortController(),to=setTimeout(()=>ac.abort(),400);
  try{const res=await fetch(q,{signal:ac.signal,cache:'no-store'});show(await res.json());lastOk=Date.now()}catch(e){}
  clearTimeout(to);busy=false;
}
setInterval(tick,50);
setInterval(()=>{if(Date.now()-lastOk>1000){
  $('stn').innerHTML='<span class="bad">Mất kết nối trạm</span>';$('lnk').innerHTML='<span class="mut">Bướm: ?</span>';
  autoLand('Mất kết nối trạm: bướm tự hạ cánh. Bấm HỦY HẠ CÁNH để lái lại');
}},250);
draw();
</script></body></html>)HTML";
