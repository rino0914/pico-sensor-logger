CHART_CLIENT_SCRIPT = r"""
const CHART_API='/api/measurements';
const CHART_REFRESH_MS=5000;
const PLOT={left:76,right:500,top:16,bottom:300,width:424,height:284};
const COLORS={co2:'#38bdf8',temperature:'#fb923c',humidity:'#34d399'};
const DEFINITIONS={
  co2:{label:'CO₂',unit:'ppm'},
  temperature:{label:'온도',unit:'°C'},
  humidity:{label:'습도',unit:'%'}
};
let chartData={time_offsets:[],co2:[],temperature:[],humidity:[]};

function escapeHtml(value){return String(value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function formatValue(value){return Number(value).toFixed(1)}
function relativeChanges(values){if(!values.length)return[];const base=values[0],d=Math.abs(base)||1;return values.map(v=>(v-base)*100/d)}
function scaleFor(values,minimumRange){
  if(!values.length)return{min:0,max:minimumRange,range:minimumRange};
  let min=Math.min(...values),max=Math.max(...values),range=max-min;
  if(range<minimumRange){const center=(min+max)/2;min=center-minimumRange/2;max=center+minimumRange/2}
  else{const padding=range*.05;min-=padding;max+=padding}
  return{min:min,max:max,range:max-min};
}
function xPositions(times,count){
  if(!count)return[];
  if(count===1)return[PLOT.right];
  const first=times[0]||0,duration=(times[count-1]||0)-first;
  if(duration>0)return times.map(t=>PLOT.left+(t-first)*PLOT.width/duration);
  return Array.from({length:count},(_,i)=>PLOT.left+i*PLOT.width/(count-1));
}
function yPosition(value,scale){return PLOT.bottom-(value-scale.min)*PLOT.height/scale.range}
function pathFor(values,scale,x){return values.map((v,i)=>(i?'L':'M')+' '+x[i].toFixed(1)+' '+yPosition(v,scale).toFixed(1)).join(' ')}
function relativeTimeLabel(seconds){const rounded=Math.max(0,Math.round(seconds));if(!rounded)return'최신';const m=Math.floor(rounded/60),s=rounded%60;return m?'-'+m+':'+String(s).padStart(2,'0'):'-'+s+'초'}
function measurementTimeLabel(index,times){const latest=times.length?times[times.length-1]:0,ago=Math.max(0,latest-(times[index]||0)),relative=relativeTimeLabel(ago),stamp=chartData.latest_timestamp;if(!stamp)return relative;const date=new Date(stamp[0],stamp[1]-1,stamp[2],stamp[4],stamp[5],stamp[6]);date.setSeconds(date.getSeconds()-ago);return String(date.getHours()).padStart(2,'0')+':'+String(date.getMinutes()).padStart(2,'0')+':'+String(date.getSeconds()).padStart(2,'0')+' ('+relative+')'}
function axesMarkup(scale,times,yTitle){
  let html='';
  for(let i=0;i<=5;i++){const ratio=i/5,y=PLOT.top+PLOT.height*ratio,value=scale.max-scale.range*ratio;html+='<line class="grid-line" x1="76" y1="'+y+'" x2="500" y2="'+y+'"/><text class="label" x="69" y="'+(y+3)+'" text-anchor="end">'+formatValue(value)+'</text>'}
  const duration=times.length>1?Math.max(0,times[times.length-1]-times[0]):0;
  for(let i=0;i<=4;i++){const ratio=i/4,x=PLOT.left+PLOT.width*ratio;html+='<line class="grid-line" x1="'+x+'" y1="16" x2="'+x+'" y2="300"/><text class="label" x="'+x+'" y="318" text-anchor="middle">'+relativeTimeLabel(duration*(1-ratio))+'</text>'}
  return html+'<line class="axis" x1="76" y1="16" x2="76" y2="300"/><line class="axis" x1="76" y1="300" x2="500" y2="300"/><text class="axis-title" x="288" y="350" text-anchor="middle">측정 시간 (분:초, 최신값 기준)</text><text class="axis-title" x="-158" y="14" text-anchor="middle" transform="rotate(-90)">'+escapeHtml(yTitle)+'</text>';
}
function renderChart(svg,datasets,minimumRange,yTitle){
  const count=datasets.length?datasets[0].plot.length:0,times=chartData.time_offsets.slice(0,count),x=xPositions(times,count);
  const all=[];datasets.forEach(d=>all.push(...d.plot));const scale=scaleFor(all,minimumRange);
  let html=axesMarkup(scale,times,yTitle);
  datasets.forEach(d=>{html+='<path class="trace" style="--accent:'+d.color+'" d="'+pathFor(d.plot,scale,x)+'"/>'});
  html+='<g class="chart-cursor" style="display:none"><line class="cursor-line" y1="16" y2="300"/>'+datasets.map((d,i)=>'<circle class="cursor-dot" data-index="'+i+'" r="4" style="--accent:'+d.color+'"/>').join('')+'</g><rect class="pointer-area" x="76" y="16" width="424" height="284"/>';
  svg.innerHTML=html;
  attachPointer(svg,datasets,x,scale,times);
}
function attachPointer(svg,datasets,x,scale,times){
  const cursor=svg.querySelector('.chart-cursor'),line=svg.querySelector('.cursor-line'),dots=svg.querySelectorAll('.cursor-dot'),tooltip=svg.parentElement.querySelector('.chart-tooltip');
  function hide(){cursor.style.display='none';tooltip.hidden=true}
  function show(event){
    if(!x.length)return hide();
    const rect=svg.getBoundingClientRect(),svgX=(event.clientX-rect.left)*520/rect.width;
    let nearest=0,distance=Infinity;x.forEach((value,i)=>{const d=Math.abs(value-svgX);if(d<distance){distance=d;nearest=i}});
    line.setAttribute('x1',x[nearest]);line.setAttribute('x2',x[nearest]);
    datasets.forEach((dataset,i)=>{dots[i].setAttribute('cx',x[nearest]);dots[i].setAttribute('cy',yPosition(dataset.plot[nearest],scale))});
    cursor.style.display='';
    tooltip.innerHTML='<strong>'+measurementTimeLabel(nearest,times)+'</strong>'+datasets.map(d=>'<span><i style="--accent:'+d.color+'"></i>'+d.label+' '+formatValue(d.raw[nearest])+' '+d.unit+'</span>').join('');
    tooltip.hidden=false;
    const left=Math.max(8,Math.min(rect.width-tooltip.offsetWidth-8,event.clientX-rect.left+12));tooltip.style.left=left+'px';tooltip.style.top=Math.max(8,event.clientY-rect.top-tooltip.offsetHeight-10)+'px';
  }
  svg.onpointermove=show;svg.onpointerdown=show;svg.onpointerleave=hide;
}
function rawDataset(key){const definition=DEFINITIONS[key];return{label:definition.label,unit:definition.unit,color:COLORS[key],raw:chartData[key],plot:chartData[key]}}
function formatDeviceTime(value){if(!value)return'--';return String(value[0]).padStart(4,'0')+'-'+String(value[1]).padStart(2,'0')+'-'+String(value[2]).padStart(2,'0')+' '+String(value[4]).padStart(2,'0')+':'+String(value[5]).padStart(2,'0')+':'+String(value[6]).padStart(2,'0')}
function formatRuntime(totalSeconds){const value=Math.max(0,Math.floor(Number(totalSeconds)||0)),minutes=Math.floor(value/60),seconds=value%60;return String(minutes).padStart(2,'0')+':'+String(seconds).padStart(2,'0')}
function updateText(id,value){const element=document.getElementById(id);if(element)element.textContent=value}
function updateDashboardStatus(){
  Object.keys(DEFINITIONS).forEach(key=>{const values=chartData[key],element=document.querySelector('[data-latest="'+key+'"]');if(element)element.textContent=values.length?formatValue(values[values.length-1]):'--'});
  const hasData=chartData.co2.length>0,freshness=!hasData?'측정값 없음':chartData.is_stale?'갱신 지연':chartData.age_ms==null?'측정값 없음':Math.floor(chartData.age_ms/1000)+'초 전',timeState=chartData.time_synchronized?'완료':'필요';
  updateText('sample-count',chartData.co2.length+'회');updateText('data-freshness',freshness);updateText('meta-freshness',freshness);updateText('time-state',timeState);updateText('meta-time-state',timeState);updateText('runtime',formatRuntime(chartData.runtime_seconds));updateText('device-time',formatDeviceTime(chartData.current_time));updateText('pending-count',chartData.pending_count||0);updateText('dropped-count',chartData.dropped_count||0);updateText('experiment-status',chartData.status_text||'');
  const badge=document.getElementById('sensing-badge');if(badge){badge.className='badge '+(chartData.sensing_enabled?'running':'stopped');badge.textContent=chartData.sensing_enabled?'측정 중':'측정 중지'}
}
function renderAllCharts(){
  updateDashboardStatus();
  const combined=Object.keys(DEFINITIONS).map(key=>{const dataset=rawDataset(key);dataset.plot=relativeChanges(dataset.raw);return dataset});
  const comparison=document.querySelector('svg[data-chart="comparison"]');if(comparison)renderChart(comparison,combined,10,'초기값 대비 변화율 (%)');
}
async function refreshMeasurements(){try{if(window.PREVIEW_MEASUREMENTS)chartData=window.PREVIEW_MEASUREMENTS;else{const response=await fetch(CHART_API,{cache:'no-store'});if(!response.ok)throw Error('HTTP '+response.status);chartData=await response.json()}renderAllCharts();document.body.dataset.chartState='ready'}catch(error){console.log('chart update failed',error);document.body.dataset.chartState='error'}}
refreshMeasurements();if(!window.PREVIEW_MEASUREMENTS)setInterval(refreshMeasurements,CHART_REFRESH_MS);
"""
