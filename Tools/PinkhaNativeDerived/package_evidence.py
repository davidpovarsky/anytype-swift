"""Pack build evidence without DerivedData or dependency checkouts.

Uploading a zip also preserves legal macOS filenames containing colons, which
GitHub's artifact uploader refuses as individual files.
"""
from pathlib import Path
import argparse
import zipfile

parser = argparse.ArgumentParser(__doc__)
parser.add_argument('root', type=Path)
args = parser.parse_args()
root = args.root.resolve()
destination = root/'Pinkha-Native-Derived-Evidence.zip'
with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for path in root.rglob('*'):
        if not path.is_file() or path == destination:
            continue
        parts = path.relative_to(root).parts
        if any(part.startswith('DerivedData') or part == 'SourcePackages' for part in parts):
            continue
        # xcresulttool exports media and UI snapshots with several suffixes,
        # including no suffix. Preserve the whole exported attachment set so
        # its manifest never points at files omitted by this archive filter.
        early_products = parts in {
            ('sdk06-early-products', 'BuildProducts.tar.gz'),
            ('coherent-native-early-products', 'BuildProducts.tar.gz'),
            ('coherent-ui-early-products', 'BuildProducts.tar.gz'),
        }
        if (early_products or path.suffix in {'.log', '.json', '.png', '.txt'}
                or any(part.endswith(('.xcresult', '-attachments')) for part in parts)):
            archive.write(path, path.relative_to(root).as_posix())
print(destination)
