const $=s=>document.querySelector(s); let job=null;
async function health(){const r=await fetch('/health'); $('#health').textContent=(await r.json()).status==='ok'?'运行中':'异常'}
async function probe(){const r=await fetch('/api/runtime/probe'); $('#runtime').textContent=JSON.stringify(await r.json(),null,2)}
$('#new').onclick=async()=>{const r=await fetch('/api/sessions',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({})});const s=await r.json();$('#session').value=s.id;$('#chat').innerHTML=''};
$('#probe').onclick=probe;
$('#form').onsubmit=async e=>{e.preventDefault();if(!$('#session').value)return alert('请先新建会话');const text=$('#message').value;$('#message').value='';$('#chat').insertAdjacentHTML('beforeend',`<article class="user">${escapeHtml(text)}</article>`);const r=await fetch('/api/chat',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({session_id:$('#session').value,message:text,length:$('#length').value})});const d=await r.json();$('#chat').insertAdjacentHTML('beforeend',`<article class="assistant">${escapeHtml(d.text||d.detail||JSON.stringify(d))}<small>${d.chunks||0} chunks · ${d.chars||0} chars · ${d.partial?'partial':'complete'}</small></article>`)};
$('#stop').onclick=()=>{if(job)fetch(`/api/generation/${job}/cancel`,{method:'POST'})};
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}; health();
