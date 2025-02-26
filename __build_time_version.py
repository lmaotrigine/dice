import pathlib
import re

ROOT = pathlib.Path(__file__).parent / 'dice'


def get_version() -> str:
    version = ''
    init = (ROOT / '__init__.py').read_text('utf-8')
    m = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', init, re.MULTILINE)
    if m:
        version = m.group(1)
    if not version:
        msg = 'version is not set'
        raise RuntimeError(msg)
    if version.endswith(('a', 'b', 'rc')):
        try:
            import subprocess  # noqa: S404

            p = subprocess.Popen(['git', 'rev-list', '--count', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # noqa: S603, S607
            out, _ = p.communicate()
            if out:
                version += out.decode('utf-8').strip()
            p = subprocess.Popen(  # noqa: S603
                ['git', 'rev-parse', '--short', 'HEAD'],  # noqa: S607
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, _ = p.communicate()
            if out:
                version += '+g' + out.decode('utf-8').strip()
        except Exception:  # noqa: BLE001, S110
            pass
    return version
