icons.settings='<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3" fill="currentColor"/><circle cx="15" cy="17" r="3" fill="currentColor"/>';
const state={demo:true,user:null,workspaces:[],workspace:null,channels:[],members:[],files:[],messages:[],channel:null,friends:[],peer:null,folders:[],folder:null,personalFiles:[],homeView:'files',groups:[],section:'home',fileMode:'personal',search:'',setting:'account',drafts:{},request:0,busy:false};
Object.assign(state,{activity:{dm:{},workspace_pins:[]},chatMembers:[],sharedFolders:[],sharedFolder:null,trash:[],showTrash:false,replies:{},mentionIds:{},readSent:{},openRead:{},scrollPositions:{},pendingSends:{},connected:true,transfer:''});
let pendingInvite=new URLSearchParams(location.search).get('invite');
const labels={home:'主页',friends:'好友',files:'文件',settings:'设置'};
const showingFiles=()=>state.section==='files'||(state.section==='home'&&state.homeView==='files');
const accepted=()=>state.friends.filter(f=>f.status==='accepted');
const currentFolder=()=>state.folders.find(f=>f.id===state.folder);
const chatKey=()=>state.section==='friends'?'dm:'+state.peer?.id:'group:'+state.channel?.id;
const chatTarget=()=>state.section==='friends'?state.peer:state.channel;
const chatPath=()=>state.section==='friends'?`/api/dm/${state.peer?.id}`:`/api/channels/${state.channel?.id}/messages`;
function ensureUser(){if(state.demo){authModal('register');return false;}return true;}
function ensureWorkspace(){if(!ensureUser())return false;if(!state.workspace){workspaceModal();return false;}return true;}
function loadDemo(){Object.assign(state,{activity:{dm:{},workspace_pins:[]},chatMembers:[],sharedFolders:[],sharedFolder:null,trash:[],showTrash:false,replies:{},mentionIds:{},readSent:{},openRead:{},scrollPositions:{},pendingSends:{},contextMessages:[],connected:true,failedUpload:null,transfer:''});Object.assign(state,{demo:true,user:{id:'demo',name:'访客'},workspaces:[{id:'demo',name:'我的工作区',owner:'demo'}],workspace:{id:'demo',name:'我的工作区',owner:'demo'},channels:[{id:'general',name:'综合讨论',description:'项目进展与日常交流'},{id:'dev',name:'开发协作',description:'代码与实现讨论'},{id:'resources',name:'资料分享',description:'项目文档与共享资料'}],members:[{id:'a',name:'林小满'},{id:'b',name:'陈一'},{id:'c',name:'苏然'}],files:demoFiles,friends:[{id:'a',name:'林小满',status:'accepted'},{id:'b',name:'陈一',status:'accepted'},{id:'c',name:'苏然',status:'accepted'}],folders:[{id:'project',name:'我的项目',parent_id:null},{id:'docs',name:'项目文档',parent_id:'project'},{id:'src',name:'源代码',parent_id:'project'},{id:'design',name:'设计资料',parent_id:null}],folder:'project',peer:null,section:'home',fileMode:'personal',search:'',drafts:{}});state.groups=state.channels.map(c=>({...c,workspace_id:'demo',workspace_name:'我的工作区'}));state.homeView='chat';state.channel=state.groups[0];state.peer=state.friends[0];state.chatMembers=state.members;demoMessages();render();}
function demoMessages(){const now=Date.now()/1000;state.messages=state.section==='friends'?[{id:1,author:state.peer.name,user_id:state.peer.id,body:state.peer.id==='b'?'项目代码已经整理好了，文件里可以查看。':'你好，之后我们就在这里沟通项目吧。',created:now-600},{id:2,author:'我',user_id:'demo',body:'好，有新的进展随时联系。',created:now-480}]:state.channel?.id==='general'?[{id:1,author:'林小满',user_id:'a',body:'大家好，项目相关的沟通就放在这个群里。',created:now-1800},{id:2,author:'陈一',user_id:'b',body:'项目说明和代码已经整理好了，点左侧「文件」就能找到。',created:now-1400},{id:3,author:'苏然',user_id:'c',body:'收到，设计资料也会同步更新。',created:now-1000}]:[{id:1,author:'陈一',user_id:'b',body:state.channel?.id==='dev'?'这里讨论开发问题，代码可以用代码块分享。':'项目资料已经上传，点击右上角文件图标查看。',created:now-800}];}
function saveDraft(){const input=$('#message-input');if(input){state.drafts[chatKey()]=input.value;const scroll=$('#message-scroll');if(scroll)state.scrollPositions[chatKey()]=scroll.scrollTop;}}
function render(){
 $('#app').innerHTML=`<div class="shell"><nav class="rail" aria-label="主导航"><button class="logo" data-section="home" title="同频">t<span>.</span></button>${[['home','home'],['friends','users'],['files','folder']].map(([s,i])=>railItem(s,i)).join('')}<div class="rail-spacer"></div>${railItem('settings','settings')}<button class="user-button" data-action="account" title="${esc(state.user?.name)}">${esc(state.user?.name?.slice(0,1)||'我')}</button></nav><aside class="list-pane"><header class="list-header"><h1>${labels[state.section]}</h1><button class="icon-button" data-action="${state.section==='home'?'channel':state.section==='friends'?'friend':state.section==='files'?'folder-root':'account'}" aria-label="${state.section==='home'?'创建群聊':state.section==='friends'?'添加好友':state.section==='files'?'添加文件工作区':'账户'}">${icon('plus')}</button></header><div id="list-content">${listContent()}</div><footer class="list-footer">${state.demo?'<span>演示模式</span><button data-action="register">登录 / 注册</button>':'<span class="status-dot"></span><span>已保存到服务器</span>'}</footer></aside><main class="main" id="main">${mainContent()}</main></div><input id="file-input" type="file" multiple hidden>`;
 bind();if(['home','friends'].includes(state.section)){paintMessages(true);returnToRead();}if(!state.demo)updateConnection(state.connected);
}
function railItem(s,i){return `<button class="rail-item ${state.section===s?'selected':''}" data-section="${s}" aria-current="${state.section===s?'page':'false'}">${icon(i)}<span>${labels[s]}</span></button>`;}
function listContent(){
 if(state.section==='home')return `<div class="list-label">工作区 <span>${state.workspaces.length}</span></div>${ordered(state.workspaces,'workspace').map(w=>`<div class="list-entry"><button class="list-item ${state.homeView==='files'&&state.workspace?.id===w.id?'active':''}" data-workspace="${w.id}" aria-pressed="${state.homeView==='files'&&state.workspace?.id===w.id}">${icon('home')}<span>${esc(w.name)}</span></button>${pinButton('workspace',w.id,w.name)}</div>`).join('')}<button class="list-add" data-action="workspace">${icon('plus')} 创建工作区</button><div class="list-label requests-label">群聊 <span>${state.groups.length}</span></div>${ordered(state.groups,'group').map(c=>`<div class="list-entry"><button class="list-item ${state.homeView==='chat'&&state.channel?.id===c.id?'active':''}" data-channel="${c.id}"><span class="hash">${c.visibility==='private'?'·':'#'}</span><span class="group-label">${esc(c.name)}<small>${esc(c.workspace_name||'独立群聊')}${c.visibility==='private'?' · 仅受邀成员':''}</small></span>${badges('group',c.id)}</button>${pinButton('group',c.id,c.name)}</div>`).join('')}<button class="list-add" data-action="channel">${icon('plus')} 创建群聊</button><button class="list-add" data-action="invite">${icon('users')} 邀请加入工作区</button>`;
 if(state.section==='friends')return `<div class="list-label">好友列表 <span>${accepted().length}</span></div>${ordered(accepted(),'dm').map(f=>`<div class="list-entry"><button class="list-item ${state.peer?.id===f.id?'active':''}" data-peer="${f.id}">${avatar(f.name)}<span>${esc(f.name)}</span>${badges('dm',f.id)}</button>${pinButton('dm',f.id,f.name)}</div>`).join('')}<button class="list-add" data-action="friend">${icon('plus')} 添加好友</button>${state.friends.some(f=>f.status==='pending')?'<div class="list-label requests-label">好友申请</div>':''}${state.friends.filter(f=>f.status==='pending').map(f=>`<div class="request-item"><strong>${esc(f.name)}</strong>${f.recipient===state.user.id?`<div><button data-accept="${f.request_id}">接受</button><button data-decline="${f.request_id}">忽略</button></div>`:'<small>等待对方接受</small>'}</div>`).join('')}`;
 if(state.section==='files')return `<div class="list-label">我的文件工作区</div>${state.folders.filter(f=>!f.parent_id).map(f=>`<button class="list-item ${state.fileMode==='personal'&&rootFolder()===f.id?'active':''}" data-folder="${f.id}">${icon('folder')}<span>${esc(f.name)}</span></button>`).join('')}<button class="list-add" data-action="folder-root">${icon('plus')} 添加文件工作区</button><div class="list-label requests-label">团队共享</div>${ordered(state.workspaces,'workspace').map(w=>`<button class="list-item ${state.fileMode==='shared'&&state.workspace?.id===w.id?'active':''}" data-shared="${w.id}">${icon('users')}<span>${esc(w.name)}</span></button>`).join('')}`;
 return `<div class="list-label">偏好与账户</div><button class="list-item ${state.setting==='account'?'active':''}" data-setting="account">${icon('users')} 个人资料</button><button class="list-item ${state.setting==='workspace'?'active':''}" data-setting="workspace">${icon('home')} 工作区管理</button>`;
}
function rootFolder(){let f=currentFolder();while(f?.parent_id)f=state.folders.find(p=>p.id===f.parent_id);return f?.id;}
function header(title,subtitle,actions=''){return `<header class="main-header"><button class="icon-button mobile-back" data-action="back" aria-label="返回列表">${icon('menu')}</button><div class="main-title"><h2>${title}</h2>${subtitle?`<p>${subtitle}</p>`:''}</div><div class="header-actions">${actions}</div></header>`;}
function mainContent(){
 if(state.section==='settings')return settingsView();
 if(showingFiles())return filesView();
 const target=chatTarget(),dm=state.section==='friends';
 if(!target)return header(dm?'好友':'群聊','')+`<div class="empty">${icon(dm?'users':'chat')}<h3>${dm?'选择一位好友开始聊天':'创建一个群聊'}</h3><p>${dm?'添加好友，对方接受后即可私聊。':'一起讨论项目，需要时关联工作区保存资料。'}</p><button class="button primary" data-action="${dm?'friend':'channel'}">${dm?'添加好友':'创建群聊'}</button></div>`;
 const linked=!dm&&target.workspace_id;
 return header(`${dm?avatar(target.name):'<span class="hash">#</span>'}${esc(target.name)}`,dm?'私聊 · 仅你和对方可见':`${linked?'工作区：'+esc(target.workspace_name||state.workspace?.name):'独立群聊'} · ${state.chatMembers.length} 位成员 · ${target.visibility==='private'?'仅受邀成员':'工作区公开'}`,`<button class="button" data-action="history" title="查找聊天记录">${icon('search')} 查找记录</button>${!dm?'<button class="button" data-action="group-library" title="查看仅本群保存的附件">'+icon('clip')+'本群附件</button>':''}${linked?'<button class="button" data-action="group-files" title="打开关联工作区">'+icon('folder')+esc(target.workspace_name||'工作区文件')+'</button>':''}<button class="icon-button" data-action="saved" title="收藏与置顶" aria-label="收藏与置顶">${icon('bookmark')}</button>${dm?'<button class="icon-button" data-action="remove-friend" title="删除好友" aria-label="删除好友">'+icon('users')+'</button>':''}${!dm?'<button class="icon-button" data-action="members" title="查看成员" aria-label="查看成员">'+icon('users')+'</button>':''}`)+`<section class="chat"><div class="message-scroll" id="message-scroll"><div class="date-divider">${state.demo?'示例聊天':'最近 500 条消息 · 更早内容可在右上角查找'}</div><div id="messages"></div></div><form id="composer" class="composer"><div id="reply-slot">${replyBanner()}</div><textarea id="message-input" maxlength="12000" aria-label="消息内容" placeholder="发送消息给 ${esc(target.name)}" rows="3">${esc(state.drafts[chatKey()]||'')}</textarea><div class="composer-toolbar"><div><button type="button" class="icon-button" data-action="upload" title="上传聊天附件" aria-label="上传聊天附件">${icon('clip')}</button><button type="button" class="icon-button" data-action="mention" title="提醒成员" aria-label="提醒成员">@</button><button type="button" class="icon-button" data-action="code" title="插入代码块">${icon('code')}</button></div><div><small>Enter 发送，Shift + Enter 换行</small><button class="send-button" aria-label="发送消息" ${state.busy?'disabled':''}>${icon('send')}</button></div></div></form><div class="transfer-bar"><span id="transfer-status" role="status">${esc(state.transfer||'')}</span><button class="text-button" data-action="retry-upload" ${state.failedUpload?'':'hidden'}>重试上传</button></div><div class="chat-foot">${state.demo?'演示内容 · 登录后开始聊天':''}</div></section>`;
}
function historyModal(filesOnly=false){
 const target=chatTarget();if(!target)return;
 const dm=state.section==='friends',demo=state.demo;
 const endpoint=dm?`/api/dm/${target.id}/history`:`/api/channels/${target.id}/history`;
 const examples=[...state.messages.map(m=>({...m,id:String(m.id),kind:'message'})),...(!dm?demoFiles.map(f=>({...f,kind:'file',body:f.name,storage:'workspace'})):[])];
 modal(`<h2 id="modal-title">查找聊天记录</h2><p>${esc(target.name)} · ${demo?'演示记录':'全部历史'}<br>${dm?'仅查找你们之间的消息与附件。':'聊天内容仅查找本群；文件可选择本群附件库或关联工作区文件库。'}</p><form id="history-form" class="history-form"><label class="history-keyword">关键词<input name="q" maxlength="200" placeholder="搜索聊天内容或文件名"></label><div class="history-filters"><label>类型<select name="type"><option value="all">全部</option><option value="messages">聊天内容</option><option value="files">文件</option></select></label>${!dm?`<label>文件范围<select name="file_scope"><option value="conversation">本群聊天中的全部附件</option><option value="group">本群附件库 · 仅本群</option>${target.workspace_id?'<option value="workspace">工作区文件库 · 全部共享文件</option>':''}</select></label>`:''}<label>开始日期<input type="date" name="since" min="1970-01-01" max="9999-12-30"></label><label>结束日期<input type="date" name="until" min="1970-01-01" max="9999-12-30"></label></div><div class="history-actions"><span class="muted">按本地日期筛选，包含结束当天</span><button type="reset" class="button">重置</button><button class="button primary">查找</button></div></form><p id="history-status" role="status" aria-live="polite"></p><div id="history-results" class="history-results"></div><button class="button full" id="history-more" hidden>加载更多</button>`,true);
 const root=$('.modal'),form=$('#history-form'),results=$('#history-results'),status=$('#history-status'),more=$('#history-more');
 root.classList.add('history-modal');
 let version=0,cursor=null,query=null,items=[];
 function row(item,index){return `<article class="history-result"><div class="message-meta"><strong>${esc(item.author)}</strong><time>${esc(new Date(item.created*1000).toLocaleString('zh-CN',{hour12:false}))}</time><span class="history-kind">${item.kind==='file'?(item.storage==='group'?'仅本群附件':item.storage==='workspace'?'工作区文件':'文件'):'消息'}</span></div>${item.kind==='file'?`<div class="history-file">${icon(fileIcon({name:item.body}))}<strong>${esc(item.body)}</strong><span class="muted">${size(item.size)}</span><button type="button" class="button" data-history-preview="${index}">预览</button><button type="button" class="icon-button" data-history-download="${index}" aria-label="下载 ${esc(item.body)}">${icon('download')}</button></div>`:`<div class="message-body">${messageBody(item.body)}</div><button type="button" class="text-button" data-history-context="${esc(item.id)}">查看上下文</button>`}</article>`;}
 async function search(append=false){
  const ticket=++version;
  if(!append){
   more.hidden=true;items=[];cursor=null;results.innerHTML='';
   const data=new FormData(form);query=new URLSearchParams({q:data.get('q').trim(),type:data.get('type')});if(!dm)query.set('file_scope',data.get('file_scope')||'conversation');
   $('#modal-title').textContent=query.get('type')==='files'&&!dm?(query.get('file_scope')==='workspace'?'工作区文件库':query.get('file_scope')==='group'?'本群附件库':'本群聊天附件'):'查找聊天记录';
   const start=data.get('since'),end=data.get('until');
   if(start&&end&&start>end){status.textContent='开始日期不能晚于结束日期';return;}
   for(const [name,value] of [['since',start],['until',end]])if(value){const date=new Date(value+'T00:00:00');if(name==='until')date.setDate(date.getDate()+1);query.set(name,String(date.getTime()/1000));}
  }
  status.textContent='正在查找…';results.setAttribute('aria-busy','true');more.disabled=true;
  try{
   const params=new URLSearchParams(query);if(append&&cursor)params.set('cursor',JSON.stringify(cursor));
   let data;
   if(demo){const q=params.get('q').toLowerCase(),kind=params.get('type'),scope=params.get('file_scope');const filtered=examples.filter(m=>(m.kind!=='file'||scope==='workspace'||(scope!=='group'&&m.channel_id===target.id))&&(kind==='all'||m.kind===(kind==='files'?'file':'message'))&&m.body.toLowerCase().includes(q)&&(!params.has('since')||m.created>=Number(params.get('since')))&&(!params.has('until')||m.created<Number(params.get('until')))).sort((a,b)=>b.created-a.created);data={items:filtered,next_cursor:null};}
   else data=await api(endpoint+'?'+params);
   if(ticket!==version||!root.isConnected)return;
   items=append?[...items,...data.items]:data.items;cursor=data.next_cursor;
   results.innerHTML=items.map(row).join('');more.hidden=!cursor;
   status.textContent=items.length?`已显示 ${items.length} 条${cursor?'，可继续加载':'，已显示全部结果'}`:'没有找到匹配记录，试试其他关键词或日期。';
  }catch(error){if(ticket===version&&root.isConnected)status.textContent='查找失败：'+error.message;}
  finally{if(ticket===version){more.disabled=false;results.removeAttribute('aria-busy');}}
 }
 form.onsubmit=e=>{e.preventDefault();search();};
 const fileScope=$('select[name=file_scope]',form),type=$('select[name=type]',form);
 if(fileScope){fileScope.onchange=()=>{type.value='files';search();};type.onchange=()=>search();}
 if(filesOnly){type.value='files';if(fileScope)fileScope.value='group';}
 form.onreset=()=>setTimeout(()=>{if(root.isConnected)search();},0);
 more.onclick=()=>search(true);
 results.onclick=async e=>{
  const button=e.target.closest('button');if(!button)return;
  if(button.dataset.historyContext){await viewContext(button.dataset.historyContext);return;}
  const preview=button.dataset.historyPreview,download=button.dataset.historyDownload;
  if(preview===undefined&&download===undefined)return;
  const item=items[Number(preview??download)];if(!item)return;
  if(download!==undefined){const a=document.createElement('a');a.href=demo?URL.createObjectURL(new Blob([item.content],{type:'text/plain;charset=utf-8'})):fileBase(dm?'dm':'shared')+'/'+item.id;a.download=item.body;a.click();if(demo)setTimeout(()=>URL.revokeObjectURL(a.href),1000);return;}
  const article=button.closest('article');const existing=$('.history-preview',article);if(existing){existing.remove();button.textContent='预览';return;}
  const block=document.createElement('div');block.className='history-preview';block.textContent='正在读取…';article.append(block);button.textContent='收起';
  try{const data=demo?item:await api(fileBase(dm?'dm':'shared')+'/'+item.id+'/preview');if(block.isConnected)block.innerHTML=`<pre class="code-preview"><code>${esc(data.content)}</code></pre>`;}
  catch(error){if(block.isConnected)block.textContent=error.message;}
 };
 search();
}
function allShownFiles(){return state.fileMode==='shared'?state.files:state.personalFiles;}
function breadcrumbs(){let f=currentFolder(),parts=[];while(f){parts.unshift(`<button data-folder="${f.id}">${esc(f.name)}</button>`);f=state.folders.find(p=>p.id===f.parent_id);}return parts.join(`<span>/</span>`);}
function fileRows(){
 const shared=state.fileMode==='shared',q=state.search.toLowerCase();
 const folders=state.showTrash?[]:shared?(state.sharedFolders||[]).filter(f=>(f.parent_id||null)===(state.sharedFolder||null)&&f.name.toLowerCase().includes(q)):state.folders.filter(f=>f.parent_id===state.folder&&f.name.toLowerCase().includes(q));
 const files=(state.showTrash?state.trash||[]:allShownFiles()).filter(f=>(state.showTrash||!shared||(f.folder_id||null)===(state.sharedFolder||null))&&f.name.toLowerCase().includes(q));
 return folders.map(f=>`<div class="file-row"><button ${shared?'data-shared-folder':'data-folder'}="${f.id}" class="file-name">${icon('folder')}<strong>${esc(f.name)}</strong></button><span>文件夹</span><span>—</span><button class="icon-button" data-folder-manage="${f.id}" data-file-kind="${shared?'shared':'personal'}" title="整理 ${esc(f.name)}" aria-label="整理 ${esc(f.name)}">${icon('more')}</button></div>`).join('')+files.map(f=>`<div class="file-row"><button class="file-name" ${f.deleted?'data-file-manage':'data-preview'}="${f.id}" data-file-kind="${f.file_type|| (shared?'shared':'personal')}">${icon(fileIcon(f))}<strong>${esc(f.name)}${f.revision>1?` <small>v${f.revision}</small>`:''}</strong></button><span>${esc(f.author||state.user.name)}</span><span>${size(f.size)}</span><div class="file-row-actions">${!f.deleted?`<button class="icon-button" data-download="${f.id}" title="下载 ${esc(f.name)}" aria-label="下载 ${esc(f.name)}">${icon('download')}</button>`:''}${fileActions(f)}</div></div>`).join('')||'<div class="empty-row">'+(q?'没有匹配的文件':state.showTrash?'回收站为空':'这个文件夹还没有内容')+'</div>';
}
function filesView(){
 const shared=state.fileMode==='shared',name=shared?state.workspace?.name:currentFolder()?.name;
 const folder=shared?state.sharedFolders?.find(f=>f.id===state.sharedFolder):currentFolder();
 let path='';if(shared){const parts=[];let f=folder;while(f){parts.unshift(`<button data-shared-folder="${f.id}">${esc(f.name)}</button>`);f=state.sharedFolders.find(p=>p.id===f.parent_id);}path=`<button data-shared-folder="">全部文件</button>${parts.length?'<span>/</span>'+parts.join('<span>/</span>'):''}`;}else path=breadcrumbs();
 return header(esc(name||'我的文件'),shared?'项目资料 · 工作区成员共享':'个人文件 · 仅自己可见',`${name?`<button class="icon-button ${state.showTrash?'is-pinned':''}" data-action="trash" title="${state.showTrash?'返回文件':'回收站'}" aria-label="${state.showTrash?'返回文件':'回收站'}">${icon('trash')}</button><button class="button" data-action="${shared?'shared-folder-new':'folder-child'}">新建文件夹</button>`:''}<button class="button primary" data-action="upload">${icon('plus')} 上传文件</button>`)+`<section class="files-body" id="drop-zone">${name?`<div class="file-tools"><div class="breadcrumbs">${state.showTrash?'回收站 · 文件可恢复':path}${folder&&!state.showTrash?`<button class="icon-button" data-folder-manage="${folder.id}" data-file-kind="${shared?'shared':'personal'}" aria-label="整理当前文件夹">${icon('more')}</button>`:''}</div><label class="search">${icon('search')}<input id="file-search" aria-label="搜索文件" placeholder="${state.showTrash?'搜索回收站':'搜索当前文件夹'}" value="${esc(state.search)}"></label></div><div class="file-row table-head"><span>名称</span><span>上传者</span><span>大小</span><span></span></div><div id="file-rows">${fileRows()}</div><p class="file-foot">${state.showTrash?'文件保留至手动恢复。':'拖放上传 · 单个文件最大 10 MB · 同名文件可保留历史版本'}</p><div class="transfer-bar"><span id="transfer-status" role="status">${esc(state.transfer||'')}</span><button class="text-button" data-action="retry-upload" ${state.failedUpload?'':'hidden'}>重试上传</button></div>`:`<div class="empty">${icon('folder')}<h3>添加一个文件工作区</h3><p>按项目保存资料与代码，文件夹里可以继续创建子文件夹。</p><button class="button primary" data-action="folder-root">添加文件工作区</button></div>`}</section>`;
}
function settingsView(){return header(state.setting==='account'?'个人资料':'工作区管理','')+`<section class="settings-body">${state.setting==='account'?`<form id="profile-form"><label>昵称<input name="name" value="${esc(state.user.name)}" maxlength="40" required></label><label>邮箱<input value="${esc(state.user.email||'演示账号')}" readonly></label><button class="button primary">保存资料</button></form><div class="settings-rule"></div><p class="muted">界面配色：蓝 / 白 / 黑</p><button class="button" data-action="${state.demo?'register':'logout'}">${state.demo?'登录 / 注册':'退出登录'}</button>`:`<h3>我的工作区</h3>${state.workspaces.map(w=>`<div class="manage-row"><span>${esc(w.name)}</span><button class="button" data-manage="${w.id}">打开</button></div>`).join('')}<button class="button primary" data-action="workspace">创建工作区</button>`}</section>`;}
function messageBody(body){return body.split(/(```[\s\S]*?```)/g).map(p=>p.startsWith('```')?`<pre><code>${esc(p.slice(3,-3).replace(/^\w*\n/,''))}</code></pre>`:`<span>${esc(p)}</span>`).join('');}
function paintMessages(force=false){
 const box=$('#messages');if(!box)return;const markup=state.messages.map(m=>messageMarkup(m)).join('')||'<div class="empty-row">还没有消息，打个招呼吧。</div>';
 if(box.dataset.markup===markup&&!force)return;const scroll=$('#message-scroll'),bottom=scroll.scrollHeight-scroll.scrollTop-scroll.clientHeight<80,position=scroll.scrollTop;box.innerHTML=markup;box.dataset.markup=markup;
 if(bottom||force)scroll.scrollTop=scroll.scrollHeight;else scroll.scrollTop=position;
 if(!force)markVisibleRead();
}
function bind(){
 $('#composer')?.addEventListener('submit',sendMessage);
 $('#message-input')?.addEventListener('input',saveDraft);
 $('#message-scroll')?.addEventListener('scroll',()=>{clearTimeout(state.readTimer);state.readTimer=setTimeout(markVisibleRead,300);});
 $('#message-input')?.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('#composer').requestSubmit();}});
 $('#file-input').addEventListener('change',e=>uploadFiles([...e.target.files]));
 $('#file-search')?.addEventListener('input',e=>{state.search=e.target.value;$('#file-rows').innerHTML=fileRows();});
 $('#profile-form')?.addEventListener('submit',async e=>{e.preventDefault();if(!ensureUser())return;try{const name=new FormData(e.target).get('name');await api('/api/profile',{name});state.user.name=name;toast('个人资料已保存');render();}catch(e){toast(e.message);}});
 const drop=$('#drop-zone');if(drop){drop.ondragover=e=>{e.preventDefault();drop.classList.add('dragging');};drop.ondragleave=()=>drop.classList.remove('dragging');drop.ondrop=e=>{e.preventDefault();drop.classList.remove('dragging');uploadFiles([...e.dataTransfer.files]);};}
}
async function openSection(section){saveDraft();state.section=section;state.transfer='';state.search='';state.request++;state.showTrash=false;if(section==='home'&&state.homeView==='files'){state.fileMode='shared';await refreshDetails();render();}else if(section==='home'||section==='friends'){state.messages=[];const key=chatKey();state.openRead[key]=preference(section==='friends'?'dm':'group',chatTarget()?.id).read_id||0;render();await fetchMessages();paintMessages(true);returnToRead();await markVisibleRead();}else if(section==='files'){await loadFolderFiles();render();}else render();}
async function selectChat(kind,id){
 saveDraft();state.request++;state.transfer='';state.messages=[];state.contextMessages=[];state.showTrash=false;
 if(kind==='peer'){state.section='friends';state.peer=accepted().find(f=>f.id===id);state.chatMembers=[];}
 else{const group=state.groups.find(c=>c.id===id);if(!group)return;state.section='home';state.homeView='chat';state.channel=group;state.workspace=state.workspaces.find(w=>w.id===group.workspace_id)||null;if(state.workspace)await refreshDetails();else{state.files=[];state.members=[];}if(!state.demo){const d=await api(`/api/channels/${id}/members`);state.chatMembers=d.members;}else state.chatMembers=state.members;}
 state.openRead[chatKey()]=preference(kind==='peer'?'dm':'group',id).read_id||0;
 render();document.body.classList.add('show-main');await fetchMessages();paintMessages(true);returnToRead();await markVisibleRead();
}
document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;try{
 if(b.dataset.section){document.body.classList.remove('show-main');await openSection(b.dataset.section);return;}
 if(b.dataset.channel){await selectChat('channel',b.dataset.channel);return;}
 if(b.dataset.workspace){await loadWorkspace(b.dataset.workspace);return;}
 if(b.dataset.peer){await selectChat('peer',b.dataset.peer);return;}
 if(b.dataset.folder){state.showTrash=false;state.fileMode='personal';state.folder=b.dataset.folder;state.search='';await loadFolderFiles();render();document.body.classList.add('show-main');return;}
 if(b.dataset.shared){await openShared(b.dataset.shared);return;}
 if(b.dataset.setting){state.setting=b.dataset.setting;render();document.body.classList.add('show-main');return;}
 if(b.dataset.manage){await loadWorkspace(b.dataset.manage);return;}
 if(b.dataset.accept||b.dataset.decline){await api(`/api/friends/${b.dataset.accept||b.dataset.decline}/${b.dataset.accept?'accept':'decline'}`,{});await refreshPersonal();render();return;}
 if(b.dataset.preview){await previewFile(b.dataset.preview);return;}
 if(b.dataset.download){downloadFile(b.dataset.download);return;}
 switch(b.dataset.action){
 case 'register':authModal('register');break;
 case 'account':if(state.demo)authModal('login');else{await openSection('settings');document.body.classList.add('show-main');}break;
 case 'workspace':if(ensureUser())workspaceModal();break;
 case 'channel':if(ensureUser())channelModal();break;
 case 'invite':if(ensureWorkspace())await inviteModal();break;
 case 'friend':if(ensureUser())friendModal();break;
 case 'folder-root':if(ensureUser())folderModal(null);break;
 case 'folder-child':if(ensureUser())folderModal(state.folder);break;
 case 'upload':if(!ensureUser())break;if(showingFiles()&&state.fileMode==='personal'&&!state.folder){folderModal(null);break;}if(showingFiles()&&state.fileMode==='shared'&&!ensureWorkspace())break;$('#file-input').click();break;
 case 'close':closeModal();break;
 case 'back':document.body.classList.remove('show-main');break;
 case 'code':{const input=$('#message-input');input.value+='\n```\n\n```';input.focus();saveDraft();break;}
 case 'history':historyModal();break;
 case 'group-library':historyModal(true);break;
 case 'group-files':await loadWorkspace(state.channel.workspace_id||state.workspace.id);break;
 case 'all-shared':state.sharedChannel=null;render();break;
 case 'members':await membersModal();break;
 case 'logout':await api('/api/logout',{});state.request++;loadDemo();break;
 }
 }catch(error){toast(error.message);}});
function simpleForm(title,html,onSubmit){modal(`<h2 id="modal-title">${title}</h2><form id="simple-form">${html}<p id="form-error" class="form-error" role="alert"></p><button class="button primary full">确定</button></form>`);$('#simple-form').onsubmit=async e=>{e.preventDefault();const b=$('button',e.target);b.disabled=true;try{await onSubmit(Object.fromEntries(new FormData(e.target)));closeModal();}catch(e){formError(e);}finally{b.disabled=false;}};}
function friendModal(){simpleForm('添加好友','<p class="muted">输入对方注册邮箱，对方接受后即可私聊。</p><label>邮箱<input name="email" type="email" required placeholder="friend@example.com"></label>',async data=>{await api('/api/friends',data);await refreshPersonal();render();toast('好友申请已发送');});}
function folderModal(parent){simpleForm(parent?'新建文件夹':'添加文件工作区','<label>名称<input name="name" required maxlength="100" placeholder="例如：我的项目"></label>',async data=>{const result=await api('/api/folders',{...data,parent_id:parent});await refreshPersonal();state.section='files';state.fileMode='personal';state.folder=result.id;await loadFolderFiles();render();document.body.classList.add('show-main');});}
async function loadAccount(preferred){
 const result=await api('/api/me');Object.assign(state,{demo:false,user:result.user,workspaces:result.workspaces,workspace:null,channels:[],members:[],chatMembers:[],files:[],messages:[],personalFiles:[],peer:null,channel:null,folder:null,fileMode:'personal',sharedChannel:null,sharedFolder:null,sharedFolders:[],trash:[],showTrash:false,drafts:{},replies:{},mentionIds:{},readSent:{},openRead:{},scrollPositions:{},pendingSends:{},failedUpload:null,transfer:'',connected:true});
 await refreshPersonal();await refreshActivity();const w=state.workspaces.find(w=>w.id===preferred)||state.workspaces[0];if(w)await loadWorkspace(w.id);else{state.section='home';state.homeView='chat';render();}
 if(pendingInvite){try{await reviewInvite(pendingInvite);}catch(error){toast(error.message);pendingInvite=null;history.replaceState({},'',location.pathname);}}
}
async function loadWorkspace(id,channel){
 if(channel){await refreshGroups();return selectChat('channel',channel);}
 saveDraft();state.request++;state.workspace=state.workspaces.find(w=>w.id===id);state.section='home';state.homeView='files';state.fileMode='shared';state.sharedChannel=null;state.sharedFolder=null;state.showTrash=false;state.search='';state.messages=[];await refreshDetails();render();document.body.classList.add('show-main');
}
async function refreshGroups(){await refreshActivity();}
async function refreshDetails(){if(state.demo||!state.workspace)return;const id=state.workspace.id;const d=await api(`/api/workspaces/${id}`);if(state.workspace?.id!==id||state.demo)return;Object.assign(state,{channels:d.channels,members:d.members,files:d.files,sharedFolders:d.folders||[]});if(state.fileMode==='shared')state.trash=d.trash||[];}
async function refreshPersonal(){if(state.demo)return;const userId=state.user.id;const [friends,folders,me]=await Promise.all([api('/api/friends'),api('/api/folders'),api('/api/me')]);if(state.demo||state.user.id!==userId)return;state.workspaces=me.workspaces;state.friends=friends.friends;state.folders=folders.folders;if(state.peer&&!accepted().some(f=>f.id===state.peer.id)){const id=state.peer.id;forgetConversation('dm',id);state.peer=null;if(state.section==='friends'){closeModal();render();toast('好友关系已解除');}}if(!state.folder)state.folder=state.folders.find(f=>!f.parent_id)?.id||null;}
async function fetchMessages(){if(showingFiles()||!chatTarget()||!['home','friends'].includes(state.section))return;if(state.demo){demoMessages();return;}const key=chatKey(),version=state.request;const d=await api(chatPath());if(key===chatKey()&&version===state.request&&!state.demo){state.messages=d.messages;const pref=preference(state.section==='friends'?'dm':'group',chatTarget().id);Object.assign(pref,{read_id:d.read_id,unread:d.unread,mentions:d.mentions});}}
async function openShared(id){saveDraft();state.request++;state.workspace=state.workspaces.find(w=>w.id===id);state.section='files';state.fileMode='shared';state.sharedChannel=null;state.sharedFolder=null;state.showTrash=false;state.search='';await refreshDetails();render();document.body.classList.add('show-main');}
async function loadFolderFiles(){if(state.fileMode!=='personal'||!state.folder){state.personalFiles=[];return;}if(state.demo){state.personalFiles=state.folder==='docs'?[demoFiles[0]]:state.folder==='src'?[demoFiles[1]]:state.folder==='design'?[demoFiles[2]]:[];return;}const id=state.folder;const d=await api(`/api/folders/${id}`);if(state.folder===id&&!state.demo){state.personalFiles=d.files;state.trash=d.trash||[];}}
async function sendMessage(e){
 e.preventDefault();if(!ensureUser()||state.busy||!chatTarget())return;const input=$('#message-input'),body=input.value.trim();if(!body)return;
 const key=chatKey(),path=chatPath(),reply=state.replies[key],people=state.section==='friends'?[state.peer]:state.chatMembers,mentions=(state.mentionIds[key]||[]).filter(id=>{const person=people.find(p=>p.id===id);return person&&body.includes('@'+person.name);});const fingerprint=JSON.stringify([body,reply?.id,mentions]);let pending=state.pendingSends[key];if(pending?.fingerprint!==fingerprint)pending=state.pendingSends[key]={fingerprint,nonce:crypto.randomUUID()};
 state.busy=true;$('.send-button').disabled=true;transferStatus('正在发送…');
 try{await api(path,{body,reply_id:reply?.id,mentions,nonce:pending.nonce});state.drafts[key]='';delete state.pendingSends[key];delete state.replies[key];delete state.mentionIds[key];if(chatKey()===key){input.value='';updateReply();await fetchMessages();paintMessages(true);delete state.scrollPositions[key];await markVisibleRead();transferStatus('已发送');}}
 catch(error){if(chatKey()===key)transferStatus('发送失败，内容已保留，点击发送可重试：'+error.message,true);toast(error.message);}
 finally{state.busy=false;const b=$('.send-button');if(b)b.disabled=false;}
}
async function uploadFiles(files,retry=null){
 if(!ensureUser()||!files.length)return;if(state.uploading||state.choosingUpload){toast('正在上传，请稍候');return;}
 const personal=showingFiles()&&state.fileMode==='personal',dm=visibleChat()&&state.section==='friends',group=visibleChat()&&!dm;
 if(personal&&!state.folder){folderModal(null);return;}if(!personal&&!dm&&!group&&!state.workspace){toast('请先选择工作区');return;}
 const context=retry||{files,endpoint:personal?`/api/folders/${state.folder}/files`:dm?`/api/dm/${state.peer.id}/files`:group?`/api/channels/${state.channel.id}/files`:`/api/workspaces/${state.workspace.id}/files`,folder_id:!personal&&!dm&&!group?state.sharedFolder:null,nonces:files.map(()=>crypto.randomUUID()),modes:{}};
 if(!retry&&group){state.choosingUpload=true;try{context.storage=state.channel.workspace_id?await attachmentStorageChoice(state.channel):'group';}finally{state.choosingUpload=false;}if(!context.storage){$('#file-input').value='';return;}}
 state.uploading=true;let count=0;
 try{for(let i=0;i<files.length;i++){
  const file=files[i];if(file.size>10485760){toast(`${file.name} 超过 10 MB`);continue;}
  transferStatus(`正在上传 ${i+1}/${files.length}：${file.name}`);
  const content=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=()=>reject(new Error('读取文件失败'));r.readAsDataURL(file);});
  const data={name:file.name,content,storage:context.storage,folder_id:context.folder_id,nonce:context.nonces[i],mode:context.modes[i]};
  try{await api(context.endpoint,data);}catch(error){if(error.status!==409)throw error;const mode=await collisionChoice(file.name);if(!mode)continue;context.modes[i]=mode;await api(context.endpoint,{...data,mode});}count++;
 }
 state.failedUpload=null;transferStatus(count?`已保存 ${count} 个文件`:'上传已结束');if(visibleChat()){await fetchMessages();paintMessages();}await refreshDetails();await loadFolderFiles();if($('#file-rows'))$('#file-rows').innerHTML=fileRows();const b=$('[data-action="retry-upload"]');if(b)b.hidden=true;
 }catch(error){state.failedUpload=context;transferStatus('上传失败，点击重试可继续：'+error.message,true);const b=$('[data-action="retry-upload"]');if(b)b.hidden=false;toast(error.message);}
 finally{state.uploading=false;$('#file-input').value='';}
}
function fileRecord(id){return [...state.personalFiles,...state.files].find(f=>f.id===id);}
function fileEndpoint(id){const f=fileRecord(id);return fileBase(f?.file_type||(state.fileMode==='personal'?'personal':'shared'))+'/'+id;}
async function previewFile(id){const f=fileRecord(id);if(!f)return;const endpoint=fileEndpoint(id);modal(`<div class="preview-title"><h2 id="modal-title">${esc(f.name)}</h2><button class="button" data-download="${id}">${icon('download')} 下载</button></div><div id="preview-content">正在读取…</div>`,true);try{const d=state.demo?f:await api(endpoint+'/preview');if($('#preview-content'))$('#preview-content').innerHTML=`<pre class="code-preview"><code>${esc(d.content)}</code></pre>`;}catch(e){if($('#preview-content'))$('#preview-content').textContent=e.message;}}
function downloadFile(id){const f=fileRecord(id);if(!f)return;const a=document.createElement('a');a.href=state.demo?URL.createObjectURL(new Blob([f.content],{type:'text/plain;charset=utf-8'})):fileEndpoint(id);a.download=f.name;a.click();if(state.demo)setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
let polling=false;
setInterval(async()=>{if(state.demo||document.hidden||polling)return;polling=true;try{
 await refreshPersonal();await refreshActivity();
 if(visibleChat()){await fetchMessages();paintMessages();await markVisibleRead();}
 await refreshDetails();
 if(showingFiles()){if(state.section==='files')await loadFolderFiles();if($('#file-rows'))$('#file-rows').innerHTML=fileRows();}
 updateConnection(true);
 }catch(error){updateConnection(false);if(error.status===401){state.request++;closeModal();loadDemo();toast('请重新登录');}}finally{polling=false;}},2500);
(async()=>{try{await loadAccount();}catch(e){loadDemo();if(e.status!==401)toast('服务器连接失败，显示演示内容');if(pendingInvite)authModal('register');}})();



