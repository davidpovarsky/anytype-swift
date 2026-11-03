"""Prepare the original-host label reload and custom build route for approval."""
from pathlib import Path
import argparse,difflib,hashlib,json

parser=argparse.ArgumentParser(__doc__)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[2]
changes={}
def edit(path,old,new):
    if path not in changes:
        before=(root/path).read_text(encoding='utf8');changes[path]=[before,before]
    assert changes[path][1].count(old)==1,(path,old)
    changes[path][1]=changes[path][1].replace(old,new)

workflow='.github/workflows/torah-inspector-ipados27.yml'
edit(workflow,'          - ipa-only\n','          - ipa-only\n          - native-derived\n')
edit(workflow,'jobs:\n',"""jobs:
  native-derived:
    if: ${{ inputs.route == 'native-derived' }}
    uses: ./.github/workflows/pinkha-native-derived.yml
    secrets: inherit

""")
host='Anytype/Sources/PresentationLayer/TextEditor/Set/Views/Popups/Filters/List/SetFiltersListViewModel.swift'
edit(host,'    private var deletingFilterIds = Set<String>()','''    private var deletingFilterIds = Set<String>()
    @ObservationIgnored
    private var nativeLabelTask: Task<Void, Never>?''')
edit(host,'''        }
    }
    
    private func rowTapped''','''        }
        loadNativeLabels(for: activeFilters)
    }

    private func loadNativeLabels(for filters: [SetFilter]) {
        let spaceId = setDocument.spaceId
        let pending = filters.filter { filter in
            TorahNativePropertyPresentation.definition(filter.relationDetails.key) != nil &&
            filter.filter.value.listValue.values.contains {
                !TorahNativeLabelCache.shared.contains(id: $0.stringValue, space: spaceId)
            }
        }
        guard !pending.isEmpty else { return }
        let missingIds = pending.flatMap { $0.filter.value.listValue.values.map(\\.stringValue) }
            .filter { !TorahNativeLabelCache.shared.contains(id: $0, space: spaceId) }
        nativeLabelTask?.cancel()
        nativeLabelTask = Task { [weak self] in
            for filter in pending {
                await TorahNativePropertyPresentation.loadLabels(
                    space: spaceId, key: filter.relationDetails.key,
                    ids: filter.filter.value.listValue.values.map(\\.stringValue)
                )
            }
            guard !Task.isCancelled, let self else { return }
            // Rebuild only when at least one identity was resolved. Offline
            // misses keep their human fallback and do not schedule retry loops.
            let loaded = missingIds.contains { TorahNativeLabelCache.shared.contains(id: $0, space: spaceId) }
            if loaded { self.updateRows(with: self.setDocument.filters(for: self.viewId)) }
        }
    }
    
    private func rowTapped''')
args.output.mkdir(parents=True,exist_ok=True)
patch='';inventory=[]
for path,(before,after) in sorted(changes.items()):
    patch+='diff --git a/'+path+' b/'+path+'\n'
    patch+=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path))
    inventory.append(dict(path=path,before_sha256=hashlib.sha256(before.encode()).hexdigest(),after_sha256=hashlib.sha256(after.encode()).hexdigest()))
data=patch.encode()
(args.output/'native-ios-followup.patch').write_bytes(data)
(args.output/'native-ios-followup.json').write_text(json.dumps(dict(patch_sha256=hashlib.sha256(data).hexdigest(),status='PENDING_EXACT_OWNER_APPROVAL_NOT_APPLIED',files=inventory),indent=2)+'\n')
print(json.dumps(dict(patch=str(args.output/'native-ios-followup.patch'),sha256=hashlib.sha256(data).hexdigest(),files=len(inventory))))
