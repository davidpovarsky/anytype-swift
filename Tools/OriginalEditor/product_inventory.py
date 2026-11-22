from pathlib import Path
import stat

from framework_profile import sha256
from pbx_source import require


def inventory(root):
    root = Path(root).resolve()
    result = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        require(not path.is_symlink(), 'Exported acceptance products must contain materialized files: ' + relative)
        if stat.S_ISDIR(mode):
            continue
        require(stat.S_ISREG(mode), 'Special file in product closure: ' + relative)
        result[relative] = {'bytes': path.stat().st_size, 'sha256': sha256(path)}
    return result
