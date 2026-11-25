"""Build a public source bundle from an explicit allowlist, never from user data."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0'
SOURCES = (
    '.gitignore', '.dockerignore', '.github/workflows/checks.yml',
    'README.md', 'LICENSE', 'CHANGELOG.md', 'CONTRIBUTING.md', 'SECURITY.md',
    'docs/SELF_HOSTING.md', 'docs/USAGE.md', 'docs/GITHUB_RELEASE.md',
    'server.py', 'collaboration.py', 'maintenance.py', 'package.json',
    'start.bat', 'start-lan.bat', 'start.sh', 'Dockerfile', 'compose.yaml',
    'public/index.html', 'public/shared.js', 'public/features.js',
    'public/client.js', 'public/layout.css', 'public/features.css',
    'tests/test_workspace.py', 'tests/test_maintenance.py', 'tests/preview_fixture.py',
    'scripts/prepare_release.py',
)


def main():
    # Validate everything before creating the output. Old frontend prototypes,
    # databases, backups, env files and Git history never enter this allowlist.
    for name in SOURCES:
        source = ROOT / name
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(ROOT):
            raise RuntimeError('Missing or unsafe release source: ' + name)
    destination = ROOT / 'release' / ('together-workspace-v' + VERSION)
    if destination.exists() or (destination.parent / (destination.name + '.zip')).exists():
        destination = destination.with_name(destination.name + '-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {}
    for name in SOURCES:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
        if name == 'start.sh':
            target.chmod(0o755)
        manifest[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (destination / 'RELEASE-MANIFEST.json').write_text(
        json.dumps({'version': VERSION, 'files': manifest}, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    archive = destination.parent / (destination.name + '.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as output:
        for name in (*SOURCES, 'RELEASE-MANIFEST.json'):
            output.write(destination / name, destination.name + '/' + name)
    print('Public source directory:', destination)
    print('Public source archive:', archive)
    print('Source files:', len(SOURCES), '(plus SHA-256 manifest)')


if __name__ == '__main__':
    main()
