(function(){
  const D = window.NEWS || {items:[],sources:[],order:[],clubs:[]};
  const $ = s => document.querySelector(s);
  const grid=$('#grid'), q=$('#q'), src=$('#src'), cats=$('#cats'), clubsNav=$('#clubs'), more=$('#more');
  const PAGE=24; let shown=PAGE;
  const preset = window.PRESET_CAT || '';
  const esc = s => String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm = s => String(s||'').replace(/İ/g,'i').replace(/I/g,'ı').toLowerCase().replace(/ё/g,'е');
  const ICON = {'Futbol':'⚽ '};

  const P=new URLSearchParams(location.search);
  let lang = P.get('lang')==='ru' ? 'ru' : 'az';
  let cat = P.has('cat') ? P.get('cat') : preset;
  let club = P.get('club')||'';
  q.value=P.get('q')||'';

  document.querySelectorAll('.tab').forEach(a=>a.setAttribute('aria-current', (a.dataset.tab==='futbol') === (cat==='Futbol') ? 'page' : 'false'));

  function pool(){            // items for the current language (club tabs mix AZ + RU so they are never empty)
    return D.items.filter(it => club ? it.clubs && it.clubs.includes(club) : it.lang===lang);
  }
  function drawFilters(){
    const base=D.items.filter(it=>it.lang===lang);
    const counts={}; base.forEach(i=>counts[i.category]=(counts[i.category]||0)+1);
    const list=[''].concat(D.order.filter(c=>counts[c]));
    cats.innerHTML=list.map(c=>`<button class="chip${c==='Futbol'?' chip-foot':''}" data-c="${esc(c)}" aria-pressed="${c===cat}">${c?(ICON[c]||'')+esc(c):'Hamısı'}${c?` <small>${counts[c]}</small>`:''}</button>`).join('');
    const cc={}; D.items.forEach(i=>(i.clubs||[]).forEach(c=>cc[c]=(cc[c]||0)+1));
    clubsNav.hidden = cat!=='Futbol';
    clubsNav.innerHTML='<span class="sub-label">Komandalar:</span>'+[''].concat(D.clubs).map(c=>`<button class="chip chip-club" data-k="${esc(c)}" aria-pressed="${c===club}">${c?esc(c):'Bütün futbol'}${c?` <small>${cc[c]||0}</small>`:''}</button>`).join('');
    const srcs=D.sources.filter(s=>club || s.lang===lang);
    const cur=src.value||P.get('src')||'';
    src.innerHTML='<option value="">Bütün mənbələr</option>'+srcs.map(s=>`<option value="${esc(s.name)}">${esc(s.name)} (${s.count})</option>`).join('');
    src.value = srcs.some(s=>s.name===cur) ? cur : '';
    document.querySelectorAll('.lang button').forEach(b=>b.setAttribute('aria-pressed', b.dataset.l===lang));
  }
  $('#srcs').innerHTML='Mənbələr: '+D.sources.map(s=>`<a href="${esc(new URL(s.url).origin)}" target="_blank" rel="noopener">${esc(s.name)}</a>${s.lang==='ru'?' <small>(RU)</small>':''}`).join(' · ');

  function hl(text, terms){
    let h=esc(text); if(!terms.length) return h;
    terms.forEach(t=>{ const re=new RegExp('('+esc(t).replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','gi'); h=h.replace(re,'<mark>$1</mark>'); });
    return h;
  }
  function ago(ts){
    const m=Math.round((Date.now()/1000-ts)/60);
    if(m<1) return 'indicə'; if(m<60) return m+' dəq əvvəl';
    const h=Math.round(m/60); if(h<24) return h+' saat əvvəl'; return null;
  }
  function card(it,i,terms){
    const lead = i===0 && !terms.length && !cat && !src.value && !club;
    const img = it.image ? `<img src="${esc(it.image)}" alt="" loading="${i<8?'eager':'lazy'}" referrerpolicy="no-referrer" onerror="this.parentNode.classList.add('noimg');this.remove()">` : '';
    const rel = ago(it.ts);
    const tags = (it.clubs||[]).map(c=>`<span class="ctag">${esc(c)}</span>`).join('');
    return `<a class="card${lead?' lead':''}" href="${esc(it.link)}" target="_blank" rel="noopener"${it.lang==='ru'?' lang="ru"':''}>
      <div class="thumb${img?'':' noimg'}" data-src="${esc(it.source)}">${img}<span class="badge${it.category==='Futbol'?' badge-foot':''}">${(ICON[it.category]||'')+esc(it.category)}</span>${it.lang==='ru'?'<span class="badge-ru">RU</span>':''}</div>
      <div class="body">
        <div class="meta"><span class="src">${esc(it.source)}</span><time title="${esc(it.time)} (Bakı vaxtı)">${rel?rel+' · ':''}${esc(it.time.slice(11))}${rel?'':', '+esc(it.time.slice(0,5))}</time></div>
        <h2>${hl(it.title,terms)}</h2>
        ${it.summary?`<p>${hl(it.summary,terms)}</p>`:''}
        ${tags?`<div class="ctags">${tags}</div>`:''}
        <span class="read">Mənbədə oxu →</span>
      </div></a>`;
  }
  function render(){
    const terms=norm(q.value).split(/\s+/).filter(Boolean);
    const list=pool().filter(it=>{
      if(src.value && it.source!==src.value) return false;
      if(cat && it.category!==cat) return false;
      const hay=norm(it.title+' '+it.summary+' '+it.source);
      return terms.every(t=>hay.includes(t));
    });
    grid.innerHTML=list.slice(0,shown).map((it,i)=>card(it,i,terms)).join('');
    $('#count').textContent=`Xəbər sayı: ${list.length}`+(list.length>shown?` · göstərilir: ${shown}`:'')+(club?' · Azərbaycan və rus dilində':'');
    $('#empty').hidden=list.length>0; more.hidden=list.length<=shown;
    const U=new URLSearchParams(); if(q.value)U.set('q',q.value); if(src.value)U.set('src',src.value);
    if(cat!==preset)U.set('cat',cat); if(club)U.set('club',club); if(lang!=='az')U.set('lang',lang);
    history.replaceState(null,'',U.toString()?'?'+U:location.pathname);
  }
  function update(){ shown=PAGE; drawFilters(); render(); }
  let t; q.addEventListener('input',()=>{clearTimeout(t);t=setTimeout(()=>{shown=PAGE;render()},150)});
  src.addEventListener('change',()=>{shown=PAGE;render()});
  cats.addEventListener('click',e=>{const b=e.target.closest('.chip'); if(!b)return; cat=b.dataset.c; if(cat!=='Futbol')club=''; update();});
  clubsNav.addEventListener('click',e=>{const b=e.target.closest('.chip'); if(!b)return; club=b.dataset.k; update();});
  document.querySelector('.lang').addEventListener('click',e=>{const b=e.target.closest('button'); if(!b)return; lang=b.dataset.l; club=''; update();});
  more.addEventListener('click',()=>{shown+=PAGE;render()});
  update();
})();
