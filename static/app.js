const tg=window.Telegram?.WebApp;
if(tg){tg.ready();tg.expand();try{tg.setHeaderColor("secondary_bg_color");tg.setBackgroundColor(tg.themeParams?.bg_color||"#17212b")}catch(e){}}
const init=tg?.initData||"",H={"X-Telegram-Init-Data":init};const $=id=>document.getElementById(id);
function say(s){const el=$("toast");el.textContent=s;el.classList.add("show");clearTimeout(say.timer);say.timer=setTimeout(()=>el.classList.remove("show"),2400)}
async function api(url,opt={}){const r=await fetch(url,{...opt,headers:{...H,"Content-Type":"application/json"}});const d=await r.json();if(!r.ok)throw Error(d.error||"Ошибка");return d}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function switchTab(name){document.querySelectorAll(".tab-page").forEach(p=>p.hidden=p.id!=="page-"+name);document.querySelectorAll(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.tab===name));window.scrollTo({top:0,behavior:"smooth"})}
document.querySelectorAll(".nav-item").forEach(b=>b.addEventListener("click",()=>switchTab(b.dataset.tab)));$("topProfile").addEventListener("click",()=>switchTab("profile"));
document.querySelectorAll("[data-goto]").forEach(b=>b.addEventListener("click",()=>switchTab(b.dataset.goto)));
let adminUsers=[];
function renderUsers(){const q=$("userSearch").value.trim().toLowerCase();const list=adminUsers.filter(x=>String(x.id).includes(q)||(x.name||"").toLowerCase().includes(q)||(x.username||"").toLowerCase().includes(q));$("users").innerHTML=list.length?list.map(x=>'<div class="user-row"><div class="user-main"><div class="user-name">'+esc(x.name||"Игрок")+(x.username?' · @'+esc(x.username):'')+'</div><div class="user-id">ID: '+x.id+'</div></div><div class="user-balance">'+x.balance+' ⭐</div></div>').join(""):'<p class="muted">Пользователи не найдены</p>'}
async function loadUsers(){const d=await api("/api/admin/users");adminUsers=d.users||[];$("totalUsers").textContent=d.total??adminUsers.length;renderUsers()}
async function load(){const m=await api("/api/me");const name=m.name||"участник";$("hello").textContent="Привет, "+name+"!";$("headerBalance").textContent=Number(m.balance).toLocaleString("ru-RU");$("homeRefs").textContent=m.refs;$("profileName").textContent=name;$("profileUsername").textContent=m.username?"@"+m.username:"Пользователь Telegram";$("profileBalance").textContent=Number(m.balance).toLocaleString("ru-RU")+" ⭐";$("avatarBalance").textContent=Number(m.balance).toLocaleString("ru-RU");$("profileRefs").textContent=m.refs;$("profileStatus").textContent=m.admin?"Администратор":"Игрок";if(m.photo_url){$("avatar").src=m.photo_url;$("avatar").hidden=false;$("avatarFallback").hidden=true;$("topAvatar").src=m.photo_url;$("topAvatar").hidden=false;$("topAvatarFallback").hidden=true}else{$("avatar").hidden=true;$("avatarFallback").hidden=false;$("topAvatar").hidden=true;$("topAvatarFallback").hidden=false}
const f=await api("/api/ref");$("refLink").textContent=f.link;$("copy").onclick=async()=>{try{if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(f.link);else{const t=document.createElement("textarea");t.value=f.link;document.body.appendChild(t);t.select();document.execCommand("copy");t.remove()}say("Ссылка скопирована")}catch(e){say("Не удалось скопировать ссылку")}};if(m.admin){$("admin").hidden=false;await loadUsers()}}
async function claimDaily(){try{const d=await api("/api/daily",{method:"POST",body:"{}"});say("Получено +"+d.reward+" ⭐");await load()}catch(e){say(e.message)}}
$("dailyBtn").onclick=claimDaily;$("homeDaily").onclick=claimDaily;
$("userSearch").addEventListener("input",renderUsers);$("refreshUsers").onclick=()=>loadUsers().catch(e=>say(e.message));
$("quizBtn").onclick=async()=>{try{const d=await api("/api/quiz");$("quizBox").hidden=false;if(d.finished){$("question").textContent="Вопросы закончились";$("answers").innerHTML="";return}$("question").textContent=d.q;$("answers").innerHTML=d.answers.map((a,i)=>'<button data-i="'+i+'">'+esc(a)+'</button>').join("");[...$("answers").children].forEach(b=>b.onclick=async()=>{try{const a=await api("/api/answer",{method:"POST",body:JSON.stringify({index:d.index,choice:+b.dataset.i})});$("result").textContent=a.correct?"Верно! +"+a.reward+" ⭐":"Неверно. "+(a.balance_delta<0?"−"+Math.abs(a.balance_delta):"0")+" ⭐";await load()}catch(e){say(e.message)}});$("quizBox").scrollIntoView({behavior:"smooth",block:"nearest"})}catch(e){say(e.message)}};
$("change").onclick=async()=>{const id=$("target").value.trim(),amount=$("amount").value.trim();if(!/^\d+$/.test(id)||! /^[+-]?\d+$/.test(amount)||Number(amount)===0){say("Введи корректный ID и сумму, например +50 или -20");return}try{await api("/api/admin/adjust",{method:"POST",body:JSON.stringify({id,amount:Number(amount)})});say(Number(amount)>0?"Начислено +"+amount+" ⭐":"Списано "+Math.abs(Number(amount))+" ⭐");$("amount").value="";await load();await loadUsers()}catch(e){say(e.message)}};
if(init)load().catch(e=>say(e.message));else say("Открой приложение через Telegram");
let memoryState=null,reactionTimer=null,reactionStarted=0,reactionReady=false;
async function awardGame(game){try{const d=await api("/api/game/reward",{method:"POST",body:JSON.stringify({game})});say("Получено +"+d.reward+" ⭐");await load()}catch(e){say(e.message)}}
function startMemory(){
 $("gameBox").hidden=false;$("quizBox").hidden=true;$("gameTitle").textContent="Игра на память";$("gameHint").textContent="Открой карточки и найди три пары. Никаких звёзд не теряешь.";
 const deck=["🍀","🚀","💎","🍀","🚀","💎"].sort(()=>Math.random()-.5);
 memoryState={deck,open:[],matched:[],locked:false};
 $("gameArea").innerHTML='<div class="memory-grid">'+deck.map((_,i)=>'<button class="memory-card" data-card="'+i+'">?</button>').join("")+'</div><p id="memoryProgress" class="muted">Найдено пар: 0/3</p><button class="button button-secondary" id="memoryRestart">Начать заново</button>';
 [...$("gameArea").querySelectorAll("[data-card]")].forEach(b=>b.onclick=()=>flipMemory(+b.dataset.card));
 $("memoryRestart").onclick=startMemory;
}
function flipMemory(i){
 const s=memoryState;if(!s||s.locked||s.open.includes(i)||s.matched.includes(i))return;
 s.open.push(i);const btn=$("gameArea").querySelector('[data-card="'+i+'"]');btn.textContent=s.deck[i];btn.classList.add("revealed");
 if(s.open.length===2){
  const [a,b]=s.open;
  if(s.deck[a]===s.deck[b]){s.matched.push(a,b);s.open=[];$("memoryProgress").textContent="Найдено пар: "+(s.matched.length/2)+"/3";if(s.matched.length===6){$("memoryProgress").textContent="Все пары найдены!";[...$("gameArea").querySelectorAll("button")].forEach(x=>x.disabled=true);awardGame("memory")}}
  else{s.locked=true;setTimeout(()=>{for(const n of s.open){const el=$("gameArea").querySelector('[data-card="'+n+'"]');if(el){el.textContent="?";el.classList.remove("revealed")}}s.open=[];s.locked=false},650)}
 }
}
function startReaction(){
 if(reactionTimer)clearTimeout(reactionTimer);reactionReady=false;
 $("gameBox").hidden=false;$("quizBox").hidden=true;$("gameTitle").textContent="Испытание реакции";$("gameHint").textContent="Нажми кнопку только когда она станет зелёной. Награда — за успешную реакцию.";
 $("gameArea").innerHTML='<button class="button" id="reactionStart">Начать</button><p id="reactionResult" class="muted">Жди сигнала.</p>';
 $("reactionStart").onclick=()=>{
  const b=$("reactionStart");b.disabled=true;b.textContent="Жди зелёный сигнал…";b.classList.remove("reaction-go");
  reactionTimer=setTimeout(()=>{reactionReady=true;reactionStarted=performance.now();b.disabled=false;b.textContent="ЖМИ!";b.classList.add("reaction-go")},1200+Math.random()*2500);
  b.onclick=()=>{
   if(!reactionReady){clearTimeout(reactionTimer);$("reactionResult").textContent="Слишком рано! Попробуй ещё раз.";b.disabled=false;b.textContent="Повторить";b.classList.remove("reaction-go");b.onclick=startReaction;return}
   const ms=Math.round(performance.now()-reactionStarted);reactionReady=false;b.disabled=true;$("reactionResult").textContent="Твоя реакция: "+ms+" мс";
   if(ms<700){awardGame("reaction")}else{$("reactionResult").textContent+=". Попробуй добиться результата меньше 700 мс."}
  };
 };
}
$("memoryBtn").onclick=startMemory;$("reactionBtn").onclick=startReaction;
