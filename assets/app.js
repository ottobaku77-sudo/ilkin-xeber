(function(){
  const D = window.NEWS || {items:[],sources:[]};
  const $ = s => document.querySelector(s);
  const grid=$('#grid'), q=$('#q'), src=$('#src'), cats=$('#cats'), more=$('#more');
  const PAGE=24; let shown=PAGE, cat='';
  const esc = s => String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm = s => String(s||'').toLowerCase().replace(/ё/g,'е');

  // filters
  D.sources.forEach(s=>src.insertAdjacentHTML('beforeend',`<option value="${esc(s.name)}">${esc(s.name)} (${s.count})</option>`));
  const counts={}; D.items.forEach(i=>counts[i.category]=(counts[i.category]||0)+1);
  const order=['Политика','Экономика','Общество','Происшествия','Мир','Спорт','Технологии','Культура','Разное'];
  const catList=[''].concat(order.filter(c=>counts[c]));
  cats.innerHTML=catList.map(c=>`<button class="chip" data-c="${esc(c)}" aria-pressed="${c===''}">${c||'Все'}${c?` <small>${counts[c]}</small>`:''}</button>`).join('');
  $('#srcs').innerHTML='Источники: '+D.sources.map(s=>`<a href="${esc(new URL(s.url).origin)}" target="_blank" rel="noopener">${esc(s.name)}</a>`).join(' · ');

  // restore state from URL
  const P=new URLSearchParams(location.search);
  q.value=P.get('q')||''; src.value=P.get('src')||''; cat=P.get('cat')||'';
  cats.querySelectorAll('.chip').forEach(b=>b.setAttribute('aria-pressed',b.dataset.c===cat));

  function hl(text, terms){
    let h=esc(text); if(!terms.length) return h;
    terms.forEach(t=>{ const re=new RegExp('('+t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','gi'); h=h.replace(re,'<mark>$1</mark>'); });
    return h;
  }
  function ago(ts){
    const m=Math.round((Date.now()/1000-ts)/60);
    if(m<1) return 'только что'; if(m<60) return m+' мин назад';
    const h=Math.round(m/60); if(h<24) return h+' ч назад'; return null;
  }
  function card(it,i,terms){
    const lead = i===0 && !terms.length && !cat && !src.value;
    const img = it.image ? `<img src="${esc(it.image)}" alt="" loading="${i<8?'eager':'lazy'}" referrerpolicy="no-referrer" onerror="this.parentNode.classList.add('noimg');this.remove()">` : '';
    const rel = ago(it.ts);
    return `<a class="card${lead?' lead':''}" href="${esc(it.link)}" target="_blank" rel="noopener">
      <div class="thumb${img?'':' noimg'}" data-src="${esc(it.source)}">${img}<span class="badge">${esc(it.category)}</span></div>
      <div class="body">
        <div class="meta"><span class="src">${esc(it.source)}</span><time title="${esc(it.time)} МСК">${rel?rel+' · ':''}${esc(it.time.slice(11))} МСК${rel?'':', '+esc(it.time.slice(0,5))}</time></div>
        <h2>${hl(it.title,terms)}</h2>
        ${it.summary?`<p>${hl(it.summary,terms)}</p>`:''}
        <span class="read">Читать на ${esc(it.source)} →</span>
      </div></a>`;
  }
  function render(){
    const terms=norm(q.value).split(/\s+/).filter(Boolean);
    const list=D.items.filter(it=>{
      if(src.value && it.source!==src.value) return false;
      if(cat && it.category!==cat) return false;
      const hay=norm(it.title+' '+it.summary+' '+it.source);
      return terms.every(t=>hay.includes(t));
    });
    grid.innerHTML=list.slice(0,shown).map((it,i)=>card(it,i,terms)).join('');
    $('#count').textContent=`Новостей: ${list.length}`+(list.length>shown?` · показано ${shown}`:'');
    $('#empty').hidden=list.length>0; more.hidden=list.length<=shown;
    const P=new URLSearchParams(); if(q.value)P.set('q',q.value); if(src.value)P.set('src',src.value); if(cat)P.set('cat',cat);
    history.replaceState(null,'',P.toString()?'?'+P:location.pathname);
  }
  let t; q.addEventListener('input',()=>{clearTimeout(t);t=setTimeout(()=>{shown=PAGE;render()},150)});
  src.addEventListener('change',()=>{shown=PAGE;render()});
  cats.addEventListener('click',e=>{const b=e.target.closest('.chip'); if(!b)return; cat=b.dataset.c;
    cats.querySelectorAll('.chip').forEach(x=>x.setAttribute('aria-pressed',x===b)); shown=PAGE; render();});
  more.addEventListener('click',()=>{shown+=PAGE;render()});
  render();
})();
