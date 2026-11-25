"""Isolated, disposable browser verification server. Never uses the user's data."""
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
import collaboration


class PreviewHandler(server.Handler):
    def user(self, con):
        return dict(con.execute("SELECT id,name,email FROM users WHERE id='aa'").fetchone())


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='together-browser-') as directory:
        server.DATA = Path(directory)
        server.init_db()
        now = time.time()
        with server.db() as con:
            con.executemany('INSERT INTO users VALUES(?,?,?,?)', [('aa','测试用户','preview@example.test','disabled'),('bb','伙伴','peer@example.test','disabled')])
            con.execute('INSERT INTO workspaces VALUES(?,?,?,?,?)', ('cc','项目协作','界面验证','aa',now))
            con.executemany('INSERT INTO members VALUES(?,?)', [('cc','aa'),('cc','bb')])
            con.execute('INSERT INTO channels VALUES(?,?,?,?)', ('dd','cc','项目讨论','测试'))
            con.execute('INSERT INTO group_settings VALUES(?,?,?)', ('dd','aa','workspace'))
            con.execute('INSERT INTO friendships VALUES(?,?,?,?,?)', ('ee','aa','bb','accepted',now))
            con.execute('INSERT INTO folders VALUES(?,?,?,?,?)', ('ff','aa',None,'我的项目',now))
            con.executemany('INSERT INTO messages(channel_id,user_id,body,created) VALUES(?,?,?,?)', [('dd','bb','项目说明已更新，请查收。',now-600),('dd','aa','收到，我们在这里确认修改。',now-500),('dd','bb','@测试用户 今天一起确认最终版本。',now-400)])
            con.execute('INSERT INTO mentions VALUES(?,?,?)', ('group',3,'aa'))
            con.execute('INSERT INTO direct_messages(sender,recipient,body,created) VALUES(?,?,?,?)', ('bb','aa','你好，这里可以直接发送附件。',now-200))
            con.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?,?)', ('ab','cc','dd','bb','项目说明.md',len('# 项目说明\n\n一起完成这个项目。'.encode()),'# 项目说明\n\n一起完成这个项目。'.encode(),now-300))
            con.execute('INSERT INTO message_details VALUES(?,?,?,?,?,?,?)', ('group',2,None,'ab','shared',None,'aa'))
        http = server.ThreadingHTTPServer(('127.0.0.1',8766), PreviewHandler)
        print('Disposable browser fixture at http://127.0.0.1:8766',flush=True)
        try:
            http.serve_forever()
        finally:
            http.server_close()
