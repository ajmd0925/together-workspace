import base64
import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from urllib.parse import urlencode
from pathlib import Path
import server


class WorkspaceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        server.DATA = Path(cls.temp.name)
        server.init_db()
        cls.http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.base = 'http://127.0.0.1:' + str(cls.http.server_port)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def client(self):
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, client, path, data=None, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        req = urllib.request.Request(self.base + path, data=None if data is None else json.dumps(data).encode(), headers=headers)
        try:
            with client.open(req) as response:
                raw = response.read()
                return response.status, json.loads(raw) if response.headers.get_content_type() == 'application/json' else raw
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def register(self, client, name):
        status, _ = self.request(client, '/api/register', {'name': name, 'email': server.uid() + '@example.com', 'password': 'test-password-123'})
        self.assertEqual(status, 200)

    def workspace(self, client):
        status, result = self.request(client, '/api/workspaces', {'name': '测试项目', 'description': '共享代码'})
        self.assertEqual(status, 201)
        workspace = result['id']
        self.request(client, '/api/workspaces/' + workspace + '/channels', {'name': '综合讨论'})
        status, details = self.request(client, '/api/workspaces/' + workspace)
        self.assertEqual(status, 200)
        return workspace, details['channels'][0]['id']

    def test_invite_chat_files_and_persistence(self):
        owner, member = self.client(), self.client()
        self.register(owner, '创建者')
        self.register(member, '伙伴')
        workspace, channel = self.workspace(owner)
        self.assertEqual(self.request(member, '/api/workspaces/' + workspace)[0], 403)
        _, invite = self.request(owner, f'/api/workspaces/{workspace}/invite', {})
        self.assertEqual(self.request(member, '/api/join', {'token': invite['token']})[0], 200)
        self.assertEqual(self.request(member, f'/api/workspaces/{workspace}/invite', {})[0], 403)
        self.assertEqual(self.request(member, f'/api/channels/{channel}/messages', {'body': '你好，团队！'})[0], 201)
        _, messages = self.request(owner, f'/api/channels/{channel}/messages')
        self.assertEqual(messages['messages'][0]['body'], '你好，团队！')
        source = '# 中文代码\nprint("hello")\n'
        _, file = self.request(owner, f'/api/channels/{channel}/files', {'name': '示例.py', 'content': base64.b64encode(source.encode()).decode()})
        self.assertEqual(self.request(member, f'/api/files/{file["id"]}')[1], source.encode())
        self.assertEqual(self.request(member, f'/api/files/{file["id"]}/preview')[1]['content'], source)
        server.init_db()
        _, details = self.request(owner, '/api/workspaces/' + workspace)
        self.assertEqual(details['files'][0]['name'], '示例.py')
        self.assertEqual(len(details['members']), 2)

    def test_nonmember_cannot_read_or_write_private_content(self):
        owner, outsider = self.client(), self.client()
        self.register(owner, 'Owner')
        self.register(outsider, 'Outsider')
        workspace, channel = self.workspace(owner)
        _, file = self.request(owner, f'/api/channels/{channel}/files', {'name': 'private.txt', 'content': 'c2VjcmV0'})
        for endpoint in [f'/api/workspaces/{workspace}', f'/api/channels/{channel}/messages', f'/api/files/{file["id"]}', f'/api/files/{file["id"]}/preview']:
            self.assertEqual(self.request(outsider, endpoint)[0], 403)
        self.assertEqual(self.request(outsider, f'/api/channels/{channel}/messages', {'body': 'intrusion'})[0], 403)
        self.assertEqual(self.request(outsider, f'/api/channels/{channel}/files', {'name': 'evil.txt', 'content': ''})[0], 403)

    def test_expired_invite_and_duplicate_channel(self):
        owner, member = self.client(), self.client()
        self.register(owner, 'Owner')
        self.register(member, 'Member')
        workspace, _ = self.workspace(owner)
        _, invite = self.request(owner, f'/api/workspaces/{workspace}/invite', {})
        with server.db() as con:
            con.execute('UPDATE invites SET expires=0 WHERE token=?', (invite['token'],))
        self.assertEqual(self.request(member, '/api/join', {'token': invite['token']})[0], 404)
        self.assertEqual(self.request(owner, f'/api/workspaces/{workspace}/channels', {'name': '综合讨论'})[0], 409)

    def test_auth_csrf_and_logout(self):
        client = self.client()
        self.assertEqual(self.request(client, '/api/me')[0], 401)
        email = server.uid() + '@example.com'
        self.assertEqual(self.request(client, '/api/register', {'name': 'User', 'email': email, 'password': 'test-password-123'})[0], 200)
        self.assertEqual(self.request(client, '/api/workspaces', {'name': 'blocked'}, origin='https://attacker.example')[0], 403)
        self.assertEqual(self.request(client, '/api/logout', {})[0], 200)
        self.assertEqual(self.request(client, '/api/me')[0], 401)
        self.assertEqual(self.request(client, '/api/login', {'email': email, 'password': 'incorrect-password'})[0], 401)
        self.assertEqual(self.request(client, '/api/login', {'email': email, 'password': 'test-password-123'})[0], 200)

    def test_friend_request_consent_private_chat_and_isolation(self):
        alice, bob, outsider = self.client(), self.client(), self.client()
        self.register(alice, 'Alice')
        self.register(bob, 'Bob')
        self.register(outsider, 'Outsider')
        a = self.request(alice, '/api/me')[1]['user']
        b = self.request(bob, '/api/me')[1]['user']
        self.assertEqual(self.request(alice, '/api/dm/' + b['id'], {'body': 'blocked'})[0], 403)
        self.assertEqual(self.request(alice, '/api/friends', {'email': b['email']})[0], 201)
        request_id = self.request(bob, '/api/friends')[1]['friends'][0]['request_id']
        self.assertEqual(self.request(alice, '/api/friends/' + request_id + '/accept', {})[0], 404)
        self.assertEqual(self.request(outsider, '/api/friends/' + request_id + '/accept', {})[0], 404)
        self.assertEqual(self.request(alice, '/api/dm/' + b['id'], {'body': 'still blocked'})[0], 403)
        self.assertEqual(self.request(bob, '/api/friends/' + request_id + '/accept', {})[0], 200)
        self.assertEqual(self.request(alice, '/api/dm/' + b['id'], {'body': '私密消息'})[0], 201)
        self.assertEqual(self.request(bob, '/api/dm/' + a['id'])[1]['messages'][0]['body'], '私密消息')
        self.assertEqual(self.request(outsider, '/api/dm/' + a['id'])[0], 403)
        self.assertEqual(self.request(bob, '/api/friends', {'email': a['email']})[0], 409)
        self.assertEqual(self.request(alice, '/api/friends', {'email': a['email']})[0], 400)
        self.assertEqual(self.request(alice, '/api/profile', {'name': 'New Alice'})[0], 200)
        self.assertEqual(self.request(bob, '/api/dm/' + a['id'])[1]['messages'][0]['author'], 'New Alice')

    def test_personal_nested_folders_and_file_isolation(self):
        owner, stranger = self.client(), self.client()
        self.register(owner, 'Owner')
        self.register(stranger, 'Stranger')
        root = self.request(owner, '/api/folders', {'name': 'Project'})[1]['id']
        child = self.request(owner, '/api/folders', {'name': 'src', 'parent_id': root})[1]['id']
        content = 'print("中文")'
        status, file = self.request(owner, '/api/folders/' + child + '/files', {'name': 'main.py', 'content': base64.b64encode(content.encode()).decode()})
        self.assertEqual(status, 201)
        self.assertEqual(len(self.request(owner, '/api/folders')[1]['folders']), 2)
        self.assertEqual(self.request(owner, '/api/folders/' + root)[1]['files'], [])
        self.assertEqual(self.request(owner, '/api/folders/' + child)[1]['files'][0]['name'], 'main.py')
        self.assertEqual(self.request(owner, '/api/personal-files/' + file['id'] + '/preview')[1]['content'], content)
        self.assertEqual(self.request(owner, '/api/personal-files/' + file['id'])[1], content.encode())
        self.assertEqual(self.request(stranger, '/api/folders')[1]['folders'], [])
        self.assertEqual(self.request(stranger, '/api/folders/' + child)[0], 404)
        self.assertEqual(self.request(stranger, '/api/personal-files/' + file['id'])[0], 403)
        self.assertEqual(self.request(stranger, '/api/folders', {'name': 'evil', 'parent_id': root})[0], 404)
        self.assertEqual(self.request(stranger, '/api/folders/' + child + '/files', {'name': 'evil.txt', 'content': ''})[0], 404)
        server.init_db()
        self.assertEqual(self.request(owner, '/api/folders/' + child)[1]['files'][0]['id'], file['id'])

    def test_workspace_files_without_groups_and_selected_group_workspace(self):
        owner, outsider = self.client(), self.client()
        self.register(owner, 'Owner')
        self.register(outsider, 'Outsider')
        first = self.request(owner, '/api/workspaces', {'name': '项目 A'})[1]['id']
        second = self.request(owner, '/api/workspaces', {'name': '项目 B'})[1]['id']
        self.assertEqual(self.request(owner, '/api/workspaces/' + first)[1]['channels'], [])
        status, file = self.request(owner, '/api/workspaces/' + second + '/files', {'name': 'shared.py', 'content': base64.b64encode(b'print(42)').decode()})
        self.assertEqual(status, 201)
        self.assertEqual(self.request(owner, '/api/workspaces/' + first)[1]['files'], [])
        self.assertEqual(self.request(owner, '/api/workspaces/' + second)[1]['files'][0]['id'], file['id'])
        self.assertEqual(self.request(outsider, '/api/workspaces/' + second + '/files', {'name': 'bad', 'content': ''})[0], 403)
        group = self.request(owner, '/api/workspaces/' + second + '/channels', {'name': '项目讨论'})[1]['id']
        groups = self.request(owner, '/api/groups')[1]['groups']
        self.assertEqual(groups[0]['id'], group)
        self.assertEqual(groups[0]['workspace_id'], second)
        self.assertEqual(groups[0]['workspace_name'], '项目 B')
        self.assertEqual(self.request(outsider, '/api/groups')[1]['groups'], [])
        invite = self.request(owner, '/api/workspaces/' + second + '/invite', {})[1]
        self.request(outsider, '/api/join', {'token': invite['token']})
        self.assertEqual(self.request(outsider, '/api/groups')[1]['groups'][0]['id'], group)
        self.assertEqual(self.request(outsider, '/api/files/' + file['id'])[1], b'print(42)')

    def test_group_history_filters_pagination_and_access(self):
        owner, outsider = self.client(), self.client()
        self.register(owner, 'History owner')
        self.register(outsider, 'History outsider')
        workspace, channel = self.workspace(owner)
        other = self.request(owner, f'/api/workspaces/{workspace}/channels', {'name': '另一个群'})[1]['id']
        user = self.request(owner, '/api/me')[1]['user']['id']
        with server.db() as con:
            con.execute('INSERT INTO messages(channel_id,user_id,body,created) VALUES(?,?,?,?)', (channel, user, '旧记录 100%_中文', 1000))
            con.executemany('INSERT INTO messages(channel_id,user_id,body,created) VALUES(?,?,?,?)', [(channel, user, f'普通消息 {i}', 2000) for i in range(505)])
            con.execute('INSERT INTO messages(channel_id,user_id,body,created) VALUES(?,?,?,?)', (other, user, '不应泄露', 2000))
            for file_id, group, name, created in [('a1', channel, 'PLAN_中文.txt', 1000), ('a2', channel, '边界.txt', 2000), ('a3', other, '其他群.txt', 1000), ('a4', None, '工作区文件.txt', 1000)]:
                con.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,?)', (file_id, workspace, group, user, name, 6, b'secret', created))
        path = f'/api/channels/{channel}/history'
        self.assertEqual(self.request(outsider, path)[0], 403)
        self.assertEqual(self.request(self.client(), path)[0], 401)
        latest = self.request(owner, f'/api/channels/{channel}/messages')[1]['messages']
        self.assertEqual(len(latest), 500)
        result = self.request(owner, path + '?' + urlencode({'q': '100%_中文'}))[1]
        self.assertEqual([m['body'] for m in result['items']], ['旧记录 100%_中文'])
        query = urlencode({'q': 'plan_中文', 'type': 'files', 'since': 1000, 'until': 2000})
        result = self.request(owner, path + '?' + query)[1]
        self.assertEqual([m['id'] for m in result['items']], ['a1'])
        self.assertNotIn('content', result['items'][0])
        rows, cursor = [], None
        while True:
            params = {'cursor': json.dumps(cursor)} if cursor else {}
            status, result = self.request(owner, path + '?' + urlencode(params))
            self.assertEqual(status, 200)
            self.assertLessEqual(len(result['items']), 30)
            rows.extend(result['items'])
            cursor = result['next_cursor']
            if not cursor:
                break
            # New arrivals must not shift the remaining pages or duplicate records.
            if len(rows) == 30:
                self.request(owner, f'/api/channels/{channel}/messages', {'body': '新消息'})
        self.assertEqual(len(rows), 508)
        self.assertEqual(len({(m['kind'], m['id']) for m in rows}), 508)
        self.assertEqual({m['body'] for m in rows if m['kind'] == 'file'}, {'PLAN_中文.txt', '边界.txt'})
        for query in [{'since': 2000, 'until': 1000}, {'since': 'NaN'}, {'until': 'inf'}, {'type': 'bad'}, {'q': 'x' * 201}, {'cursor': '{}'}, {'cursor': '[1,"file",null]'}]:
            self.assertEqual(self.request(owner, path + '?' + urlencode(query))[0], 400)
        self.assertEqual(self.request(owner, path + '?since=3000&until=4000')[1]['items'], [])

    def test_private_history_scope_and_full_history(self):
        alice, bob, third = self.client(), self.client(), self.client()
        for client, name in [(alice, 'Search Alice'), (bob, 'Search Bob'), (third, 'Search Third')]:
            self.register(client, name)
        a, b, c = [self.request(client, '/api/me')[1]['user'] for client in (alice, bob, third)]
        path = '/api/dm/' + b['id'] + '/history'
        self.assertEqual(self.request(alice, path)[0], 403)
        with server.db() as con:
            for peer in (b, c):
                con.execute('INSERT INTO friendships VALUES(?,?,?,?,?)', (server.uid(), a['id'], peer['id'], 'accepted', 1))
            con.execute('INSERT INTO direct_messages(sender,recipient,body,created) VALUES(?,?,?,?)', (b['id'], a['id'], '很久以前的记录', 1000))
            con.execute('INSERT INTO direct_messages(sender,recipient,body,created) VALUES(?,?,?,?)', (a['id'], c['id'], '很久以前的记录：第三人', 1000))
            con.executemany('INSERT INTO direct_messages(sender,recipient,body,created) VALUES(?,?,?,?)', [(a['id'], b['id'], '后续消息', 2000) for _ in range(501)])
        params = urlencode({'q': '很久以前', 'type': 'messages', 'since': 1000, 'until': 2000})
        result = self.request(alice, path + '?' + params)[1]
        self.assertEqual([m['body'] for m in result['items']], ['很久以前的记录'])
        self.assertEqual(self.request(bob, '/api/dm/' + a['id'] + '/history?' + params)[1], result)
        self.assertEqual(self.request(third, path)[0], 403)
        self.assertEqual(self.request(alice, path + '?type=files')[1]['items'], [])

    def test_private_groups_standalone_and_invitation_scope(self):
        owner, member, outsider = self.client(), self.client(), self.client()
        for client, name in [(owner, 'Group owner'), (member, 'Group member'), (outsider, 'Group outsider')]:
            self.register(client, name)
        workspace, public = self.workspace(owner)
        secret = self.request(owner, '/api/groups', {'name': '仅邀请', 'workspace_id': workspace})[1]['id']
        independent = self.request(owner, '/api/groups', {'name': '独立群聊'})[1]['id']
        invite = self.request(owner, f'/api/workspaces/{workspace}/invite', {})[1]['token']
        self.request(member, '/api/join', {'token': invite})
        self.assertEqual([g['id'] for g in self.request(member, '/api/groups')[1]['groups']], [public])
        for suffix in ['messages', 'members', 'history']:
            self.assertEqual(self.request(member, f'/api/channels/{secret}/{suffix}')[0], 403)
        self.assertEqual([g['id'] for g in self.request(member, f'/api/workspaces/{workspace}')[1]['channels']], [public])
        token = self.request(owner, f'/api/channels/{secret}/invite', {})[1]['token']
        preview = self.request(outsider, '/api/join/preview?' + urlencode({'token': token}))[1]
        self.assertEqual(preview['name'], '仅邀请')
        self.assertIn('全部文件', preview['scope'])
        self.assertEqual(self.request(outsider, f'/api/channels/{secret}/messages')[0], 403)
        self.request(outsider, '/api/join', {'token': token})
        self.assertEqual(self.request(outsider, f'/api/channels/{secret}/messages')[0], 200)
        self.assertEqual(self.request(outsider, f'/api/channels/{independent}/messages')[0], 403)
        self.assertEqual(self.request(outsider, f'/api/channels/{secret}/invite', {})[0], 403)
        standalone_token = self.request(owner, f'/api/channels/{independent}/invite', {})[1]['token']
        self.request(member, '/api/join', {'token': standalone_token})
        file = self.request(member, f'/api/channels/{independent}/files', {'name': 'standalone.txt', 'content': 'YQ=='})[1]['id']
        self.assertEqual(self.request(owner, '/api/files/' + file)[1], b'a')
        self.assertEqual(self.request(outsider, '/api/files/' + file)[0], 403)
        with server.db() as con:
            con.execute('UPDATE group_invites SET expires=0 WHERE token=?', (standalone_token,))
        self.assertEqual(self.request(outsider, '/api/join/preview?' + urlencode({'token': standalone_token}))[0], 404)

    def test_replies_mentions_read_positions_and_retry_deduplication(self):
        owner, member = self.client(), self.client()
        self.register(owner, 'Writer')
        self.register(member, 'Reader')
        workspace, group = self.workspace(owner)
        token = self.request(owner, f'/api/workspaces/{workspace}/invite', {})[1]['token']
        self.request(member, '/api/join', {'token': token})
        reader = self.request(member, '/api/me')[1]['user']['id']
        path = f'/api/channels/{group}/messages'
        first = self.request(owner, path, {'body': '开始讨论', 'nonce': 'first-message'})[1]['id']
        data = {'body': '@Reader 请查看', 'mentions': [reader], 'reply_id': first, 'nonce': 'retry-message'}
        mid = self.request(owner, path, data)[1]['id']
        self.assertEqual(self.request(owner, path, data)[1]['id'], mid)
        messages = self.request(member, path)[1]
        self.assertEqual(len(messages['messages']), 2)
        self.assertEqual(messages['messages'][1]['reply']['id'], first)
        self.assertTrue(messages['messages'][1]['mentioned'])
        self.assertEqual(messages['unread'], 2)
        self.assertEqual(messages['mentions'], 1)
        state_path = f'/api/conversations/group/{group}/state'
        self.assertEqual(self.request(member, state_path, {'read_id': mid, 'pinned': True})[0], 200)
        self.request(member, state_path, {'read_id': first})
        status = self.request(member, '/api/activity')[1]['groups'][0]
        self.assertEqual((status['unread'], status['mentions'], status['read_id'], status['pinned']), (0, 0, mid, True))
        other = self.request(owner, '/api/groups', {'name': 'Other'})[1]['id']
        foreign = self.request(owner, f'/api/channels/{other}/messages', {'body': 'foreign'})[1]['id']
        self.assertEqual(self.request(member, path, {'body': 'bad reply', 'reply_id': foreign})[0], 404)
        self.assertEqual(self.request(member, state_path, {'read_id': foreign})[0], 404)
        self.assertEqual(self.request(owner, path, {'body': 'bad mention', 'mentions': ['not-a-member']})[0], 400)

    def test_saved_messages_pin_visibility_and_old_context(self):
        owner, member = self.client(), self.client()
        self.register(owner, 'Save owner')
        self.register(member, 'Save member')
        workspace, group = self.workspace(owner)
        token = self.request(owner, f'/api/workspaces/{workspace}/invite', {})[1]['token']
        self.request(member, '/api/join', {'token': token})
        mid = self.request(owner, f'/api/channels/{group}/messages', {'body': 'Important'})[1]['id']
        endpoint = f'/api/conversations/group/{group}'
        self.request(owner, endpoint + '/saved', {'message_id': mid})
        self.assertEqual(len(self.request(owner, endpoint + '/saved')[1]['messages']), 1)
        self.assertEqual(self.request(member, endpoint + '/saved')[1]['messages'], [])
        self.request(owner, endpoint + '/saved', {'message_id': mid, 'pinned': True})
        self.assertTrue(self.request(member, endpoint + '/saved')[1]['messages'][0]['pinned'])
        self.request(member, endpoint + '/saved', {'message_id': mid, 'unpin': True})
        self.assertFalse(self.request(owner, endpoint + '/saved')[1]['messages'][0]['pinned'])
        user = self.request(owner, '/api/me')[1]['user']['id']
        with server.db() as con:
            con.executemany('INSERT INTO messages(channel_id,user_id,body,created) VALUES(?,?,?,?)', [(group, user, 'Later', 2000+i) for i in range(510)])
        context = self.request(member, endpoint + '/context?id=' + str(mid))[1]['messages']
        self.assertEqual(context[0]['body'], 'Important')
        self.assertEqual(len(context), 21)

    def test_dm_attachments_and_conversation_isolation(self):
        alice, bob, outsider = self.client(), self.client(), self.client()
        for client, name in [(alice, 'File Alice'), (bob, 'File Bob'), (outsider, 'File outsider')]:
            self.register(client, name)
        a, b = [self.request(c, '/api/me')[1]['user'] for c in (alice, bob)]
        self.request(alice, '/api/friends', {'email': b['email']})
        rid = self.request(bob, '/api/friends')[1]['friends'][0]['request_id']
        self.request(bob, '/api/friends/' + rid + '/accept', {})
        upload = {'name': 'private.py', 'content': base64.b64encode(b'print(42)').decode(), 'nonce': 'upload-once'}
        file = self.request(alice, '/api/dm/' + b['id'] + '/files', upload)[1]['id']
        self.assertEqual(self.request(alice, '/api/dm/' + b['id'] + '/files', upload)[1]['id'], file)
        messages = self.request(bob, '/api/dm/' + a['id'])[1]
        self.assertEqual(len(messages['messages']), 1)
        self.assertEqual(messages['messages'][0]['attachment']['name'], 'private.py')
        self.assertEqual(messages['unread'], 1)
        self.assertEqual(self.request(bob, '/api/dm-files/' + file)[1], b'print(42)')
        self.assertEqual(self.request(outsider, '/api/dm-files/' + file)[0], 403)
        self.assertEqual(self.request(outsider, '/api/dm-files/' + file + '/versions')[0], 403)
        self.assertEqual(self.request(bob, '/api/dm/' + a['id'] + '/history?type=files')[1]['items'][0]['id'], file)
        reply = self.request(bob, '/api/dm/' + a['id'], {'body': '收到了', 'reply_id': messages['messages'][0]['id']})
        self.assertEqual(reply[0], 201)
        self.assertEqual(self.request(alice, '/api/activity')[1]['dm'][b['id']]['unread'], 1)

    def test_file_folders_versions_trash_and_permissions(self):
        owner, outsider = self.client(), self.client()
        self.register(owner, 'Version owner')
        self.register(outsider, 'Version outsider')
        workspace, group = self.workspace(owner)
        folder = self.request(owner, f'/api/workspaces/{workspace}/folders', {'name': 'src'})[1]['id']
        other = self.request(owner, '/api/workspaces', {'name': 'Other workspace'})[1]['id']
        wrong_folder = self.request(owner, f'/api/workspaces/{other}/folders', {'name': 'wrong'})[1]['id']
        endpoint = f'/api/workspaces/{workspace}/files'
        first = {'name': 'main.py', 'content': base64.b64encode(b'version one').decode(), 'folder_id': folder}
        file = self.request(owner, endpoint, first)[1]['id']
        updated = {**first, 'content': base64.b64encode(b'version two').decode()}
        self.assertEqual(self.request(owner, endpoint, updated)[0], 409)
        self.assertEqual(self.request(owner, endpoint, {**updated, 'mode': 'replace'})[1]['id'], file)
        base = '/api/files/' + file
        versions = self.request(owner, base + '/versions')[1]
        self.assertEqual(versions['revision'], 2)
        self.assertEqual(len(versions['versions']), 1)
        self.assertEqual(self.request(owner, base)[1], b'version two')
        self.assertEqual(self.request(outsider, base + '/manage', {'action': 'restore-version', 'version_id': versions['versions'][0]['id']})[0], 403)
        self.request(owner, base + '/manage', {'action': 'restore-version', 'version_id': versions['versions'][0]['id']})
        self.assertEqual(self.request(owner, base)[1], b'version one')
        self.assertEqual(self.request(owner, base + '/versions')[1]['revision'], 3)
        # Updating an existing workspace file from a different group still makes
        # that attachment discoverable in the uploading conversation.
        second_group = self.request(owner, f'/api/workspaces/{workspace}/channels', {'name': '版本讨论'})[1]['id']
        group_file = self.request(owner, f'/api/channels/{group}/files', {'name': 'shared.txt', 'content': 'YQ=='})[1]['id']
        self.request(owner, f'/api/channels/{second_group}/files', {'name': 'shared.txt', 'content': 'Yg==', 'mode': 'replace'})
        self.assertEqual(self.request(owner, f'/api/channels/{second_group}/history?type=files')[1]['items'][0]['id'], group_file)
        self.request(owner, '/api/files/' + group_file + '/manage', {'action': 'trash'})
        self.assertEqual(self.request(owner, f'/api/channels/{second_group}/history?type=files')[1]['items'], [])
        self.assertEqual(self.request(owner, base + '/manage', {'action': 'move', 'folder_id': wrong_folder})[0], 404)
        self.request(owner, base + '/manage', {'action': 'rename', 'name': 'renamed.py'})
        self.request(owner, base + '/manage', {'action': 'move', 'folder_id': None})
        self.request(owner, base + '/manage', {'action': 'trash'})
        self.assertEqual(self.request(owner, base)[0], 404)
        details = self.request(owner, f'/api/workspaces/{workspace}')[1]
        self.assertEqual(details['files'], [])
        self.assertIn('renamed.py', [f['name'] for f in details['trash']])
        self.request(owner, base + '/manage', {'action': 'restore'})
        self.assertEqual(self.request(owner, base)[1], b'version one')
        kept = self.request(owner, endpoint, {**first, 'mode': 'keep'})[1]['id']
        self.assertNotEqual(kept, file)
        child = self.request(owner, f'/api/workspaces/{workspace}/folders', {'name': 'child', 'parent_id': folder})[1]['id']
        self.assertEqual(self.request(owner, f'/api/shared-folders/{folder}/manage', {'parent_id': child})[0], 400)
        self.assertEqual(self.request(outsider, f'/api/workspaces/{workspace}/folders')[0], 403)
        self.assertEqual(self.request(outsider, base + '/manage', {'action': 'trash'})[0], 403)

    def test_personal_file_management_stays_private(self):
        owner, outsider = self.client(), self.client()
        self.register(owner, 'Personal owner')
        self.register(outsider, 'Personal outsider')
        folder = self.request(owner, '/api/folders', {'name': 'one'})[1]['id']
        second = self.request(owner, '/api/folders', {'name': 'two'})[1]['id']
        forbidden = self.request(outsider, '/api/folders', {'name': 'private'})[1]['id']
        file = self.request(owner, f'/api/folders/{folder}/files', {'name': 'test.txt', 'content': 'YQ=='})[1]['id']
        endpoint = '/api/personal-files/' + file + '/manage'
        self.assertEqual(self.request(owner, endpoint, {'action': 'move', 'folder_id': forbidden})[0], 404)
        self.request(owner, endpoint, {'action': 'move', 'folder_id': second})
        self.assertEqual(self.request(owner, '/api/folders/' + folder)[1]['files'], [])
        self.assertEqual(self.request(owner, '/api/folders/' + second)[1]['files'][0]['id'], file)
        self.request(owner, endpoint, {'action': 'trash'})
        self.assertEqual(self.request(owner, '/api/folders/' + folder)[1]['trash'][0]['id'], file)
        self.request(owner, endpoint, {'action': 'restore'})
        self.assertEqual(self.request(outsider, endpoint, {'action': 'restore'})[0], 403)

    def test_group_member_removal_permissions_and_reinvitation(self):
        for visibility in ('workspace', 'private', 'standalone'):
            with self.subTest(visibility=visibility):
                owner, member, outsider = self.client(), self.client(), self.client()
                for client in (owner, member, outsider):
                    self.register(client, 'Removal test')
                owner_id = self.request(owner, '/api/me')[1]['user']['id']
                member_id = self.request(member, '/api/me')[1]['user']['id']
                outsider_id = self.request(outsider, '/api/me')[1]['user']['id']
                workspace, other_group = self.workspace(owner)
                payload = {'name': 'Removable group'}
                if visibility != 'standalone':
                    payload.update(workspace_id=workspace, visibility=visibility)
                group = self.request(owner, '/api/groups', payload)[1]['id']
                base = f'/api/channels/{group}'
                token = self.request(owner, base + '/invite', {})[1]['token']
                self.request(member, '/api/join', {'token': token})
                # Public groups include members who joined through a workspace invite.
                if visibility == 'workspace':
                    with server.db() as con:
                        con.execute('DELETE FROM group_members WHERE channel_id=? AND user_id=?', (group, member_id))
                mid = self.request(member, base + '/messages', {'body': 'Retained history'})[1]['id']
                file = self.request(member, base + '/files', {'name': 'retain.txt', 'content': 'YQ=='})[1]['id']
                self.request(member, f'/api/conversations/group/{group}/state', {'pinned': True})
                remove = base + f'/members/{member_id}/remove'
                self.assertEqual(self.request(member, base + f'/members/{owner_id}/remove', {})[0], 403)
                self.assertEqual(self.request(outsider, remove, {})[0], 403)
                self.assertEqual(self.request(owner, base + f'/members/{owner_id}/remove', {})[0], 400)
                self.assertEqual(self.request(owner, base + f'/members/{outsider_id}/remove', {})[0], 404)
                self.assertEqual(self.request(owner, remove, {})[0], 200)
                self.assertEqual(self.request(owner, remove, {})[0], 404)
                for suffix in ('messages', 'members', 'history'):
                    self.assertEqual(self.request(member, base + '/' + suffix)[0], 403)
                for suffix, data in [('messages', {'body': 'Blocked'}), ('files', {'name': 'blocked.txt', 'content': 'YQ=='})]:
                    self.assertEqual(self.request(member, base + '/' + suffix, data)[0], 403)
                for path in (f'/api/conversations/group/{group}/saved', f'/api/conversations/group/{group}/context?id={mid}'):
                    self.assertEqual(self.request(member, path)[0], 403)
                self.assertNotIn(group, [g['id'] for g in self.request(member, '/api/groups')[1]['groups']])
                self.assertNotIn(group, [g['id'] for g in self.request(member, '/api/activity')[1]['groups']])
                self.assertNotIn(member_id, [p['id'] for p in self.request(owner, base + '/members')[1]['members']])
                self.assertEqual(self.request(member, '/api/join', {'token': token})[0], 404)
                self.assertEqual(self.request(member, '/api/join/preview?' + urlencode({'token': token}))[0], 404)
                self.assertIn(mid, [m['id'] for m in self.request(owner, base + '/messages')[1]['messages']])
                self.assertEqual(self.request(member, '/api/files/' + file)[0], 403 if visibility == 'standalone' else 200)
                if visibility != 'standalone':
                    self.assertEqual(self.request(member, f'/api/workspaces/{workspace}')[0], 200)
                    self.assertEqual(self.request(member, f'/api/channels/{other_group}/messages')[0], 200)
                    workspace_token = self.request(owner, f'/api/workspaces/{workspace}/invite', {})[1]['token']
                    self.request(member, '/api/join', {'token': workspace_token})
                    self.assertEqual(self.request(member, base + '/messages')[0], 403)
                # Exclusions survive server schema initialization and valid new group invites restore access.
                server.init_db()
                self.assertEqual(self.request(member, base + '/messages')[0], 403)
                new_token = self.request(owner, base + '/invite', {})[1]['token']
                self.assertEqual(self.request(member, '/api/join', {'token': new_token})[0], 200)
                self.assertEqual(self.request(member, base + '/messages')[0], 200)
                self.assertEqual(self.request(member, '/api/files/' + file)[0], 200)

    def test_remove_friend_revokes_both_sides_and_preserves_history(self):
        alice, bob, third = self.client(), self.client(), self.client()
        for client in (alice, bob, third):
            self.register(client, 'Friend removal test')
        a = self.request(alice, '/api/me')[1]['user']
        b = self.request(bob, '/api/me')[1]['user']
        self.request(alice, '/api/friends', {'email': b['email']})
        rid = self.request(bob, '/api/friends')[1]['friends'][0]['request_id']
        self.request(bob, f'/api/friends/{rid}/accept', {})
        mid = self.request(alice, '/api/dm/' + b['id'], {'body': 'Keep this history'})[1]['id']
        file = self.request(alice, '/api/dm/' + b['id'] + '/files', {'name': 'private.txt', 'content': 'YQ=='})[1]['id']
        for client, peer in ((alice, b), (bob, a)):
            self.request(client, f'/api/conversations/dm/{peer["id"]}/state', {'pinned': True})
        workspace, group = self.workspace(alice)
        token = self.request(alice, f'/api/workspaces/{workspace}/invite', {})[1]['token']
        self.request(bob, '/api/join', {'token': token})
        self.assertEqual(self.request(third, '/api/friends/' + b['id'] + '/remove', {})[0], 403)
        self.assertEqual(self.request(alice, '/api/friends/' + b['id'] + '/remove', {})[0], 200)
        for client, peer in ((alice, b), (bob, a)):
            self.assertEqual(self.request(client, '/api/friends')[1]['friends'], [])
            for path in ('/api/dm/' + peer['id'], '/api/dm/' + peer['id'] + '/history', f'/api/conversations/dm/{peer["id"]}/saved', f'/api/conversations/dm/{peer["id"]}/context?id={mid}', '/api/dm-files/' + file):
                self.assertEqual(self.request(client, path)[0], 403)
            self.assertEqual(self.request(client, '/api/dm/' + peer['id'], {'body': 'Blocked'})[0], 403)
            self.assertEqual(self.request(client, '/api/dm/' + peer['id'] + '/files', {'name': 'blocked.txt', 'content': 'YQ=='})[0], 403)
            self.assertEqual(self.request(client, '/api/activity')[1]['dm'], {})
            self.assertEqual(self.request(client, f'/api/channels/{group}/messages')[0], 200)
        self.request(bob, '/api/friends', {'email': a['email']})
        rid = self.request(alice, '/api/friends')[1]['friends'][0]['request_id']
        self.assertEqual(self.request(bob, '/api/dm/' + a['id'])[0], 403)
        self.request(alice, f'/api/friends/{rid}/accept', {})
        self.assertIn(mid, [m['id'] for m in self.request(bob, '/api/dm/' + a['id'])[1]['messages']])
        self.assertEqual(self.request(bob, '/api/dm-files/' + file)[0], 200)
        self.assertFalse(self.request(bob, '/api/activity')[1]['dm'][a['id']]['pinned'])
        self.assertEqual(self.request(bob, '/api/friends/' + a['id'] + '/remove', {})[0], 200)

    def test_attachment_storage_scopes_and_search(self):
        owner, member, outsider = self.client(), self.client(), self.client()
        for client in (owner, member, outsider):
            self.register(client, 'Storage test')
        workspace, public = self.workspace(owner)
        private = self.request(owner, '/api/groups', {'name': 'Private attachments', 'workspace_id': workspace})[1]['id']
        other = self.request(owner, '/api/groups', {'name': 'Other attachments', 'workspace_id': workspace})[1]['id']
        standalone = self.request(owner, '/api/groups', {'name': 'Standalone'})[1]['id']
        token = self.request(owner, f'/api/workspaces/{workspace}/invite', {})[1]['token']
        self.request(member, '/api/join', {'token': token})

        def upload(group, storage, name, **extra):
            return self.request(owner, f'/api/channels/{group}/files', {'name': name, 'content': 'YQ==', 'storage': storage, **extra})

        local = upload(private, 'group', 'local.txt', nonce='local-upload')[1]['id']
        shared = upload(private, 'workspace', 'shared.txt')[1]['id']
        other_local = upload(other, 'group', 'other-local.txt')[1]['id']
        other_shared = upload(other, 'workspace', 'other-shared.txt')[1]['id']
        direct = self.request(owner, f'/api/workspaces/{workspace}/files', {'name': 'direct.txt', 'content': 'YQ=='})[1]['id']
        self.assertEqual(upload(private, 'group', 'local.txt', nonce='local-upload')[1]['id'], local)
        self.assertEqual(upload(private, 'workspace', 'local.txt', nonce='local-upload')[0], 409)
        self.assertEqual(upload(private, 'invalid', 'bad.txt')[0], 400)
        self.assertEqual(upload(standalone, 'workspace', 'bad.txt')[0], 400)
        self.assertEqual(upload(private, 'group', 'bad.txt', folder_id='ff')[0], 400)
        self.assertEqual(self.request(member, '/api/files/' + local)[0], 403)
        self.assertEqual(self.request(member, '/api/files/' + shared)[0], 200)

        self.assertEqual(self.request(outsider, '/api/files/' + shared)[0], 403)
        listing = self.request(member, f'/api/workspaces/{workspace}')[1]['files']
        self.assertEqual({f['id'] for f in listing}, {shared, other_shared, direct})
        self.assertTrue(all(f['storage'] == 'workspace' for f in listing))

        def search(client, group, scope, **extra):
            return self.request(client, f'/api/channels/{group}/history?' + urlencode({'type': 'files', 'file_scope': scope, **extra}))

        self.assertEqual({f['id'] for f in search(owner, private, 'group')[1]['items']}, {local})
        self.assertEqual({f['id'] for f in search(owner, private, 'workspace')[1]['items']}, {shared, other_shared, direct})
        self.assertEqual({f['id'] for f in search(owner, private, 'conversation')[1]['items']}, {local, shared})
        self.assertEqual({f['id'] for f in search(member, public, 'workspace')[1]['items']}, {shared, other_shared, direct})
        self.assertEqual(search(member, private, 'workspace')[0], 403)
        self.assertEqual(search(owner, standalone, 'workspace')[0], 400)
        self.assertEqual(search(owner, private, 'invalid')[0], 400)
        self.assertEqual(search(owner, private, 'workspace', q='direct')[1]['items'][0]['id'], direct)
        self.assertEqual(search(owner, private, 'workspace', since=253402300000)[1]['items'], [])
        attachments = [m['attachment'] for m in self.request(owner, f'/api/channels/{private}/messages')[1]['messages']]
        self.assertEqual({f['storage'] for f in attachments}, {'group', 'workspace'})
        self.assertEqual(upload(private, 'group', 'local.txt')[0], 409)
        copy = upload(private, 'group', 'local.txt', mode='keep')[1]['id']
        self.assertEqual(self.request(owner, '/api/files/' + copy + '/preview')[1]['name'], 'local (2).txt')
        self.assertEqual(upload(private, 'group', 'local.txt', mode='replace')[1]['id'], local)
        self.assertEqual(self.request(owner, '/api/files/' + local + '/versions')[1]['revision'], 2)
        self.request(owner, '/api/files/' + local + '/manage', {'action': 'trash'})
        self.assertNotIn(local, {f['id'] for f in search(owner, private, 'group')[1]['items']})
        self.request(owner, '/api/files/' + local + '/manage', {'action': 'restore'})
        token = self.request(owner, f'/api/channels/{private}/invite', {})[1]['token']
        self.request(member, '/api/join', {'token': token})
        self.assertEqual(self.request(member, '/api/files/' + local)[0], 200)
        uid = self.request(member, '/api/me')[1]['user']['id']
        self.request(owner, f'/api/channels/{private}/members/{uid}/remove', {})
        self.assertEqual(self.request(member, '/api/files/' + local)[0], 403)
        self.assertEqual(self.request(member, '/api/files/' + shared)[0], 200)

    def test_group_and_workspace_same_names_do_not_replace_each_other(self):
        owner = self.client()
        self.register(owner, 'Filename test')
        workspace, group = self.workspace(owner)
        other = self.request(owner, '/api/groups', {'name': 'Other', 'workspace_id': workspace})[1]['id']
        payload = {'name': 'same.py', 'content': 'YQ=='}
        local = self.request(owner, f'/api/channels/{group}/files', {**payload, 'storage': 'group'})[1]['id']
        shared = self.request(owner, f'/api/channels/{group}/files', {**payload, 'storage': 'workspace', 'mode': 'replace'})[1]['id']
        separate = self.request(owner, f'/api/channels/{other}/files', {**payload, 'storage': 'group', 'mode': 'replace'})[1]['id']
        self.assertEqual(len({local, shared, separate}), 3)
        for file in (local, shared, separate):
            self.assertEqual(self.request(owner, f'/api/files/{file}/preview')[1]['name'], 'same.py')
            self.assertEqual(self.request(owner, f'/api/files/{file}/versions')[1]['revision'], 1)
        self.assertEqual(self.request(owner, f'/api/files/{local}/manage', {'action': 'move', 'folder_id': None})[0], 400)
        for i in range(34):
            self.request(owner, f'/api/channels/{group}/files', {'name': f'page-{i}.txt', 'content': 'YQ==', 'storage': 'group'})
        path = f'/api/channels/{group}/history?type=files&file_scope=group'
        first = self.request(owner, path)[1]
        second = self.request(owner, path + '&' + urlencode({'cursor': json.dumps(first['next_cursor'])}))[1]
        self.assertEqual(len(first['items']), 30)
        self.assertEqual(len(second['items']), 5)
        self.assertEqual(len({f['id'] for f in first['items'] + second['items']}), 35)
        self.assertTrue(all(f['storage'] == 'group' for f in first['items'] + second['items']))

    def test_file_validation_and_binary_download(self):
        owner = self.client()
        self.register(owner, 'Owner')
        _, channel = self.workspace(owner)
        for name, content in [('../file.txt', ''), ('bad.txt', '@@@'), ('bad\n.txt', '')]:
            self.assertEqual(self.request(owner, f'/api/channels/{channel}/files', {'name': name, 'content': content})[0], 400)
        raw = b'\x00\xff\x10binary'
        _, file = self.request(owner, f'/api/channels/{channel}/files', {'name': 'archive.bin', 'content': base64.b64encode(raw).decode()})
        self.assertEqual(self.request(owner, f'/api/files/{file["id"]}/preview')[0], 415)
        self.assertEqual(self.request(owner, f'/api/files/{file["id"]}')[1], raw)


if __name__ == '__main__':
    unittest.main()
