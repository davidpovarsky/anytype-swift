"""Record the exact native menu-controller lifecycle correction before apply."""
import difflib, hashlib, json
from pathlib import Path

root=Path(__file__).resolve().parents[2]
output=root/'docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/revision-10'
changes={}
def edit(path,old,new):
    if path not in changes:
        before=(root/path).read_text(encoding='utf8');changes[path]=[before,before]
    assert changes[path][1].count(old)==1,(path,old)
    changes[path][1]=changes[path][1].replace(old,new)
helper='Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Utils/EditorNavigationBarHelper/EditorNavigationBarHelper.swift'
edit(helper,'    private let settingsMenuView: UIView','    private let settingsMenuController: UIViewController\n    private let settingsMenuView: UIView')
edit(helper,'        navigationBarView: EditorNavigationBarView,','        navigationBarView: EditorNavigationBarView,\n        parentViewController: UIViewController,')
edit(helper,'        hostingController.view.backgroundColor = .clear','''        // Retain and contain the original SwiftUI menu. Keeping only its view
        // leaves native .sheet presentation without an owning controller.
        self.settingsMenuController = hostingController
        parentViewController.addChild(hostingController)
        hostingController.view.backgroundColor = .clear''')
edit(helper,'        navigationBarView.bannerView = webBannerItem','        hostingController.didMove(toParent: parentViewController)\n\n        navigationBarView.bannerView = webBannerItem')
controller='Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageController.swift'
edit(controller,'        navigationBarView: navigationBarView,','        navigationBarView: navigationBarView,\n        parentViewController: self,')
patch='';inventory=[]
for path,(before,after) in sorted(changes.items()):
    patch+='diff --git a/'+path+' b/'+path+'\n'
    patch+=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path))
    inventory.append(dict(path=path,before_sha256=hashlib.sha256(before.encode()).hexdigest(),after_sha256=hashlib.sha256(after.encode()).hexdigest()))
output.mkdir(parents=True,exist_ok=True)
data=patch.encode()
(output/'native-ios-menu-containment.patch').write_bytes(data)
(output/'native-ios-menu-containment.json').write_text(json.dumps(dict(patch_sha256=hashlib.sha256(data).hexdigest(),authorization='Existing explicit owner standing authorization for complete implementation and protected fixes',status='EXACT_DIFF_RECORDED_BEFORE_APPLY',files=inventory),indent=2)+'\n')
print(json.dumps(dict(sha256=hashlib.sha256(data).hexdigest(),files=len(inventory))))
