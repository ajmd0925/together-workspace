"""Conversation membership, activity, attachments and recoverable file management."""
import base64
import json
import re
import secrets
import time
from urllib.parse import parse_qs, quote

ApiError = None  # Assigned by server.py, including when launched as __main__.


def uid():
    return secrets.token_hex(12)


def init(con):
    con.executescript('''
    CREATE TABLE IF NOT EXISTS group_settings(channel_id TEXT PRIMARY KEY REFERENCES channels(id),owner TEXT REFERENCES users(id),visibility TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS group_members(channel_id TEXT REFERENCES channels(id),user_id TEXT REFERENCES users(id),PRIMARY KEY(channel_id,user_id));
    CREATE TABLE IF NOT EXISTS group_exclusions(channel_id TEXT REFERENCES channels(id),user_id TEXT REFERENCES users(id),PRIMARY KEY(channel_id,user_id));
    CREATE TABLE IF NOT EXISTS group_invites(token TEXT PRIMARY KEY,channel_id TEXT REFERENCES channels(id),expires REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS conversation_state(user_id TEXT REFERENCES users(id),kind TEXT,target TEXT,read_id INTEGER NOT NULL DEFAULT 0,pinned INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,kind,target));
    CREATE TABLE IF NOT EXISTS message_details(kind TEXT,message_id INTEGER,reply_id INTEGER,file_id TEXT,file_type TEXT,nonce TEXT,user_id TEXT,PRIMARY KEY(kind,message_id),UNIQUE(user_id,nonce));
    CREATE TABLE IF NOT EXISTS mentions(kind TEXT,message_id INTEGER,user_id TEXT REFERENCES users(id),PRIMARY KEY(kind,message_id,user_id));
    CREATE TABLE IF NOT EXISTS saved_messages(user_id TEXT REFERENCES users(id),kind TEXT,target TEXT,message_id INTEGER,pinned INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,kind,target,message_id));
    CREATE TABLE IF NOT EXISTS dm_files(id TEXT PRIMARY KEY,sender TEXT REFERENCES users(id),recipient TEXT REFERENCES users(id),name TEXT NOT NULL,size INTEGER NOT NULL,content BLOB NOT NULL,created REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS file_details(kind TEXT,file_id TEXT,folder_id TEXT,deleted REAL,revision INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(kind,file_id));
    CREATE TABLE IF NOT EXISTS file_versions(id TEXT PRIMARY KEY,kind TEXT,file_id TEXT,revision INTEGER,name TEXT,size INTEGER,content BLOB,created REAL,user_id TEXT);
    CREATE TABLE IF NOT EXISTS shared_folders(id TEXT PRIMARY KEY,workspace_id TEXT REFERENCES workspaces(id),parent_id TEXT REFERENCES shared_folders(id),name TEXT NOT NULL,created REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS upload_requests(user_id TEXT,nonce TEXT,file_id TEXT,PRIMARY KEY(user_id,nonce));
    INSERT OR IGNORE INTO group_settings SELECT c.id,w.owner,'workspace' FROM channels c JOIN workspaces w ON w.id=c.workspace_id;
    ''')


def channel(con, channel_id, user):
    row = con.execute("SELECT c.*,s.owner,coalesce(s.visibility,'workspace') AS visibility FROM channels c LEFT JOIN group_settings s ON s.channel_id=c.id WHERE c.id=?", (channel_id,)).fetchone()
    if not row:
        raise ApiError(404, '群聊不存在')
    if con.execute('SELECT 1 FROM group_exclusions WHERE channel_id=? AND user_id=?', (channel_id, user['id'])).fetchone():
        raise ApiError(403, '你已被移出这个群聊')
    joined = con.execute('SELECT 1 FROM group_members WHERE channel_id=? AND user_id=?', (channel_id, user['id'])).fetchone()
    workspace_member = row['workspace_id'] and con.execute('SELECT 1 FROM members WHERE workspace_id=? AND user_id=?', (row['workspace_id'], user['id'])).fetchone()
    if not joined and not (row['visibility'] == 'workspace' and workspace_member):
        raise ApiError(403, '你还不是这个群聊的成员')
    return row


def peers(con, group):
    sql = 'SELECT u.id,u.name FROM users u JOIN group_members m ON m.user_id=u.id WHERE m.channel_id=?'
    params = [group['id']]
    if group['visibility'] == 'workspace':
        sql += ' UNION SELECT u.id,u.name FROM users u JOIN members m ON m.user_id=u.id WHERE m.workspace_id=?'
        params.append(group['workspace_id'])
    return [dict(r) for r in con.execute('SELECT * FROM (' + sql + ') p WHERE NOT EXISTS(SELECT 1 FROM group_exclusions e WHERE e.channel_id=? AND e.user_id=p.id)', [*params, group['id']])]


def friend(con, user, peer):
    if not con.execute("SELECT 1 FROM friendships WHERE status='accepted' AND ((sender=? AND recipient=?) OR (sender=? AND recipient=?))", (user['id'], peer, peer, user['id'])).fetchone():
        raise ApiError(403, '双方成为好友后才能私聊')


def scope(kind, target, user):
    if kind == 'group':
        return 'messages', 'channel_id=?', [target]
    return 'direct_messages', '((sender=? AND recipient=?) OR (sender=? AND recipient=?))', [user['id'], target, target, user['id']]


def message(con, kind, target, user, message_id):
    table, where, params = scope(kind, target, user)
    row = con.execute(f'SELECT * FROM {table} WHERE {where} AND id=?', [*params, message_id]).fetchone()
    if not row:
        raise ApiError(404, '该消息不在当前会话中')
    return row


def activity(con, user, kind, target):
    pref = con.execute('SELECT * FROM conversation_state WHERE user_id=? AND kind=? AND target=?', (user['id'], kind, target)).fetchone()
    read_id = pref['read_id'] if pref else 0
    table, where, params = scope(kind, target, user)
    sender = 'user_id' if kind == 'group' else 'sender'
    unread = con.execute(f'SELECT count(*) FROM {table} WHERE {where} AND id>? AND {sender}<>?', [*params, read_id, user['id']]).fetchone()[0]
    mentions = con.execute(f'SELECT count(*) FROM mentions n JOIN {table} m ON m.id=n.message_id WHERE n.kind=? AND n.user_id=? AND m.id>? AND {where}', [kind, user['id'], read_id, *params]).fetchone()[0]
    return {'read_id': read_id, 'unread': unread, 'mentions': mentions, 'pinned': bool(pref and pref['pinned'])}


def file_row(con, kind, file_id, user, allow_deleted=False, include_content=True):
    table = {'shared': 'files', 'personal': 'personal_files', 'dm': 'dm_files'}.get(kind)
    if not table:
        raise ApiError(400, '文件类型无效')
    columns = 'f.*' if include_content else {'shared':'f.id,f.name,f.size,f.created,f.workspace_id,f.channel_id,f.user_id', 'personal':'f.id,f.name,f.size,f.created,f.folder_id,f.owner', 'dm':'f.id,f.name,f.size,f.created,f.sender,f.recipient'}[kind]
    row = con.execute(f'SELECT {columns},d.folder_id AS shared_folder,d.deleted,coalesce(d.revision,1) AS revision FROM {table} f LEFT JOIN file_details d ON d.kind=? AND d.file_id=f.id WHERE f.id=?', (kind, file_id)).fetchone()
    if not row:
        raise ApiError(404, '文件不存在')
    if kind == 'personal':
        if row['owner'] != user['id']:
            raise ApiError(403, '无权访问此文件')
    elif kind == 'dm':
        if user['id'] not in (row['sender'], row['recipient']):
            raise ApiError(403, '无权访问此文件')
        friend(con, user, row['recipient'] if row['sender'] == user['id'] else row['sender'])
    elif row['workspace_id']:
        if not con.execute('SELECT 1 FROM members WHERE workspace_id=? AND user_id=?', (row['workspace_id'], user['id'])).fetchone():
            raise ApiError(403, '无权访问工作区文件')
    else:
        channel(con, row['channel_id'], user)
    if row['deleted'] and not allow_deleted:
        raise ApiError(404, '文件已移入回收站')
    return row


def metadata(con, kind, row):
    result = {k: row[k] for k in row.keys() if k != 'content'}
    detail = con.execute('SELECT * FROM file_details WHERE kind=? AND file_id=?', (kind, row['id'])).fetchone()
    result.update(file_type=kind, deleted=detail['deleted'] if detail else None, revision=detail['revision'] if detail else 1)
    if kind == 'shared':
        result['folder_id'] = detail['folder_id'] if detail else None
        workspace = row['workspace_id'] if 'workspace_id' in row.keys() else con.execute('SELECT workspace_id FROM files WHERE id=?', (row['id'],)).fetchone()[0]
        result['storage'] = 'workspace' if workspace else 'group'
    return result


def decorate(con, rows, kind, target, user):
    result = []
    for row in rows:
        m = dict(row)
        m.setdefault('user_id', m.get('sender'))
        detail = con.execute('SELECT * FROM message_details WHERE kind=? AND message_id=?', (kind, m['id'])).fetchone()
        m['attachment'] = None
        m['reply'] = None
        if detail and detail['file_id']:
            try:
                f = file_row(con, detail['file_type'], detail['file_id'], user, include_content=False)
                m['attachment'] = {'id': f['id'], 'name': f['name'], 'size': f['size'], 'file_type': detail['file_type']}
                if detail['file_type'] == 'shared':
                    m['attachment']['storage'] = 'workspace' if f['workspace_id'] else 'group'
            except ApiError:
                m['attachment'] = {'unavailable': True, 'name': '附件已移入回收站或无权访问'}
        if detail and detail['reply_id']:
            reply = message(con, kind, target, user, detail['reply_id'])
            author_id = reply['user_id'] if kind == 'group' else reply['sender']
            author = con.execute('SELECT name FROM users WHERE id=?', (author_id,)).fetchone()
            m['reply'] = {'id': reply['id'], 'body': reply['body'][:240] or '文件附件', 'author': author['name']}
        m['mentioned'] = bool(con.execute('SELECT 1 FROM mentions WHERE kind=? AND message_id=? AND user_id=?', (kind, m['id'], user['id'])).fetchone())
        m['saved'] = bool(con.execute('SELECT 1 FROM saved_messages WHERE user_id=? AND kind=? AND target=? AND message_id=?', (user['id'], kind, target, m['id'])).fetchone())
        m['pinned'] = bool(con.execute('SELECT 1 FROM saved_messages WHERE kind=? AND target=? AND message_id=? AND pinned=1', (kind, target, m['id'])).fetchone())
        result.append(m)
    return result


def post_message(h, con, kind, target, user, data, attachment=None):
    nonce = data.get('nonce')
    if nonce is not None and (not isinstance(nonce, str) or not 1 <= len(nonce) <= 100):
        raise ApiError(400, '消息标识无效')
    if nonce:
        old = con.execute('SELECT * FROM message_details WHERE user_id=? AND nonce=?', (user['id'], nonce)).fetchone()
        if old:
            if old['kind'] != kind:
                raise ApiError(409, '消息标识已使用')
            message(con, kind, target, user, old['message_id'])
            return old['message_id']
    body = h.field(data, 'body', 12000, 0 if attachment else 1)
    reply_id = data.get('reply_id')
    if reply_id is not None:
        if type(reply_id) != int:
            raise ApiError(400, '回复消息无效')
        message(con, kind, target, user, reply_id)
    people = peers(con, channel(con, target, user)) if kind == 'group' else [dict(r) for r in con.execute('SELECT id,name FROM users WHERE id IN (?,?)', (user['id'], target))]
    requested = data.get('mentions', [])
    if not isinstance(requested, list) or any(not isinstance(p, str) or p not in {u['id'] for u in people} for p in requested):
        raise ApiError(400, '只能提醒当前会话成员')
    mentioned = {u['id'] for u in people if u['id'] != user['id'] and (u['id'] in requested or re.search(r'@' + re.escape(u['name']) + r'(?=\s|$|[，。！？、,:;])', body))}
    if kind == 'group':
        cursor = con.execute('INSERT INTO messages(channel_id,user_id,body,created) VALUES(?,?,?,?)', (target, user['id'], body, time.time()))
    else:
        cursor = con.execute('INSERT INTO direct_messages(sender,recipient,body,created) VALUES(?,?,?,?)', (user['id'], target, body, time.time()))
    mid = cursor.lastrowid
    con.execute('INSERT INTO message_details VALUES(?,?,?,?,?,?,?)', (kind, mid, reply_id, attachment['id'] if attachment else None, attachment['kind'] if attachment else None, nonce, user['id']))
    con.executemany('INSERT INTO mentions VALUES(?,?,?)', [(kind, mid, p) for p in mentioned])
    return mid


def upload(h, con, kind, user, data, workspace=None, group=None, folder=None, peer=None):
    con.execute('UPDATE users SET name=name WHERE id=?', (user['id'],))
    nonce = data.get('nonce')
    if nonce is not None and (not isinstance(nonce, str) or not 1 <= len(nonce) <= 100):
        raise ApiError(400, '上传标识无效')
    if nonce:
        old = con.execute('SELECT file_id FROM upload_requests WHERE user_id=? AND nonce=?', (user['id'], nonce)).fetchone()
        if old:
            f = file_row(con, kind, old['file_id'], user)
            if (kind == 'shared' and (f['workspace_id'] != workspace or f['channel_id'] != group)) or (kind == 'personal' and f['folder_id'] != folder) or (kind == 'dm' and f['recipient'] != peer):
                raise ApiError(409, '上传标识已使用')
            return f['id']
    name, content = h.file_data(data)
    table = {'shared': 'files', 'personal': 'personal_files', 'dm': 'dm_files'}[kind]
    # Serialize collision checks and writes, including concurrent uploads.
    if kind == 'shared':
        if folder:
            shared_folder(con, folder, workspace)
        duplicates = con.execute("SELECT f.id FROM files f LEFT JOIN file_details d ON d.kind='shared' AND d.file_id=f.id WHERE f.workspace_id IS ? AND (? IS NOT NULL OR f.channel_id=?) AND d.folder_id IS ? AND d.deleted IS NULL AND f.name=?", (workspace, workspace, group, folder, name)).fetchall()
    elif kind == 'personal':
        duplicates = con.execute("SELECT f.id FROM personal_files f LEFT JOIN file_details d ON d.kind='personal' AND d.file_id=f.id WHERE f.folder_id=? AND f.owner=? AND d.deleted IS NULL AND f.name=?", (folder, user['id'], name)).fetchall()
    else:
        duplicates = []
    mode = data.get('mode')
    if mode not in (None, 'keep', 'replace'):
        raise ApiError(400, '同名文件处理方式无效')
    if duplicates and mode is None:
        raise ApiError(409, '存在同名文件，请选择保留两个版本或更新原文件')
    if duplicates and mode == 'keep':
        if kind == 'shared':
            existing = {r[0] for r in con.execute("SELECT f.name FROM files f LEFT JOIN file_details d ON d.kind='shared' AND d.file_id=f.id WHERE f.workspace_id IS ? AND (? IS NOT NULL OR f.channel_id=?) AND d.folder_id IS ? AND d.deleted IS NULL", (workspace, workspace, group, folder))}
        else:
            existing = {r[0] for r in con.execute("SELECT f.name FROM personal_files f LEFT JOIN file_details d ON d.kind='personal' AND d.file_id=f.id WHERE f.folder_id=? AND f.owner=? AND d.deleted IS NULL", (folder, user['id']))}
        dot = name.rfind('.')
        stem, suffix = (name[:dot], name[dot:]) if dot > 0 else (name, '')
        number = 2
        while name in existing:
            marker = f' ({number})'
            name = stem[:max(1,180-len(suffix)-len(marker))] + marker + suffix
            number += 1
    now, file_id = time.time(), uid()
    if duplicates and mode == 'replace':
        file_id = duplicates[0]['id']
        old = file_row(con, kind, file_id, user)
        con.execute('INSERT INTO file_versions VALUES(?,?,?,?,?,?,?,?,?)', (uid(), kind, file_id, old['revision'], old['name'], old['size'], old['content'], old['created'], user['id']))
        con.execute(f'UPDATE {table} SET content=?,size=?,created=? WHERE id=?', (content, len(content), now, file_id))
        con.execute('INSERT INTO file_details(kind,file_id,folder_id,revision) VALUES(?,?,?,?) ON CONFLICT(kind,file_id) DO UPDATE SET revision=excluded.revision', (kind, file_id, folder, old['revision'] + 1))
    else:
        if kind == 'shared':
            con.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,?)', (file_id, workspace, group, user['id'], name, len(content), content, now))
        elif kind == 'personal':
            con.execute('INSERT INTO personal_files VALUES(?,?,?,?,?,?,?)', (file_id, folder, user['id'], name, len(content), content, now))
        else:
            con.execute('INSERT INTO dm_files VALUES(?,?,?,?,?,?,?)', (file_id, user['id'], peer, name, len(content), content, now))
        con.execute('INSERT INTO file_details(kind,file_id,folder_id) VALUES(?,?,?)', (kind, file_id, folder if kind == 'shared' else None))
    if nonce:
        con.execute('INSERT INTO upload_requests VALUES(?,?,?)', (user['id'], nonce, file_id))
    if group or peer:
        post_message(h, con, 'group' if group else 'dm', group or peer, user, {'body': '', 'nonce': 'attachment:' + nonce if nonce and len(nonce) <= 89 else None}, {'id': file_id, 'kind': kind})
    return file_id


def shared_folder(con, folder_id, workspace):
    row = con.execute('SELECT * FROM shared_folders WHERE id=? AND workspace_id=?', (folder_id, workspace)).fetchone()
    if not row:
        raise ApiError(404, '工作区文件夹不存在')
    return row


def groups(con, user):
    rows = con.execute("SELECT c.*,w.name AS workspace_name,s.owner,coalesce(s.visibility,'workspace') AS visibility FROM channels c LEFT JOIN workspaces w ON w.id=c.workspace_id LEFT JOIN group_settings s ON s.channel_id=c.id WHERE (EXISTS(SELECT 1 FROM group_members g WHERE g.channel_id=c.id AND g.user_id=?) OR (coalesce(s.visibility,'workspace')='workspace' AND EXISTS(SELECT 1 FROM members m WHERE m.workspace_id=c.workspace_id AND m.user_id=?))) AND NOT EXISTS(SELECT 1 FROM group_exclusions e WHERE e.channel_id=c.id AND e.user_id=?) ORDER BY c.rowid", (user['id'], user['id'], user['id']))
    return [{**dict(r), **activity(con, user, 'group', r['id'])} for r in rows]


def handle(h, con, user, path, method, data, query):
    if method == 'POST':
        con.execute('UPDATE users SET name=name WHERE id=?', (user['id'],))
    params = parse_qs(query)
    if path == '/api/groups':
        if method == 'GET':
            h.send(200, {'groups': groups(con, user)})
        else:
            workspace = data.get('workspace_id') or None
            if workspace:
                h.member(con, workspace, user)
            group_id = uid()
            visibility = data.get('visibility', 'private')
            if visibility not in ('private', 'workspace') or (visibility == 'workspace' and not workspace):
                raise ApiError(400, '工作区群聊需要选择工作区')
            name = h.field(data, 'name', 40)
            if workspace and con.execute('SELECT 1 FROM channels WHERE workspace_id=? AND name=?', (workspace, name)).fetchone():
                raise ApiError(409, '该工作区已存在同名群聊')
            con.execute('INSERT INTO channels VALUES(?,?,?,?)', (group_id, workspace, name, h.field(data, 'description', 200, 0)))
            con.execute('INSERT INTO group_settings VALUES(?,?,?)', (group_id, user['id'], visibility))
            con.execute('INSERT INTO group_members VALUES(?,?)', (group_id, user['id']))
            h.send(201, {'id': group_id})
        return True
    if path == '/api/activity' and method == 'GET':
        dm = {}
        for r in con.execute("SELECT CASE WHEN sender=? THEN recipient ELSE sender END AS peer FROM friendships WHERE status='accepted' AND (sender=? OR recipient=?)", (user['id'], user['id'], user['id'])):
            dm[r['peer']] = activity(con, user, 'dm', r['peer'])
        workspace_pins = [r[0] for r in con.execute("SELECT target FROM conversation_state WHERE user_id=? AND kind='workspace' AND pinned=1", (user['id'],))]
        h.send(200, {'groups': groups(con, user), 'dm': dm, 'workspace_pins': workspace_pins})
        return True
    if path == '/api/join/preview' and method == 'GET':
        token = params.get('token', [''])[0]
        invitation = con.execute('SELECT * FROM group_invites WHERE token=? AND expires>?', (token, time.time())).fetchone()
        if invitation:
            row = con.execute('SELECT c.name,c.workspace_id,w.name AS workspace_name FROM channels c LEFT JOIN workspaces w ON w.id=c.workspace_id WHERE c.id=?', (invitation['channel_id'],)).fetchone()
            h.send(200, {'kind': 'group', 'name': row['name'], 'workspace_name': row['workspace_name'], 'scope': '本群全部聊天记录与附件' + ('；关联工作区的全部文件及工作区公开群聊' if row['workspace_id'] else '')})
        else:
            row = con.execute('SELECT w.name FROM invites i JOIN workspaces w ON w.id=i.workspace_id WHERE i.token=? AND i.expires>?', (token, time.time())).fetchone()
            if not row:
                raise ApiError(404, '邀请链接无效或已过期')
            h.send(200, {'kind': 'workspace', 'name': row['name'], 'scope': '工作区全部文件与工作区公开群聊；仅受邀成员群聊需要单独邀请'})
        return True
    if path == '/api/join' and method == 'POST':
        token = h.field(data, 'token', 100)
        invite = con.execute('SELECT * FROM group_invites WHERE token=? AND expires>?', (token, time.time())).fetchone()
        if not invite:
            return False
        group = con.execute('SELECT * FROM channels WHERE id=?', (invite['channel_id'],)).fetchone()
        con.execute('DELETE FROM group_exclusions WHERE channel_id=? AND user_id=?', (group['id'], user['id']))
        con.execute('INSERT OR IGNORE INTO group_members VALUES(?,?)', (group['id'], user['id']))
        if group['workspace_id']:
            con.execute('INSERT OR IGNORE INTO members VALUES(?,?)', (group['workspace_id'], user['id']))
        h.send(200, {'id': group['workspace_id'], 'channel_id': group['id']})
        return True
    match = re.fullmatch(r'/api/channels/([a-f0-9]+)/members/([a-f0-9]+)/remove', path)
    if match and method == 'POST':
        group = channel(con, match[1], user)
        if group['owner'] != user['id']:
            raise ApiError(403, '只有群主可以移除成员')
        target = match[2]
        if target == group['owner']:
            raise ApiError(400, '不能移除群主')
        if target not in {p['id'] for p in peers(con, group)}:
            raise ApiError(404, '该成员不在群聊中')
        con.execute('DELETE FROM group_members WHERE channel_id=? AND user_id=?', (group['id'], target))
        con.execute('INSERT OR IGNORE INTO group_exclusions VALUES(?,?)', (group['id'], target))
        # Old shared links must not undo removal. A newly issued group invite can re-admit them.
        con.execute('DELETE FROM group_invites WHERE channel_id=?', (group['id'],))
        con.execute("UPDATE conversation_state SET pinned=0 WHERE user_id=? AND kind='group' AND target=?", (target, group['id']))
        h.send(200, {'ok': True})
        return True
    match = re.fullmatch(r'/api/friends/([a-f0-9]+)/remove', path)
    if match and method == 'POST':
        peer = match[1]
        friend(con, user, peer)
        con.execute("DELETE FROM friendships WHERE status='accepted' AND ((sender=? AND recipient=?) OR (sender=? AND recipient=?))", (user['id'], peer, peer, user['id']))
        con.execute("UPDATE conversation_state SET pinned=0 WHERE kind='dm' AND ((user_id=? AND target=?) OR (user_id=? AND target=?))", (user['id'], peer, peer, user['id']))
        h.send(200, {'ok': True})
        return True
    match = re.fullmatch(r'/api/channels/([a-f0-9]+)/(members|invite)', path)
    if match:
        group = channel(con, match[1], user)
        if match[2] == 'members' and method == 'GET':
            h.send(200, {'members': peers(con, group), 'owner': group['owner'], 'visibility': group['visibility']})
        elif match[2] == 'invite' and method == 'POST':
            if group['owner'] != user['id']:
                raise ApiError(403, '只有群主可以生成群聊邀请')
            token = secrets.token_urlsafe(24)
            con.execute('INSERT INTO group_invites VALUES(?,?,?)', (token, group['id'], time.time()+7*86400))
            h.send(201, {'token': token})
        else:
            raise ApiError(405, '不支持此操作')
        return True
    match = re.fullmatch(r'/api/conversations/(group|dm|workspace)/([a-f0-9]+)/(state|saved|context)', path)
    if match:
        kind, target, action = match.groups()
        if kind == 'group':
            channel(con, target, user)
        elif kind == 'dm':
            friend(con, user, target)
        else:
            h.member(con, target, user)
        if action == 'state' and method == 'POST':
            old = con.execute('SELECT * FROM conversation_state WHERE user_id=? AND kind=? AND target=?', (user['id'], kind, target)).fetchone()
            read_id = old['read_id'] if old else 0
            if 'read_id' in data and kind != 'workspace':
                value = data['read_id']
                if type(value) != int or value < 0:
                    raise ApiError(400, '已读位置无效')
                if value:
                    message(con, kind, target, user, value)
                read_id = max(read_id, value)
            pinned = bool(data.get('pinned', old['pinned'] if old else False))
            con.execute('INSERT INTO conversation_state VALUES(?,?,?,?,?) ON CONFLICT(user_id,kind,target) DO UPDATE SET read_id=max(read_id,excluded.read_id),pinned=excluded.pinned', (user['id'], kind, target, read_id, int(pinned)))
            h.send(200, {'ok': True, **(activity(con, user, kind, target) if kind != 'workspace' else {})})
        elif action == 'saved' and kind != 'workspace':
            if method == 'POST':
                mid = data.get('message_id')
                if type(mid) != int:
                    raise ApiError(400, '消息无效')
                message(con, kind, target, user, mid)
                if data.get('unpin'):
                    con.execute('UPDATE saved_messages SET pinned=0 WHERE kind=? AND target=? AND message_id=?', (kind, target, mid))
                if data.get('remove'):
                    con.execute('DELETE FROM saved_messages WHERE user_id=? AND kind=? AND target=? AND message_id=?', (user['id'], kind, target, mid))
                else:
                    con.execute('INSERT INTO saved_messages VALUES(?,?,?,?,?) ON CONFLICT(user_id,kind,target,message_id) DO UPDATE SET pinned=excluded.pinned', (user['id'], kind, target, mid, int(bool(data.get('pinned')))))
                h.send(200, {'ok': True})
            else:
                table, where, values = scope(kind, target, user)
                rows = con.execute(f'SELECT m.*,u.name AS author FROM {table} m JOIN users u ON u.id=m.' + ('user_id' if kind == 'group' else 'sender') + f' WHERE {where} AND EXISTS(SELECT 1 FROM saved_messages s WHERE s.kind=? AND s.target=? AND s.message_id=m.id AND (s.user_id=? OR s.pinned=1)) ORDER BY m.id DESC LIMIT 200', [*values, kind, target, user['id']]).fetchall()
                h.send(200, {'messages': decorate(con, rows, kind, target, user)})
        elif action == 'context' and method == 'GET' and kind != 'workspace':
            try:
                mid = int(params.get('id', ['0'])[0])
            except ValueError:
                raise ApiError(400, '消息无效')
            message(con, kind, target, user, mid)
            table, where, values = scope(kind, target, user)
            sender = 'user_id' if kind == 'group' else 'sender'
            columns = f'SELECT m.*,u.name AS author FROM {table} m JOIN users u ON u.id=m.{sender} WHERE {where}'
            before = con.execute(columns+' AND m.id<=? ORDER BY m.id DESC LIMIT 21', [*values, mid]).fetchall()
            after = con.execute(columns+' AND m.id>? ORDER BY m.id LIMIT 20', [*values, mid]).fetchall()
            h.send(200, {'messages': decorate(con, [*reversed(before), *after], kind, target, user)})
        else:
            raise ApiError(405, '不支持此操作')
        return True
    match = re.fullmatch(r'/api/(?:channels/([a-f0-9]+)/messages|dm/([a-f0-9]+))', path)
    if match:
        kind, target = ('group', match[1]) if match[1] else ('dm', match[2])
        channel(con, target, user) if kind == 'group' else friend(con, user, target)
        if method == 'POST':
            # Write lock before idempotency check prevents concurrent retry duplicates.
            con.execute('UPDATE users SET name=name WHERE id=?', (user['id'],))
            mid = post_message(h, con, kind, target, user, data)
            h.send(201, {'id': mid})
        else:
            table, where, values = scope(kind, target, user)
            sender = 'user_id' if kind == 'group' else 'sender'
            rows = con.execute(f'SELECT m.*,u.name AS author FROM {table} m JOIN users u ON u.id=m.{sender} WHERE {where} ORDER BY m.id DESC LIMIT 500', values).fetchall()
            h.send(200, {'messages': decorate(con, reversed(rows), kind, target, user), **activity(con, user, kind, target)})
        return True
    match = re.fullmatch(r'/api/dm/([a-f0-9]+)/history', path)
    if match and method == 'GET':
        friend(con, user, match[1])
        h.history(con, query, "SELECT CAST(d.id AS TEXT) AS id,'message' AS kind,d.body,d.created,u.name AS author,NULL AS size FROM direct_messages d JOIN users u ON u.id=d.sender LEFT JOIN message_details x ON x.kind='dm' AND x.message_id=d.id WHERE ((d.sender=? AND d.recipient=?) OR (d.sender=? AND d.recipient=?)) AND (x.file_id IS NULL OR d.body<>'') UNION ALL SELECT f.id,'file',f.name,f.created,u.name,f.size FROM dm_files f JOIN users u ON u.id=f.sender LEFT JOIN file_details x ON x.kind='dm' AND x.file_id=f.id WHERE ((f.sender=? AND f.recipient=?) OR (f.sender=? AND f.recipient=?)) AND x.deleted IS NULL", (user['id'], match[1], match[1], user['id'], user['id'], match[1], match[1], user['id']))
        return True
    match = re.fullmatch(r'/api/channels/([a-f0-9]+)/history', path)
    if match and method == 'GET':
        group = channel(con, match[1], user)
        file_scope = params.get('file_scope', ['conversation'])[0]
        if file_scope not in ('conversation', 'group', 'workspace'):
            raise ApiError(400, '文件查找范围无效')
        if file_scope == 'workspace':
            if not group['workspace_id']:
                raise ApiError(400, '此群未关联工作区')
            h.member(con, group['workspace_id'], user)
            files_where, values = 'f.workspace_id=?', [group['workspace_id']]
        elif file_scope == 'group':
            files_where, values = 'f.channel_id=? AND f.workspace_id IS NULL', [group['id']]
        else:
            files_where = "(f.channel_id=? OR EXISTS(SELECT 1 FROM message_details a JOIN messages b ON b.id=a.message_id WHERE a.kind='group' AND a.file_id=f.id AND a.file_type='shared' AND b.channel_id=?))"
            values = [group['id'], group['id']]
        h.history(con, query, "SELECT CAST(m.id AS TEXT) AS id,'message' AS kind,m.body,m.created,u.name AS author,NULL AS size,NULL AS storage FROM messages m JOIN users u ON u.id=m.user_id LEFT JOIN message_details x ON x.kind='group' AND x.message_id=m.id WHERE m.channel_id=? AND (x.file_id IS NULL OR m.body<>'') UNION ALL SELECT f.id,'file',f.name,f.created,u.name,f.size,CASE WHEN f.workspace_id IS NULL THEN 'group' ELSE 'workspace' END FROM files f JOIN users u ON u.id=f.user_id LEFT JOIN file_details x ON x.kind='shared' AND x.file_id=f.id WHERE (" + files_where + ") AND x.deleted IS NULL", [group['id'], *values])
        return True
    match = re.fullmatch(r'/api/(?:channels/([a-f0-9]+)|workspaces/([a-f0-9]+)|folders/([a-f0-9]+)|dm/([a-f0-9]+))/files', path)
    if match and method == 'POST':
        group, workspace, folder, peer = match.groups()
        if group:
            workspace = channel(con, group, user)['workspace_id']
            storage = data.get('storage', 'workspace' if workspace else 'group')
            if storage not in ('group', 'workspace'):
                raise ApiError(400, '附件保存位置无效')
            if storage == 'workspace':
                if not workspace:
                    raise ApiError(400, '此群未关联工作区')
                h.member(con, workspace, user)
            else:
                workspace = None
                if data.get('folder_id'):
                    raise ApiError(400, '本群附件不能放入工作区文件夹')
        elif workspace:
            h.member(con, workspace, user)
        elif folder:
            h.folder(con, folder, user)
        else:
            friend(con, user, peer)
        file_id = upload(h, con, 'dm' if peer else 'personal' if folder else 'shared', user, data, workspace=workspace, group=group, folder=folder or data.get('folder_id') or None, peer=peer)
        h.send(201, {'id': file_id})
        return True
    match = re.fullmatch(r'/api/workspaces/([a-f0-9]+)/folders', path)
    if match:
        h.member(con, match[1], user)
        if method == 'GET':
            h.send(200, {'folders': [dict(r) for r in con.execute('SELECT * FROM shared_folders WHERE workspace_id=? ORDER BY created', (match[1],))]})
        else:
            parent = data.get('parent_id') or None
            if parent:
                shared_folder(con, parent, match[1])
            folder_id = uid()
            con.execute('INSERT INTO shared_folders VALUES(?,?,?,?,?)', (folder_id, match[1], parent, h.field(data, 'name', 100), time.time()))
            h.send(201, {'id': folder_id})
        return True
    match = re.fullmatch(r'/api/(shared-folders|folders)/([a-f0-9]+)/manage', path)
    if match and method == 'POST':
        shared = match[1] == 'shared-folders'
        table = 'shared_folders' if shared else 'folders'
        row = con.execute(f'SELECT * FROM {table} WHERE id=?', (match[2],)).fetchone()
        if not row:
            raise ApiError(404, '文件夹不存在')
        if shared:
            h.member(con, row['workspace_id'], user)
        else:
            h.folder(con, row['id'], user)
        parent = data.get('parent_id', row['parent_id']) or None
        if parent:
            target = shared_folder(con, parent, row['workspace_id']) if shared else h.folder(con, parent, user)
            seen = {row['id']}
            while target:
                if target['id'] in seen:
                    raise ApiError(400, '不能把文件夹移入自身或子文件夹')
                seen.add(target['id'])
                target = con.execute(f'SELECT * FROM {table} WHERE id=?', (target['parent_id'],)).fetchone() if target['parent_id'] else None
        name = h.field(data, 'name', 100) if 'name' in data else row['name']
        con.execute(f'UPDATE {table} SET name=?,parent_id=? WHERE id=?', (name, parent, row['id']))
        h.send(200, {'ok': True})
        return True
    match = re.fullmatch(r'/api/(files|personal-files|dm-files)/([a-f0-9]+)(?:/(preview|manage|versions))?', path)
    if match:
        kind = {'files': 'shared', 'personal-files': 'personal', 'dm-files': 'dm'}[match[1]]
        action = match[3]
        row = file_row(con, kind, match[2], user, action == 'manage')
        if action == 'manage' and method == 'POST':
            table = {'shared': 'files', 'personal': 'personal_files', 'dm': 'dm_files'}[kind]
            if data.get('action') == 'trash':
                con.execute('INSERT INTO file_details(kind,file_id,deleted) VALUES(?,?,?) ON CONFLICT(kind,file_id) DO UPDATE SET deleted=excluded.deleted', (kind, row['id'], time.time()))
            elif data.get('action') == 'restore':
                con.execute('UPDATE file_details SET deleted=NULL WHERE kind=? AND file_id=?', (kind, row['id']))
            elif data.get('action') == 'restore-version':
                version = con.execute('SELECT * FROM file_versions WHERE id=? AND kind=? AND file_id=?', (data.get('version_id'), kind, row['id'])).fetchone()
                if not version:
                    raise ApiError(404, '历史版本不存在')
                con.execute('INSERT INTO file_versions VALUES(?,?,?,?,?,?,?,?,?)', (uid(), kind, row['id'], row['revision'], row['name'], row['size'], row['content'], row['created'], user['id']))
                con.execute(f'UPDATE {table} SET name=?,size=?,content=?,created=? WHERE id=?', (version['name'], version['size'], version['content'], time.time(), row['id']))
                con.execute('INSERT INTO file_details(kind,file_id,revision) VALUES(?,?,?) ON CONFLICT(kind,file_id) DO UPDATE SET revision=excluded.revision', (kind, row['id'], row['revision']+1))
            elif data.get('action') in ('rename', 'move') and kind != 'dm':
                if data['action'] == 'rename':
                    name = h.field(data, 'name', 180)
                    if '/' in name or '\\' in name or any(ord(c)<32 for c in name):
                        raise ApiError(400, '文件名无效')
                    con.execute(f'UPDATE {table} SET name=? WHERE id=?', (name, row['id']))
                else:
                    folder = data.get('folder_id') or None
                    if kind == 'personal':
                        h.folder(con, folder, user)
                        con.execute('UPDATE personal_files SET folder_id=? WHERE id=?', (folder, row['id']))
                    else:
                        if not row['workspace_id']:
                            raise ApiError(400, '未关联工作区的附件不能移动')
                        if folder:
                            shared_folder(con, folder, row['workspace_id'])
                        con.execute('INSERT INTO file_details(kind,file_id,folder_id) VALUES(?,?,?) ON CONFLICT(kind,file_id) DO UPDATE SET folder_id=excluded.folder_id', (kind, row['id'], folder))
            else:
                raise ApiError(400, '文件操作无效')
            h.send(200, {'ok': True})
        elif action == 'versions' and method == 'GET':
            h.send(200, {'revision': row['revision'], 'versions': [dict(r) for r in con.execute('SELECT id,revision,name,size,created FROM file_versions WHERE kind=? AND file_id=? ORDER BY revision DESC', (kind, row['id']))]})
        elif method == 'GET' and action in (None, 'preview'):
            if action == 'preview':
                try:
                    if row['size']>1024*1024 or b'\0' in row['content']:
                        raise UnicodeError()
                    text = row['content'].decode('utf-8')
                except UnicodeError:
                    raise ApiError(415, '该文件暂不支持文本预览，请下载查看')
                h.send(200, {'name': row['name'], 'content': text})
            else:
                h.send_response(200)
                for key, value in {'Content-Type':'application/octet-stream', 'Content-Disposition':"attachment; filename*=UTF-8''"+quote(row['name']), 'Content-Length':str(row['size']), 'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff'}.items():
                    h.send_header(key, value)
                h.end_headers()
                h.wfile.write(row['content'])
        else:
            raise ApiError(405, '不支持此文件操作')
        return True
    return False
