const $ = (s, root = document) => root.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icons = {
 pin:'<path d="m8 3 8 0-1 6 4 4H5l4-4ZM12 13v8"/>',reply:'<path d="m9 5-6 6 6 6M3 11h10a8 8 0 0 1 8 8"/>',bookmark:'<path d="M6 3h12v19l-6-4-6 4Z"/>',more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',trash:'<path d="M3 6h18M8 6V3h8v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
 search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/>',
 plus:'<path d="M12 5v14M5 12h14"/>', arrow:'<path d="m9 5 7 7-7 7"/>', down:'<path d="m6 9 6 6 6-6"/>',
 home:'<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',
 chat:'<path d="M21 11a9 9 0 0 1-9 9H4l-2 2V11a9 9 0 0 1 19 0Z"/><path d="M7 9h10M7 13h6"/>',
 file:'<path d="M14 3H5v18h14V8Z"/><path d="M14 3v5h5M8 12h8M8 16h5"/>',
 folder:'<path d="M3 6h6l2 3h10v11H3Z"/>', users:'<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 6"/>',
 send:'<path d="m3 3 19 9-19 9 4-9ZM7 12h15"/>', clip:'<path d="m9 12 6-6a3 3 0 0 1 4 4l-9 9a5 5 0 0 1-7-7l10-10M6 15l9-9"/>',
 code:'<path d="m8 6-6 6 6 6m8-12 6 6-6 6M14 3l-4 18"/>', check:'<path d="m5 12 4 4L19 6"/>',
 close:'<path d="m6 6 12 12M18 6 6 18"/>', download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
 logout:'<path d="M10 3H3v18h7m5-15 6 6-6 6m-7-6h13"/>', link:'<path d="m9 15 6-6M8 16l-2 2a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m2 1 2-2a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0"/>',
 menu:'<path d="M4 6h16M4 12h16M4 18h16"/>', globe:'<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
 spark:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/>'
};
const icon = (name, cls='') => `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.file}</svg>`;
const demoFiles = [];
async function api(path, data){
 const response=await fetch(path,{signal:AbortSignal.timeout(20000),method:data===undefined?'GET':'POST',headers:data===undefined?{}:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});
 const result=await response.json();if(!response.ok){const error=new Error(result.error || '请求失败');error.status=response.status;throw error;}return result;
}
function toast(message){$('#toast').textContent=message;$('#toast').classList.add('show');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),4000);}
const size = n => n<1024?`${n} B`:n<1048576?`${(n/1024).toFixed(1)} KB`:`${(n/1048576).toFixed(1)} MB`;
const time = n => new Date(n*1000).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',hour12:false});
const avatar = (name, index=0) => `<span class="avatar tone-${index%4}">${esc(name.slice(0,1))}</span>`;
const fileIcon = file => /\.(ts|js|py|html|css|json|tsx|jsx|go|rs|java|c|cpp|sh|yml|yaml)$/i.test(file.name)?'code':'file';
function modal(html,wide=false){$('#modal-root').innerHTML=`<div class="modal-overlay"><section class="modal ${wide?'wide':''}" role="dialog" aria-modal="true" aria-labelledby="modal-title"><button class="modal-close icon-button" data-action="close" aria-label="关闭">${icon('close')}</button>${html}</section></div>`;$('.modal-overlay').addEventListener('click',e=>{if(e.target===e.currentTarget)closeModal();});setTimeout(()=>$('.modal input')?.focus(),30);}
function closeModal(){$('#modal-root').innerHTML='';}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();if(e.key==='Tab'&&$('.modal')){const elements=[...$('.modal').querySelectorAll('button,input,textarea,select,a[href]')].filter(el=>!el.disabled);const first=elements[0],last=elements.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}});
function formError(error){const el=$('#form-error');if(el)el.textContent=error.message;else toast(error.message);}
function authModal(mode='register'){
 const register=mode==='register';modal(`<div class="modal-symbol">t.</div><span class="eyebrow">WELCOME TO TOGETHER</span><h2 id="modal-title">${register?'让我们开始同频':'欢迎回到同频'}</h2><p>${pendingInvite?'登录或注册后即可加入邀请中的工作区。':'给项目、资料和伙伴，一个共同的空间。'}</p><form id="auth-form">${register?'<label>你的名字<input name="name" required maxlength="40" autocomplete="name" placeholder="伙伴们怎么称呼你"></label>':''}<label>邮箱地址<input name="email" type="email" required maxlength="200" autocomplete="email" placeholder="you@team.com"></label><label>密码<input name="password" type="password" required minlength="8" maxlength="128" autocomplete="${register?'new-password':'current-password'}" placeholder="至少 8 个字符"></label><p id="form-error" class="form-error" role="alert"></p><button class="button primary full" type="submit">${register?'创建账号':'登录'} ${icon('arrow')}</button></form><button class="switch-auth" id="switch-auth">${register?'已有账号？直接登录':'第一次来？创建账号'}</button>`);
 $('#switch-auth').onclick=()=>authModal(register?'login':'register');
 $('#auth-form').onsubmit=async e=>{e.preventDefault();const submit=$('button[type=submit]',e.target);submit.disabled=true;try{await api('/api/'+mode,Object.fromEntries(new FormData(e.target)));closeModal();await loadAccount();if(!state.workspace&&!pendingInvite)workspaceModal();}catch(error){formError(error);}finally{submit.disabled=false;}};
}
function workspaceModal(){modal(`<span class="eyebrow">A NEW BEGINNING</span><h2 id="modal-title">创建你的工作区</h2><p>一个项目，一群伙伴，一处共同的空间。</p><form id="workspace-form"><label>工作区名称<input name="name" required maxlength="50" placeholder="例如：好想法工作室"></label><label>简单介绍<textarea name="description" maxlength="300" placeholder="我们准备一起做些什么？"></textarea></label><p id="form-error" class="form-error" role="alert"></p><button class="button primary full">创建工作区 ${icon('arrow')}</button></form>`);$('#workspace-form').onsubmit=async e=>{e.preventDefault();const submit=$('button',e.target);submit.disabled=true;try{const result=await api('/api/workspaces',Object.fromEntries(new FormData(e.target)));await loadAccount(result.id);closeModal();toast('工作区已创建，邀请伙伴一起加入吧');}catch(error){formError(error);}finally{submit.disabled=false;}};}
function channelModal(){
 modal(`<h2 id="modal-title">创建群聊</h2><p>群聊用来讨论，工作区用来保存项目资料。</p><form id="channel-form"><label>群聊名称<input name="name" required maxlength="40" placeholder="例如：官网开发讨论"></label><label>关联工作区<select name="workspace_id"><option value="">暂不关联 · 独立群聊</option>${state.workspaces.map(w=>`<option value="${w.id}" ${w.id===state.workspace?.id?'selected':''}>${esc(w.name)}</option>`).join('')}</select></label><label>谁可以查看群聊<select name="visibility"><option value="private">仅受邀成员</option><option value="workspace">工作区全体成员</option></select></label><p class="invite-note" id="group-scope-note">仅受邀成员可以查看聊天。关联工作区后，群邀请也会授予该工作区文件及公开群聊的访问权限。</p><label>群聊介绍<input name="description" maxlength="200" placeholder="这个群聊用来讨论什么"></label><p id="form-error" class="form-error" role="alert"></p><button class="button primary full">创建群聊</button></form>`);
 const form=$('#channel-form'),workspace=$('select[name=workspace_id]',form),visibility=$('select[name=visibility]',form);
 const update=()=>{if(!workspace.value){visibility.value='private';visibility.disabled=true;}else visibility.disabled=false;$('#group-scope-note').textContent=!workspace.value?'独立群聊，仅受邀成员可查看消息和附件。':visibility.value==='private'?'仅受邀成员可查看聊天。群邀请也会授予关联工作区全部文件及公开群聊的访问权限。':'所选工作区的全部成员都可以查看本群聊天及附件。';};workspace.onchange=update;visibility.onchange=update;update();
 form.onsubmit=async e=>{e.preventDefault();const button=$('button.primary',form);button.disabled=true;try{const data=Object.fromEntries(new FormData(form));data.visibility=visibility.value;const result=await api('/api/groups',data);await refreshGroups();await selectChat('channel',result.id);closeModal();toast(data.workspace_id?'群聊已创建，已关联工作区':'独立群聊已创建');}catch(error){formError(error);}finally{button.disabled=false;}};
}
async function inviteModal(){
 if(state.workspace.owner!==state.user.id){toast('请联系工作区创建者生成邀请链接');return;}
 modal(`<span class="eyebrow">BETTER TOGETHER</span><h2 id="modal-title">邀请伙伴，一起同频</h2><p>加入后可访问本工作区的全部文件及公开群聊。仅受邀成员群聊需要单独邀请。</p><button class="button primary full" id="generate-invite">生成 7 天有效的邀请链接</button><p id="form-error" class="form-error"></p><div id="invite-result"></div>`);
 $('#generate-invite').onclick=async e=>{e.target.disabled=true;try{const result=await api(`/api/workspaces/${state.workspace.id}/invite`,{});const url=location.origin+'/?invite='+result.token;$('#invite-result').innerHTML=`<label>邀请链接<input id="invite-url" readonly value="${esc(url)}"></label><button class="button secondary full" id="copy-invite">${icon('link')} 复制邀请链接</button><p class="invite-note">${['localhost','127.0.0.1'].includes(location.hostname)?'当前为本机地址。邀请其他电脑前，请通过局域网地址或部署后的域名打开本站，再生成链接。':'将链接发给伙伴，对方注册或登录后即可加入。'}</p>`;$('#copy-invite').onclick=async()=>{try{await navigator.clipboard.writeText(url);toast('邀请链接已复制');}catch{$('#invite-url').select();toast('请按 Ctrl+C 复制选中的链接');}};}catch(error){formError(error);}finally{e.target.disabled=false;}};
}


