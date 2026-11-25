"""SQLite snapshots and offline restore; no external services required."""
import argparse
from contextlib import contextmanager, closing
from datetime import datetime
import os
from pathlib import Path
import sqlite3
import threading


@contextmanager
def server_lock(data):
    data = Path(data)
    data.mkdir(parents=True, exist_ok=True)
    handle = (data / 'server.lock').open('a+b')
    if os.fstat(handle.fileno()).st_size == 0:
        handle.write(b'0')
        handle.flush()
    handle.seek(0)
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise RuntimeError('服务器正在运行，请先停止后再恢复数据或启动另一个实例')
    try:
        yield
    finally:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        handle.close()


def backup(data, label='manual'):
    data = Path(data)
    source = data / 'workspace.db'
    if not source.exists():
        raise RuntimeError('还没有可以备份的数据库')
    directory = data / 'backups'
    directory.mkdir(exist_ok=True)
    target = directory / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + label + '.db')
    with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('备份校验失败')
    return target


def restore(data, source):
    data, source = Path(data), Path(source).resolve()
    if source == (data / 'workspace.db').resolve() or not source.is_file():
        raise RuntimeError('请选择独立的数据库备份文件')
    with server_lock(data):
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src:
            if src.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('备份数据库损坏，未进行恢复')
            tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'users', 'workspaces', 'messages', 'files', 'sessions'} <= tables:
                raise RuntimeError('这不是有效的工作区备份')
            safety = backup(data, 'before-restore') if (data / 'workspace.db').exists() else None
            with closing(sqlite3.connect(data / 'workspace.db')) as dst:
                src.backup(dst)
                dst.execute('DELETE FROM sessions')
                dst.commit()
        return safety


def start_daily_backup(data):
    def snapshot():
        day = datetime.now().strftime('%Y%m%d')
        if not list((Path(data) / 'backups').glob(day + '-*-daily.db')):
            backup(data, 'daily')
    snapshot()
    def loop():
        event = threading.Event()
        while not event.wait(3600):
            try:
                snapshot()
            except Exception as error:
                print('自动备份失败：', str(error), flush=True)
    threading.Thread(target=loop, daemon=True).start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='工作区数据库备份与恢复')
    parser.add_argument('action', choices=['backup', 'restore'])
    parser.add_argument('source', nargs='?')
    parser.add_argument('--data', default=os.environ.get('WORKSPACE_DATA', str(Path(__file__).resolve().parent / 'data')))
    args = parser.parse_args()
    try:
        if args.action == 'backup':
            print('备份完成：', backup(args.data))
        elif not args.source:
            parser.error('恢复时需要提供备份 .db 路径')
        else:
            safety = restore(args.data, args.source)
            print('恢复完成，请重新启动服务器并登录。恢复前快照：', safety or '无旧数据库')
    except (RuntimeError, sqlite3.Error) as error:
        parser.exit(1, str(error) + '\n')
