"""Create a repeatable install ZIP without caches, tests or development tools."""
from pathlib import Path
import json
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def package() -> Path:
    source = ROOT / 'custom_components' / 'speicher_ladelogik_ae'
    version = json.loads((source / 'manifest.json').read_text())['version']
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / f'Speicher-Ladelogik-AE-{version}.zip'
    with ZipFile(archive, 'w', ZIP_DEFLATED) as target:
        for folder in (source, ROOT / 'lovelace'):
            for item in sorted(folder.rglob('*')):
                if item.is_file() and '__pycache__' not in item.parts and item.suffix != '.pyc':
                    target.write(item, item.relative_to(ROOT))
        for name in ('README.md', 'CHANGELOG.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md'):
            target.write(ROOT / name, name)
    changelog = (ROOT / 'CHANGELOG.md').read_text()
    section = changelog.split(f'## {version}\n', 1)[1].split('\n## ', 1)[0]
    (output / 'RELEASE.md').write_text(f'# Speicher-Ladelogik A/E {version}\n\n{section.strip()}\n\nUpdate-Anleitung und Lovelace-YAML im ZIP und in der README. Die vorhandene Integration nicht löschen.\n')
    print(archive)
    return archive


if __name__ == '__main__':
    package()
