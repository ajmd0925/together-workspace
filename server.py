import argparse
import base64
import hashlib
import hmac
import json
import mimetypes
import math
import os
import re
import secrets
import sqlite3
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from contextlib import contextmanager
from urllib.parse import urlparse, parse_qs, quote
import collaboration
import maintenance

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('WORKSPACE_DATA', str(ROOT / 'data')))
MAX_FILE = 10 * 1024 * 1024


@contextmanager
def db():
    con = sqlite3.connect(DATA / 'workspace.db', timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with con:
            yield con
    finally:
        con.close()


def init_db():
    DATA.mkdir(parents=True, exist_ok=True)
    with db() as con:
        con.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL, owner TEXT REFERENCES users(id), created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS members(workspace_id TEXT REFERENCES workspaces(id), user_id TEXT REFERENCES users(id), PRIMARY KEY(workspace_id,user_id));
        CREATE TABLE IF NOT EXISTS channels(id TEXT PRIMARY KEY, workspace_id TEXT REFERENCES workspaces(id), name TEXT NOT NULL, description TEXT NOT NULL, UNIQUE(workspace_id,name));
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, channel_id TEXT REFERENCES channels(id), user_id TEXT REFERENCES users(id), body TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY, workspace_id TEXT REFERENCES workspaces(id), channel_id TEXT REFERENCES channels(id), user_id TEXT REFERENCES users(id), name TEXT NOT NULL, size INTEGER NOT NULL, content BLOB NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS invites(token TEXT PRIMARY KEY, workspace_id TEXT REFERENCES workspaces(id), expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS friendships(id TEXT PRIMARY KEY, sender TEXT REFERENCES users(id), recipient TEXT REFERENCES users(id), status TEXT NOT NULL DEFAULT 'pending', created REAL NOT NULL);
        CREATE UNIQUE INDEX IF NOT EXISTS friendship_pair ON friendships(min(sender,recipient),max(sender,recipient));
        CREATE TABLE IF NOT EXISTS direct_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT REFERENCES users(id), recipient TEXT REFERENCES users(id), body TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS folders(id TEXT PRIMARY KEY, owner TEXT REFERENCES users(id), parent_id TEXT REFERENCES folders(id), name TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS personal_files(id TEXT PRIMARY KEY, folder_id TEXT REFERENCES folders(id), owner TEXT REFERENCES users(id), name TEXT NOT NULL, size INTEGER NOT NULL, content BLOB NOT NULL, created REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS message_history ON messages(channel_id,created);
        CREATE INDEX IF NOT EXISTS file_history ON files(channel_id,created);
        CREATE INDEX IF NOT EXISTS dm_history ON direct_messages(sender,recipient,created);
        ''')
        collaboration.init(con)
        con.execute('PRAGMA user_version=3')


def uid():
    return secrets.token_hex(12)


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000).hex()
    return salt + ':' + digest


class ApiError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


collaboration.ApiError = ApiError


class Handler(BaseHTTPRequestHandler):
    server_version = 'Together/0.1'

    def log_message(self, fmt, *args):
        # Avoid writing invite/session values to logs.
        pass

    def send(self, status, value, headers=None):
        # Persist writes before a successful response lets the client read them.
        if status < 400 and getattr(self, '_con', None) is not None:
            self._con.commit()
        payload = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        for key, val in (headers or {}).items():
            self.send_header(key, val)
        self.end_headers()
        self.wfile.write(payload)

    def body(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size < 0 or size > 15 * 1024 * 1024:
                raise ApiError(413, '文件不能超过 10 MB')
            result = json.loads(self.rfile.read(size))
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except (ValueError, UnicodeError):
            raise ApiError(400, '请求格式不正确')

    def user(self, con):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            token = cookie['together_session'].value if 'together_session' in cookie else ''
        except Exception:
            token = ''
        row = con.execute('SELECT u.id,u.name,u.email FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=? AND s.expires>?', (token, time.time())).fetchone()
        if not row:
            raise ApiError(401, '请先登录')
        return dict(row)

    def member(self, con, workspace, user):
        if not con.execute('SELECT 1 FROM members WHERE workspace_id=? AND user_id=?', (workspace, user['id'])).fetchone():
            raise ApiError(403, '你还不是这个工作区的成员')

    def channel(self, con, channel, user):
        return collaboration.channel(con, channel, user)

    def folder(self, con, folder_id, user):
        row = con.execute('SELECT * FROM folders WHERE id=? AND owner=?', (folder_id, user['id'])).fetchone()
        if not row:
            raise ApiError(404, '文件夹不存在或无权访问')
        return row

    def file_data(self, data):
        name = self.field(data, 'name', 180)
        if '/' in name or '\\' in name or any(ord(c) < 32 for c in name):
            raise ApiError(400, '文件名无效')
        try:
            content = base64.b64decode(data.get('content', ''), validate=True)
        except (ValueError, TypeError):
            raise ApiError(400, '文件内容无效')
        if len(content) > MAX_FILE:
            raise ApiError(413, '文件不能超过 10 MB')
        return name, content

    def field(self, data, name, maximum=100, minimum=1):
        value = data.get(name, '')
        if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
            raise ApiError(400, f'{name} 长度需要在 {minimum}–{maximum} 个字符之间')
        return value.strip()

    def do_GET(self):
        self.dispatch('GET')

    def history(self, con, query, scope, params):
        """Search the authorized conversation, with an exclusive pagination cursor."""
        values = parse_qs(query)
        keyword = values.get('q', [''])[0].strip()
        kind = values.get('type', ['all'])[0]
        if len(keyword) > 200 or kind not in ('all', 'messages', 'files'):
            raise ApiError(400, '搜索关键词过长或筛选类型无效')
        where, filters = [], []
        bounds = {}
        for name, operator in [('since', '>='), ('until', '<')]:
            if name in values:
                try:
                    value = float(values[name][0])
                    if not math.isfinite(value) or not 0 <= value <= 253402300800:
                        raise ValueError()
                except ValueError:
                    raise ApiError(400, '日期格式无效')
                bounds[name] = value
                where.append(f'created {operator} ?')
                filters.append(value)
        if 'since' in bounds and 'until' in bounds and bounds['since'] >= bounds['until']:
            raise ApiError(400, '开始日期不能晚于结束日期')
        if keyword:
            where.append('instr(lower(body),lower(?)) > 0')
            filters.append(keyword)
        if kind != 'all':
            where.append('kind=?')
            filters.append('message' if kind == 'messages' else 'file')
        if 'cursor' in values:
            try:
                cursor = json.loads(values['cursor'][0])
                if (not isinstance(cursor, list) or len(cursor) != 3
                        or type(cursor[0]) not in (int, float) or not math.isfinite(cursor[0])
                        or cursor[1] not in ('message', 'file')
                        or not isinstance(cursor[2], str) or len(cursor[2]) > 100):
                    raise ValueError()
            except (ValueError, TypeError):
                raise ApiError(400, '分页参数无效，请重新查找')
            where.append('(created,kind,id) < (?,?,?)')
            filters.extend(cursor)
        sql = 'SELECT * FROM (' + scope + ')'
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        rows = [dict(row) for row in con.execute(sql + ' ORDER BY created DESC,kind DESC,id DESC LIMIT 31', [*params, *filters])]
        items = rows[:30]
        last = items[-1] if items else None
        self.send(200, {'items': items, 'next_cursor': [last['created'], last['kind'], last['id']] if len(rows) > 30 else None})

    def do_POST(self):
        self.dispatch('POST')

    def dispatch(self, method):
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            if method == 'POST':
                origin = self.headers.get('Origin')
                if origin and urlparse(origin).netloc != self.headers.get('Host'):
                    raise ApiError(403, '不允许跨站请求')
                if not self.headers.get('Content-Type', '').startswith('application/json'):
                    raise ApiError(415, '需要 JSON 请求')
            if not path.startswith('/api/'):
                if method != 'GET':
                    raise ApiError(404, '页面不存在')
                names = {'/': 'index.html', '/app.js': 'app.js', '/client.js': 'client.js', '/shared.js': 'shared.js', '/features.js': 'features.js', '/features.css': 'features.css', '/layout.css': 'layout.css', '/style.css': 'style.css', '/theme.css': 'theme.css'}
                if path not in names:
                    raise ApiError(404, '页面不存在')
                file = ROOT / 'public' / names[path]
                content = file.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', mimetypes.guess_type(str(file))[0] + '; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Referrer-Policy', 'same-origin')
                self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(content)
                return
            with db() as con:
                self._con = con
                data = self.body() if method == 'POST' else {}
                if method == 'POST' and path in ('/api/register', '/api/login'):
                    email = self.field(data, 'email', 200).lower()
                    password = self.field(data, 'password', 128, 8)
                    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
                        raise ApiError(400, '请输入有效的邮箱地址')
                    if path.endswith('register'):
                        user_id = uid()
                        try:
                            con.execute('INSERT INTO users VALUES(?,?,?,?)', (user_id, self.field(data, 'name', 40), email, password_hash(password)))
                        except sqlite3.IntegrityError:
                            raise ApiError(409, '这个邮箱已注册，请登录')
                    else:
                        row = con.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
                        check = password_hash(password, row['password'].split(':')[0] if row else 'invalid')
                        if not row or not hmac.compare_digest(check, row['password']):
                            raise ApiError(401, '邮箱或密码不正确')
                        user_id = row['id']
                    token = secrets.token_urlsafe(32)
                    con.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
                    con.execute('INSERT INTO sessions VALUES(?,?,?)', (token, user_id, time.time() + 7 * 86400))
                    secure = '; Secure' if os.environ.get('COOKIE_SECURE') == '1' else ''
                    self.send(200, {'ok': True}, {'Set-Cookie': f'together_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800{secure}'})
                    return
                user = self.user(con)
                if collaboration.handle(self, con, user, path, method, data, parsed.query):
                    return
                if path == '/api/profile' and method == 'POST':
                    con.execute('UPDATE users SET name=? WHERE id=?', (self.field(data, 'name', 40), user['id']))
                    self.send(200, {'ok': True})
                    return
                if path == '/api/friends' and method == 'GET':
                    rows = con.execute('SELECT f.id AS request_id, f.sender, f.recipient, f.status, u.id, u.name FROM friendships f JOIN users u ON u.id=CASE WHEN f.sender=? THEN f.recipient ELSE f.sender END WHERE f.sender=? OR f.recipient=? ORDER BY f.created', (user['id'], user['id'], user['id']))
                    self.send(200, {'friends': [dict(row) for row in rows]})
                    return
                if path == '/api/friends' and method == 'POST':
                    target = con.execute('SELECT id FROM users WHERE email=?', (self.field(data, 'email', 200).lower(),)).fetchone()
                    if not target:
                        raise ApiError(404, '该邮箱尚未注册')
                    if target['id'] == user['id']:
                        raise ApiError(400, '不能添加自己为好友')
                    try:
                        con.execute('INSERT INTO friendships VALUES(?,?,?,?,?)', (uid(), user['id'], target['id'], 'pending', time.time()))
                    except sqlite3.IntegrityError:
                        raise ApiError(409, '已经是好友，或存在待处理的好友申请')
                    self.send(201, {'ok': True})
                    return
                match = re.fullmatch(r'/api/friends/([a-f0-9]+)/(accept|decline)', path)
                if match and method == 'POST':
                    row = con.execute('SELECT * FROM friendships WHERE id=? AND recipient=? AND status=?', (match[1], user['id'], 'pending')).fetchone()
                    if not row:
                        raise ApiError(404, '好友申请不存在')
                    if match[2] == 'accept':
                        con.execute('UPDATE friendships SET status=? WHERE id=?', ('accepted', match[1]))
                    else:
                        con.execute('DELETE FROM friendships WHERE id=?', (match[1],))
                    self.send(200, {'ok': True})
                    return
                match = re.fullmatch(r'/api/dm/([a-f0-9]+)(/history)?', path)
                if match:
                    peer = match[1]
                    friendship = con.execute("SELECT 1 FROM friendships WHERE status='accepted' AND ((sender=? AND recipient=?) OR (sender=? AND recipient=?))", (user['id'], peer, peer, user['id'])).fetchone()
                    if not friendship:
                        raise ApiError(403, '双方成为好友后才能私聊')
                    if match[2]:
                        if method != 'GET':
                            raise ApiError(405, '请使用 GET 查找聊天记录')
                        self.history(con, parsed.query, "SELECT CAST(d.id AS TEXT) AS id,'message' AS kind,d.body,d.created,u.name AS author,NULL AS size FROM direct_messages d JOIN users u ON u.id=d.sender WHERE (d.sender=? AND d.recipient=?) OR (d.sender=? AND d.recipient=?)", (user['id'], peer, peer, user['id']))
                        return
                    if method == 'GET':
                        rows = con.execute('SELECT d.id,d.sender AS user_id,d.body,d.created,u.name AS author FROM direct_messages d JOIN users u ON u.id=d.sender WHERE (d.sender=? AND d.recipient=?) OR (d.sender=? AND d.recipient=?) ORDER BY d.id DESC LIMIT 500', (user['id'], peer, peer, user['id'])).fetchall()
                        self.send(200, {'messages': [dict(row) for row in reversed(rows)]})
                    else:
                        con.execute('INSERT INTO direct_messages(sender,recipient,body,created) VALUES(?,?,?,?)', (user['id'], peer, self.field(data, 'body', 12000), time.time()))
                        self.send(201, {'ok': True})
                    return
                if path == '/api/folders':
                    if method == 'GET':
                        self.send(200, {'folders': [dict(row) for row in con.execute('SELECT id,parent_id,name,created FROM folders WHERE owner=? ORDER BY created', (user['id'],))]})
                    else:
                        parent = data.get('parent_id') or None
                        if parent:
                            self.folder(con, parent, user)
                        folder_id = uid()
                        con.execute('INSERT INTO folders VALUES(?,?,?,?,?)', (folder_id, user['id'], parent, self.field(data, 'name', 100), time.time()))
                        self.send(201, {'id': folder_id})
                    return
                match = re.fullmatch(r'/api/folders/([a-f0-9]+)(/files)?', path)
                if match:
                    folder = self.folder(con, match[1], user)
                    if method == 'GET' and not match[2]:
                        rows = con.execute('SELECT id,name,size,created,folder_id FROM personal_files WHERE folder_id=? AND owner=? ORDER BY created DESC', (folder['id'], user['id']))
                        files = [collaboration.metadata(con, 'personal', row) for row in rows]
                        self.send(200, {'files': [f for f in files if not f['deleted']], 'trash': [collaboration.metadata(con, 'personal', row) for row in con.execute("SELECT f.id,f.name,f.size,f.created,f.folder_id FROM personal_files f JOIN file_details d ON d.file_id=f.id AND d.kind='personal' WHERE f.owner=? AND d.deleted IS NOT NULL", (user['id'],))]})
                        return
                    if method == 'POST' and match[2]:
                        name, content = self.file_data(data)
                        file_id = uid()
                        con.execute('INSERT INTO personal_files VALUES(?,?,?,?,?,?,?)', (file_id, folder['id'], user['id'], name, len(content), content, time.time()))
                        self.send(201, {'id': file_id})
                        return
                if path == '/api/logout' and method == 'POST':
                    cookie = SimpleCookie(self.headers.get('Cookie', ''))
                    con.execute('DELETE FROM sessions WHERE token=?', (cookie['together_session'].value,))
                    self.send(200, {'ok': True}, {'Set-Cookie': 'together_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0'})
                    return
                if path == '/api/me' and method == 'GET':
                    workspaces = [dict(r) for r in con.execute('SELECT w.* FROM workspaces w JOIN members m ON m.workspace_id=w.id WHERE m.user_id=? ORDER BY w.created', (user['id'],))]
                    self.send(200, {'user': user, 'workspaces': workspaces})
                    return
                if path == '/api/groups' and method == 'GET':
                    groups = con.execute('SELECT c.*,w.name AS workspace_name FROM channels c JOIN workspaces w ON w.id=c.workspace_id JOIN members m ON m.workspace_id=w.id WHERE m.user_id=? ORDER BY w.created,c.rowid', (user['id'],))
                    self.send(200, {'groups': [dict(row) for row in groups]})
                    return
                if path == '/api/workspaces' and method == 'POST':
                    workspace = uid()
                    con.execute('INSERT INTO workspaces VALUES(?,?,?,?,?)', (workspace, self.field(data, 'name', 50), self.field(data, 'description', 300, 0), user['id'], time.time()))
                    con.execute('INSERT INTO members VALUES(?,?)', (workspace, user['id']))
                    self.send(201, {'id': workspace})
                    return
                if path == '/api/join' and method == 'POST':
                    invite = con.execute('SELECT * FROM invites WHERE token=? AND expires>?', (self.field(data, 'token', 100), time.time())).fetchone()
                    if not invite:
                        raise ApiError(404, '邀请链接无效或已过期，请联系工作区创建者')
                    con.execute('INSERT OR IGNORE INTO members VALUES(?,?)', (invite['workspace_id'], user['id']))
                    self.send(200, {'id': invite['workspace_id']})
                    return
                match = re.fullmatch(r'/api/workspaces/([a-f0-9]+)(?:/(channels|invite|files))?', path)
                if match:
                    workspace, action = match.groups()
                    self.member(con, workspace, user)
                    if method == 'POST' and action == 'files':
                        name, content = self.file_data(data)
                        file_id = uid()
                        con.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,?)', (file_id, workspace, None, user['id'], name, len(content), content, time.time()))
                        self.send(201, {'id': file_id})
                        return
                    if method == 'GET' and action is None:
                        channels = [r for r in collaboration.groups(con, user) if r['workspace_id'] == workspace]
                        members = [dict(r) for r in con.execute('SELECT u.id,u.name FROM users u JOIN members m ON m.user_id=u.id WHERE m.workspace_id=?', (workspace,))]
                        files = [collaboration.metadata(con, 'shared', r) for r in con.execute('SELECT f.id,f.name,f.size,f.created,f.channel_id,u.name AS author FROM files f JOIN users u ON u.id=f.user_id WHERE f.workspace_id=? ORDER BY f.created DESC', (workspace,))]
                        folders = [dict(r) for r in con.execute('SELECT * FROM shared_folders WHERE workspace_id=? ORDER BY created', (workspace,))]
                        self.send(200, {'channels': channels, 'members': members, 'files': [f for f in files if not f['deleted']], 'trash': [f for f in files if f['deleted']], 'folders': folders})
                        return
                    if method == 'POST' and action == 'channels':
                        channel = uid()
                        try:
                            con.execute('INSERT INTO channels VALUES(?,?,?,?)', (channel, workspace, self.field(data, 'name', 40), self.field(data, 'description', 200, 0)))
                        except sqlite3.IntegrityError:
                            raise ApiError(409, '频道名称已存在')
                        con.execute('INSERT INTO group_settings VALUES(?,?,?)', (channel, user['id'], 'workspace'))
                        self.send(201, {'id': channel})
                        return
                    if method == 'POST' and action == 'invite':
                        owner = con.execute('SELECT owner FROM workspaces WHERE id=?', (workspace,)).fetchone()['owner']
                        if owner != user['id']:
                            raise ApiError(403, '只有工作区创建者可以生成邀请')
                        token = secrets.token_urlsafe(24)
                        con.execute('INSERT INTO invites VALUES(?,?,?)', (token, workspace, time.time() + 7 * 86400))
                        self.send(201, {'token': token})
                        return
                match = re.fullmatch(r'/api/channels/([a-f0-9]+)/(messages|files|history)', path)
                if match:
                    channel, action = match.groups()
                    channel_row = self.channel(con, channel, user)
                    if action == 'history':
                        if method != 'GET':
                            raise ApiError(405, '请使用 GET 查找聊天记录')
                        self.history(con, parsed.query, "SELECT CAST(m.id AS TEXT) AS id,'message' AS kind,m.body,m.created,u.name AS author,NULL AS size FROM messages m JOIN users u ON u.id=m.user_id LEFT JOIN message_details x ON x.kind='group' AND x.message_id=m.id WHERE m.channel_id=? AND (x.file_id IS NULL OR m.body<>'') UNION ALL SELECT f.id,'file',f.name,f.created,u.name,f.size FROM files f JOIN users u ON u.id=f.user_id LEFT JOIN file_details x ON x.kind='shared' AND x.file_id=f.id WHERE (f.channel_id=? OR EXISTS(SELECT 1 FROM message_details a JOIN messages b ON b.id=a.message_id WHERE a.kind='group' AND a.file_id=f.id AND a.file_type='shared' AND b.channel_id=?)) AND x.deleted IS NULL", (channel, channel, channel))
                        return
                    if action == 'messages' and method == 'GET':
                        rows = con.execute('SELECT m.*,u.name AS author FROM messages m JOIN users u ON u.id=m.user_id WHERE channel_id=? ORDER BY m.id DESC LIMIT 500', (channel,)).fetchall()
                        self.send(200, {'messages': [dict(r) for r in reversed(rows)]})
                        return
                    if action == 'messages' and method == 'POST':
                        cursor = con.execute('INSERT INTO messages(channel_id,user_id,body,created) VALUES(?,?,?,?)', (channel, user['id'], self.field(data, 'body', 12000), time.time()))
                        self.send(201, {'id': cursor.lastrowid})
                        return
                    if action == 'files' and method == 'POST':
                        name = self.field(data, 'name', 180)
                        if '/' in name or '\\' in name or any(ord(c) < 32 for c in name):
                            raise ApiError(400, '文件名无效')
                        try:
                            content = base64.b64decode(data.get('content', ''), validate=True)
                        except (ValueError, TypeError):
                            raise ApiError(400, '文件内容无效')
                        if len(content) > MAX_FILE:
                            raise ApiError(413, '文件不能超过 10 MB')
                        file_id = uid()
                        con.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,?)', (file_id, channel_row['workspace_id'], channel, user['id'], name, len(content), content, time.time()))
                        self.send(201, {'id': file_id})
                        return
                match = re.fullmatch(r'/api/(files|personal-files)/([a-f0-9]+)(/preview)?', path)
                if match and method == 'GET':
                    personal = match[1] == 'personal-files'
                    table = 'personal_files' if personal else 'files'
                    row = con.execute(f'SELECT * FROM {table} WHERE id=?', (match[2],)).fetchone()
                    if not row:
                        raise ApiError(404, '文件不存在')
                    if personal:
                        if row['owner'] != user['id']:
                            raise ApiError(403, '无权访问此文件')
                    else:
                        self.member(con, row['workspace_id'], user)
                    if match[3]:
                        try:
                            if row['size'] > 1024 * 1024 or b'\0' in row['content']:
                                raise UnicodeError()
                            content = row['content'].decode('utf-8')
                        except UnicodeError:
                            raise ApiError(415, '该文件暂不支持文本预览，请下载查看')
                        self.send(200, {'name': row['name'], 'content': content})
                    else:
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/octet-stream')
                        self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(row['name']))
                        self.send_header('Content-Length', str(row['size']))
                        self.send_header('Cache-Control', 'no-store')
                        self.send_header('X-Content-Type-Options', 'nosniff')
                        self.end_headers()
                        self.wfile.write(row['content'])
                    return
                raise ApiError(404, '接口不存在')
        except ApiError as error:
            self.send(error.status, {'error': error.message})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as error:
            print(type(error).__name__, str(error), flush=True)
            self.send(500, {'error': '服务器暂时无法处理请求，请重试'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=8765, type=int)
    args = parser.parse_args()
    with maintenance.server_lock(DATA):
        if (DATA / 'workspace.db').exists():
            with db() as con:
                version = con.execute('PRAGMA user_version').fetchone()[0]
            if version < 3:
                print('升级前备份：', maintenance.backup(DATA, 'before-upgrade'), flush=True)
        init_db()
        maintenance.start_daily_backup(DATA)
        server = ThreadingHTTPServer((args.host, args.port), Handler)
        print(f'Together workspace running at http://{args.host}:{args.port}', flush=True)
        server.serve_forever()
