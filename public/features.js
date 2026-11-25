// Small collaboration controls shared by the three-column views.
const fileBase = kind => '/api/' + ({shared:'files',personal:'personal-files',dm:'dm-files'}[kind] || 'files');
const conversationPath = () => `/api/conversations/${state.section==='friends'?'dm':'group'}/${chatTarget()?.id}`;
function preference(kind,id){return kind==='group'?state.groups.find(g=>g.id===id)||{}:kind==='dm'?state.activity?.dm?.[id]||{}:{pinned:state.activity?.workspace_pins?.includes(id)};}
function ordered(items,kind){return [...items].sort((a,b)=>Number(!!preference(kind,b.id).pinned)-Number(!!preference(kind,a.id).pinned));}
function badges(kind,id){const p=preference(kind,id);return `${p.mentions?'<span class="mention-badge">@</span>':''}${p.unread?`<span class="unread-badge" aria-label="${p.unread} 条未读">${p.unread>99?'99+':p.unread}</span>`:''}`;}
function pinButton(kind,id,name){const pinned=preference(kind,id).pinned;return `<button class="list-pin ${pinned?'is-pinned':''}" data-pin-kind="${kind}" data-pin-id="${id}" aria-label="${pinned?'取消置顶':'置顶'} ${esc(name)}" aria-pressed="${!!pinned}" title="${pinned?'取消置顶':'置顶'}">${icon('pin')}</button>`;}
async function refreshActivity(){if(state.demo)return;const user=state.user.id;const data=await api('/api/activity');if(state.demo||user!==state.user.id)return;const changed=JSON.stringify(state.activity)!==JSON.stringify(data);state.activity=data;state.groups=data.groups;if(state.channel&&!state.groups.some(g=>g.id===state.channel.id)){const id=state.channel.id;forgetConversation('group',id);state.channel=null;state.chatMembers=[];if(state.section==='home'&&state.homeView==='chat'){closeModal();render();toast('你已不在该群聊中');}}const list=$('#list-content');if(list&&changed)list.innerHTML=listContent();}
function replyBanner(){const m=state.replies?.[chatKey()];return m?`<div class="reply-banner"><span>回复 ${esc(m.author)}：${esc((m.body||m.attachment?.name||'附件').slice(0,100))}</span><button type="button" class="icon-button" data-action="cancel-reply" aria-label="取消回复">${icon('close')}</button></div>`:'';}
function attachmentCard(file){return !file?'':file.unavailable?`<div class="attachment-card muted">${esc(file.name)}</div>`:`<div class="attachment-card">${icon(fileIcon(file))}<button class="attachment-name" data-attachment-preview="${file.id}" data-file-kind="${file.file_type}" data-file-name="${esc(file.name)}">${esc(file.name)}</button><span class="muted">${size(file.size)}${file.storage==='group'?' · 仅本群':file.storage==='workspace'?' · 工作区共享':''}</span><button class="icon-button" data-attachment-download="${file.id}" data-file-kind="${file.file_type}" data-file-name="${esc(file.name)}" aria-label="下载 ${esc(file.name)}">${icon('download')}</button></div>`;}
function messageMarkup(m,{context=false}={}){return `<article class="message ${m.mentioned?'mentioned-message':''}" data-message-id="${m.id}">${avatar(m.author)}<div class="message-content"><div class="message-meta"><strong>${esc(m.author)}</strong><time>${esc(new Date(m.created*1000).toLocaleString('zh-CN',{hour12:false}))}</time>${m.pinned?'<span class="message-tag">已置顶</span>':''}${m.mentioned?'<span class="message-tag">提到了你</span>':''}<div class="message-actions"><button class="icon-button" data-reply="${m.id}" title="回复" aria-label="回复 ${esc(m.author)}">${icon('reply')}</button><button class="icon-button ${m.saved?'is-pinned':''}" data-save="${m.id}" aria-label="${m.saved?'取消收藏':'收藏'}消息" title="${m.saved?'取消收藏':'收藏'}">${icon('bookmark')}</button><button class="icon-button ${m.pinned?'is-pinned':''}" data-message-pin="${m.id}" aria-label="${m.pinned?'取消置顶':'置顶'}消息" title="${m.pinned?'取消置顶':'置顶'}">${icon('pin')}</button></div></div>${m.reply?`<button class="quoted-message" data-context="${m.reply.id}">${esc(m.reply.author)}：${esc(m.reply.body)}</button>`:''}${m.body?`<div class="message-body">${messageBody(m.body)}</div>`:''}${attachmentCard(m.attachment)}${context?`<button class="text-button" data-context="${m.id}">查看上下文</button>`:''}</div></article>`;}
function updateReply(){const box=$('#reply-slot');if(box)box.innerHTML=replyBanner();}
function visibleChat(){return !showingFiles()&&['home','friends'].includes(state.section)&&!!chatTarget();}
async function markVisibleRead(){
 if(state.demo||document.hidden||!visibleChat()||$('.modal'))return;
 const scroll=$('#message-scroll');if(!scroll)return;
 const edge=scroll.getBoundingClientRect().bottom;let last;
 for(const m of state.messages){const el=$(`[data-message-id="${m.id}"]`,scroll);if(el&&el.getBoundingClientRect().bottom<=edge+5)last=m;}
 if(!last)return;
 const key=chatKey(),path=conversationPath(),kind=state.section==='friends'?'dm':'group',target=chatTarget().id;
 if((state.readSent?.[key]||0)>=last.id)return;
 state.readSent??={};state.readSent[key]=last.id;
 try{const data=await api(path+'/state',{read_id:last.id});Object.assign(preference(kind,target),data);if(chatKey()===key){const list=$('#list-content');if(list)list.innerHTML=listContent();}}
 catch{state.readSent[key]=0;}
}
function returnToRead(force=false){
 const key=chatKey(),scroll=$('#message-scroll');if(!scroll)return;
 if(!force&&state.scrollPositions?.[key]!==undefined){scroll.scrollTop=state.scrollPositions[key];return;}
 const read=state.openRead?.[key]||0;
 const first=state.messages.find(m=>m.id>read&&m.user_id!==state.user.id);
 const element=first&&$(`[data-message-id="${first.id}"]`);
 if(first&&element){element.insertAdjacentHTML('beforebegin','<div class="unread-divider">以下为未读消息</div>');scroll.scrollTop=Math.max(0,element.offsetTop-scroll.offsetTop-40);}
 else scroll.scrollTop=scroll.scrollHeight;
}
async function viewContext(id){
 if(state.demo){toast('演示模式仅展示示例记录');return;}
 const key=chatKey(),path=conversationPath();
 try{const data=await api(path+'/context?id='+encodeURIComponent(id));if(key!==chatKey())return;state.contextMessages=data.messages;modal(`<h2 id="modal-title">消息上下文</h2><p>显示这条消息前后的聊天记录。</p><div class="context-messages">${data.messages.map(m=>`<div class="${String(m.id)===String(id)?'context-focus':''}">${messageMarkup(m)}</div>`).join('')}</div>`,true);const focus=$('.context-focus');if(focus)focus.scrollIntoView({block:'center'});}
 catch(error){toast(error.message);}
}
async function savedModal(){
 if(!ensureUser())return;const key=chatKey(),data=await api(conversationPath()+'/saved');if(key!==chatKey())return;
 state.contextMessages=data.messages;modal(`<h2 id="modal-title">收藏与置顶</h2><p>收藏仅自己可见；置顶对当前会话成员可见。最多显示最近 200 条。</p><div class="context-messages">${data.messages.map(m=>messageMarkup(m,{context:true})).join('')||'<div class="empty-row">还没有收藏或置顶的消息</div>'}</div>`,true);
}
function findMessage(id){return [...state.messages,...(state.contextMessages||[])].find(m=>String(m.id)===String(id));}
async function changeSaved(id,pin=false){
 if(!ensureUser())return;const m=findMessage(id);if(!m)return;
 await api(conversationPath()+'/saved',{message_id:Number(id),remove:!pin&&!!m.saved,pinned:pin?!m.pinned:!!m.pinned,unpin:pin&&!!m.pinned});
 await fetchMessages();paintMessages();if($('.modal .context-messages'))await savedModal();
}
function mentionModal(){const people=state.section==='friends'?[state.peer]:state.chatMembers||[];modal(`<h2 id="modal-title">提醒成员</h2><p>对方会在会话列表看到 @ 提醒。</p>${people.filter(p=>p.id!==state.user.id).map(p=>`<button class="member-row full" data-mention-id="${p.id}" data-mention-name="${esc(p.name)}">${avatar(p.name)} ${esc(p.name)}</button>`).join('')||'<p class="muted">暂时没有其他成员，先邀请伙伴加入吧。</p>'}`);}
function transferStatus(text,error=false){state.transfer=text;const slot=$('#transfer-status');if(slot){slot.textContent=text;slot.classList.toggle('transfer-error',error);}}
function fileActions(file){return `<button class="icon-button" data-file-manage="${file.id}" data-file-kind="${file.file_type|| (state.fileMode==='shared'?'shared':'personal')}" title="管理 ${esc(file.name)}" aria-label="管理 ${esc(file.name)}">${icon('more')}</button>`;}
function folderOptions(kind,current=null,exclude=null){const folders=kind==='shared'?state.sharedFolders||[]:state.folders;function label(f){const parts=[f.name];let p=f.parent_id;const seen=new Set([f.id]);while(p&&!seen.has(p)){seen.add(p);const parent=folders.find(x=>x.id===p);if(!parent)break;parts.unshift(parent.name);p=parent.parent_id;}return parts.join(' / ');}return `${kind==='shared'?'<option value="">工作区根目录</option>':''}${folders.filter(f=>f.id!==exclude).map(f=>`<option value="${f.id}" ${f.id===current?'selected':''}>${esc(label(f))}</option>`).join('')}`;}
async function refreshFiles(){if(state.fileMode==='shared')await refreshDetails();else await loadFolderFiles();render();}
async function manageFile(id,kind){
 if(!ensureUser())return;const f=[...state.files,...state.personalFiles,...(state.trash||[])].find(x=>x.id===id);if(!f)return;
 const base=fileBase(kind)+'/'+id;
 modal(`<h2 id="modal-title">${esc(f.name)}</h2>${f.deleted?'<p>文件在回收站中，恢复后会回到原文件夹。</p><button class="button primary full" id="restore-file">恢复文件</button>':`<form id="file-manage-form"><label>文件名<input name="name" required maxlength="180" value="${esc(f.name)}"></label><label>所在文件夹<select name="folder_id">${folderOptions(kind,f.folder_id)}</select></label><p id="form-error" class="form-error" role="alert"></p><button class="button primary">保存</button></form><div class="file-manage-actions"><button class="button" id="file-versions">历史版本 · v${f.revision||1}</button><button class="button" id="trash-file">移入回收站</button></div>`}`);
 if(f.deleted){$('#restore-file').onclick=async()=>{try{await api(base+'/manage',{action:'restore'});closeModal();await refreshFiles();toast('文件已恢复');}catch(e){toast(e.message);}};return;}
 $('#file-manage-form').onsubmit=async e=>{e.preventDefault();const values=Object.fromEntries(new FormData(e.target));const submit=$('button',e.target);submit.disabled=true;try{await api(base+'/manage',{action:'rename',name:values.name});await api(base+'/manage',{action:'move',folder_id:values.folder_id});closeModal();await refreshFiles();toast('文件已更新');}catch(e){formError(e);}finally{submit.disabled=false;}};
 $('#trash-file').onclick=async()=>{try{await api(base+'/manage',{action:'trash'});closeModal();await refreshFiles();toast('已移入回收站，可随时恢复');}catch(e){toast(e.message);}};
 $('#file-versions').onclick=()=>versionsModal(f,kind);
}
async function versionsModal(file,kind){
 const base=fileBase(kind)+'/'+file.id,data=await api(base+'/versions');modal(`<h2 id="modal-title">${esc(file.name)} · 历史版本</h2><p>当前版本 v${data.revision}。恢复旧版本时会保留当前内容。</p>${data.versions.map(v=>`<div class="version-row"><div><strong>v${v.revision} · ${esc(v.name)}</strong><small>${esc(new Date(v.created*1000).toLocaleString('zh-CN'))} · ${size(v.size)}</small></div><button class="button" data-version-id="${v.id}">恢复此版本</button></div>`).join('')||'<p class="muted">更新同名文件后，旧内容会保存在这里。</p>'}`);
 for(const b of document.querySelectorAll('[data-version-id]'))b.onclick=async()=>{b.disabled=true;try{await api(base+'/manage',{action:'restore-version',version_id:b.dataset.versionId});closeModal();await refreshFiles();toast('已恢复为新版本，原内容仍可找回');}catch(e){toast(e.message);b.disabled=false;}};
}
function collisionChoice(name){return new Promise(resolve=>{modal(`<h2 id="modal-title">存在同名文件</h2><p>${esc(name)} 已经存在，选择如何保存。</p><div class="choice-buttons"><button class="button primary" id="replace-upload">更新原文件，保留历史版本</button><button class="button" id="keep-upload">保留两个文件</button><button class="button" id="cancel-upload">取消本次上传</button></div>`);let done=false;const finish=value=>{if(done)return;done=true;observer.disconnect();closeModal();resolve(value);};const root=$('.modal');const observer=new MutationObserver(()=>{if(!root.isConnected)finish(null);});observer.observe($('#modal-root'),{childList:true});$('#replace-upload').onclick=()=>finish('replace');$('#keep-upload').onclick=()=>finish('keep');$('#cancel-upload').onclick=()=>finish(null);});}
function attachmentStorageChoice(group){return new Promise(resolve=>{
 modal(`<h2 id="modal-title">附件保存到哪里？</h2><p>本次选择适用于这次上传的全部文件。</p><div class="choice-buttons"><button class="button primary" id="storage-group">仅保存到本群附件库</button><p class="muted">仅本群成员可访问，不加入工作区文件库。</p><button class="button" id="storage-workspace">添加到工作区文件库</button><p class="muted">「${esc(group.workspace_name||'关联工作区')}」全体成员可访问，其他关联群也能在工作区查到。聊天中仍显示附件。</p><button class="button" id="storage-cancel">取消上传</button></div>`);
 let done=false;const finish=value=>{if(done)return;done=true;observer.disconnect();closeModal();resolve(value);};const root=$('.modal');const observer=new MutationObserver(()=>{if(!root.isConnected)finish(null);});observer.observe($('#modal-root'),{childList:true});$('#storage-group').onclick=()=>finish('group');$('#storage-workspace').onclick=()=>finish('workspace');$('#storage-cancel').onclick=()=>finish(null);
});}
function sharedFolderModal(){simpleForm('新建工作区文件夹','<label>名称<input name="name" required maxlength="100"></label>',async data=>{const result=await api(`/api/workspaces/${state.workspace.id}/folders`,{...data,parent_id:state.sharedFolder||null});state.sharedFolder=result.id;await refreshDetails();render();});}
function manageFolder(id,kind){const folders=kind==='shared'?state.sharedFolders:state.folders;const f=folders.find(x=>x.id===id);if(!f)return;simpleForm('整理文件夹',`<label>名称<input name="name" required maxlength="100" value="${esc(f.name)}"></label><label>上级文件夹<select name="parent_id"><option value="">${kind==='shared'?'工作区根目录':'作为文件工作区'}</option>${folderOptions(kind,f.parent_id,id)}</select></label>`,async data=>{await api(`/api/${kind==='shared'?'shared-folders':'folders'}/${id}/manage`,data);await refreshPersonal();await refreshDetails();render();});}
function updateConnection(ok){state.connected=ok;const footer=$('.list-footer');if(footer&&!state.demo)footer.innerHTML=`<span class="status-dot ${ok?'':'offline'}"></span><span>${ok?'已连接 · 数据保存在服务器':'连接中断，正在重试'}</span>`;}

function forgetConversation(kind,id){
 const key=kind+':'+id;
 for(const field of ['drafts','replies','mentionIds','pendingSends','scrollPositions','openRead','readSent'])if(state[field])delete state[field][key];
 if(chatKey()===key){state.request++;state.messages=[];state.contextMessages=[];state.failedUpload=null;state.transfer='';}
}
async function membersModal(){
 const group=state.channel;if(!group)return;
 if(!state.demo){const data=await api(`/api/channels/${group.id}/members`);if(state.channel?.id!==group.id)return;state.chatMembers=data.members;group.owner=data.owner;}
 const owner=group.owner===state.user.id;
 modal(`<h2 id="modal-title">群聊成员</h2><div class="member-list">${state.chatMembers.map(m=>`<div class="member-row">${avatar(m.name)}<span class="member-name">${esc(m.name)}${m.id===group.owner?' <small>群主</small>':''}${m.id===state.user.id?' <small>我</small>':''}</span>${owner&&m.id!==group.owner?`<button class="text-button remove-member" data-remove-member="${m.id}">移除</button>`:''}</div>`).join('')}</div><p class="muted">${group.visibility==='private'?'仅受邀成员可查看本群聊天记录。':'工作区成员可查看本群聊天记录，被移出的成员除外。'}</p>${owner?'<button class="button primary" data-action="group-invite">邀请加入本群</button>':'<p class="muted">群主可以邀请和移除成员。</p>'}`);
 for(const button of document.querySelectorAll('[data-remove-member]'))button.onclick=()=>removeMemberModal(group,state.chatMembers.find(m=>m.id===button.dataset.removeMember));
}
function removeMemberModal(group,member){
 if(!member||!ensureUser())return;
 modal(`<h2 id="modal-title">移除群成员</h2><p>确定将「${esc(member.name)}」移出「${esc(group.name)}」？</p><p class="invite-note">对方将不能查看或发送本群消息，也不能访问仅本群附件。${group.workspace_id?'工作区文件和其他群聊的访问权限保留。':'本群附件也将无法访问。'}本群已有邀请链接会失效，需要重新生成；之后可通过新链接邀请对方回来。</p><p id="form-error" class="form-error" role="alert"></p><div class="confirm-actions"><button class="button" id="cancel-remove">取消</button><button class="button primary" id="confirm-remove">确认移除</button></div>`);
 $('#cancel-remove').onclick=()=>membersModal().catch(e=>toast(e.message));
 $('#confirm-remove').onclick=async e=>{e.target.disabled=true;try{await api(`/api/channels/${group.id}/members/${member.id}/remove`,{});await refreshActivity();if(state.channel?.id===group.id){await selectChat('channel',group.id);await membersModal();}else closeModal();toast('已移除成员');}catch(error){formError(error);e.target.disabled=false;}};
}
function removeFriendModal(){
 if(!ensureUser())return;const peer=state.peer;if(!peer)return;
 modal(`<h2 id="modal-title">删除好友</h2><p>确定删除好友「${esc(peer.name)}」？</p><p class="invite-note">双方将从好友列表中移除，不能继续私聊或访问私聊附件。已有聊天记录保留，重新添加并接受好友申请后可继续查看。共同群聊和工作区的权限保留。</p><p id="form-error" class="form-error" role="alert"></p><div class="confirm-actions"><button class="button" data-action="close">取消</button><button class="button primary" id="confirm-remove">确认删除</button></div>`);
 $('#confirm-remove').onclick=async e=>{e.target.disabled=true;try{await api(`/api/friends/${peer.id}/remove`,{});closeModal();await refreshPersonal();await refreshActivity();render();toast('已删除好友');}catch(error){formError(error);e.target.disabled=false;}};
}

document.addEventListener('click',async e=>{
 const b=e.target.closest('button');if(!b)return;
 try{
  if(b.dataset.pinKind){if(!ensureUser())return;const kind=b.dataset.pinKind,id=b.dataset.pinId;await api(`/api/conversations/${kind}/${id}/state`,{pinned:!preference(kind,id).pinned});await refreshActivity();return;}
  if(b.dataset.reply){const m=findMessage(b.dataset.reply);if(!m)return;state.replies??={};state.replies[chatKey()]=m;closeModal();updateReply();$('#message-input')?.focus();return;}
  if(b.dataset.save){await changeSaved(b.dataset.save);return;}
  if(b.dataset.messagePin){await changeSaved(b.dataset.messagePin,true);return;}
  if(b.dataset.context){await viewContext(b.dataset.context);return;}
  if(b.dataset.mentionId){const input=$('#message-input');if(!input)return;input.value+=(input.value&&!/\s$/.test(input.value)?' ':'')+'@'+b.dataset.mentionName+' ';state.mentionIds??={};state.mentionIds[chatKey()]??=[];state.mentionIds[chatKey()].push(b.dataset.mentionId);closeModal();input.focus();saveDraft();return;}
  if(b.dataset.attachmentPreview){await attachmentPreview(b.dataset.attachmentPreview,b.dataset.fileKind,b.dataset.fileName);return;}
  if(b.dataset.attachmentDownload){attachmentDownload(b.dataset.attachmentDownload,b.dataset.fileKind,b.dataset.fileName);return;}
  if(b.dataset.fileManage){await manageFile(b.dataset.fileManage,b.dataset.fileKind);return;}
  if(b.dataset.sharedFolder!==undefined){state.sharedFolder=b.dataset.sharedFolder||null;state.fileMode='shared';state.showTrash=false;render();return;}
  if(b.dataset.folderManage){manageFolder(b.dataset.folderManage,b.dataset.fileKind);return;}
  switch(b.dataset.action){
   case 'cancel-reply':delete state.replies[chatKey()];updateReply();break;
   case 'mention':mentionModal();break;
   case 'saved':await savedModal();break;
   case 'group-invite':await groupInviteModal();break;
   case 'remove-friend':removeFriendModal();break;
   case 'shared-folder-new':if(ensureUser())sharedFolderModal();break;
   case 'trash':state.showTrash=!state.showTrash;render();break;
   case 'retry-upload':if(state.failedUpload)await uploadFiles(state.failedUpload.files,state.failedUpload);break;
  }
 }catch(error){toast(error.message);}
});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)markVisibleRead();});

async function attachmentPreview(id,kind,name){
 const demo=state.demo,example=demoFiles.find(f=>f.id===id);modal(`<div class="preview-title"><h2 id="modal-title">${esc(name)}</h2><button class="button" data-attachment-download="${id}" data-file-kind="${kind}" data-file-name="${esc(name)}">下载</button></div><div id="preview-content">正在读取…</div>`,true);const root=$('#preview-content');try{const data=demo?example:await api(fileBase(kind)+'/'+id+'/preview');if(root.isConnected)root.innerHTML=`<pre class="code-preview"><code>${esc(data.content)}</code></pre>`;}catch(error){if(root.isConnected)root.textContent=error.message;}
}
function attachmentDownload(id,kind,name){const a=document.createElement('a');a.href=state.demo?URL.createObjectURL(new Blob([demoFiles.find(f=>f.id===id)?.content||''],{type:'text/plain;charset=utf-8'})):fileBase(kind)+'/'+id;a.download=name;a.click();if(state.demo)setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
async function groupInviteModal(){
 if(!ensureUser())return;const group=state.channel;if(group.owner!==state.user.id){toast('请联系群主生成邀请链接');return;}
 modal(`<h2 id="modal-title">邀请加入 ${esc(group.name)}</h2><p>对方可查看本群的全部聊天记录与附件。${group.workspace_id?`还会加入工作区「${esc(group.workspace_name)}」，访问该工作区全部文件和公开群聊。`:'此群聊未关联工作区。'}仅受邀成员群聊需要分别邀请。</p><button class="button primary full" id="generate-group-invite">生成 7 天有效的邀请链接</button><div id="invite-result"></div><p id="form-error" class="form-error" role="alert"></p>`);
 $('#generate-group-invite').onclick=async e=>{e.target.disabled=true;try{const result=await api(`/api/channels/${group.id}/invite`,{});showInviteResult(result.token);}catch(error){formError(error);}finally{e.target.disabled=false;}};
}
function showInviteResult(token){const url=location.origin+'/?invite='+token;$('#invite-result').innerHTML=`<label>邀请链接<input readonly id="invite-url" value="${esc(url)}"></label><button class="button full" id="copy-invite">复制邀请链接</button><p class="invite-note">${['127.0.0.1','localhost'].includes(location.hostname)?'当前是本机地址。邀请其他电脑前，请通过局域网地址或部署后的域名打开，再生成链接。':'对方打开后会先看到访问范围，确认后才会加入。'}</p>`;$('#copy-invite').onclick=async()=>{try{await navigator.clipboard.writeText(url);toast('已复制');}catch{$('#invite-url').select();toast('请按 Ctrl+C 复制');}};}
async function reviewInvite(token){
 const data=await api('/api/join/preview?token='+encodeURIComponent(token));modal(`<h2 id="modal-title">加入${data.kind==='group'?'群聊':'工作区'}「${esc(data.name)}」</h2><p>加入后可访问：</p><p class="invite-note">${esc(data.scope)}</p><p id="form-error" class="form-error" role="alert"></p><button class="button primary full" id="accept-invite">确认加入</button><button class="button full" id="skip-invite">暂不加入</button>`);
 $('#skip-invite').onclick=()=>{pendingInvite=null;history.replaceState({},'',location.pathname);closeModal();};
 $('#accept-invite').onclick=async e=>{e.target.disabled=true;try{const joined=await api('/api/join',{token});pendingInvite=null;history.replaceState({},'',location.pathname);closeModal();await loadAccount(joined.id);if(joined.channel_id)await selectChat('channel',joined.channel_id);toast('已加入');}catch(error){formError(error);e.target.disabled=false;}};
}
