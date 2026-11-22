import pathlib,subprocess,json,hashlib,re,datetime
w=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-authority-integration-20261122")
head="d33a41338bd0a56326fd02c05977c10d1c4c7baa"
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-space-bind-20261122")
assert not out.exists(),"Owned control directory exists; inspect instead of duplicate preparation"
out.mkdir();tests=out/"Tests"/"CompositionControls";tests.mkdir(parents=True)
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):
 p=subprocess.run(["git",*args],cwd=w,capture_output=True,timeout=60);p.check_returncode();return p.stdout
assert git("rev-parse","HEAD").decode().strip()==head
records=[]
def original(path):
 data=git("show",head+":"+path);dest=out/"original"/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 records.append({"path":path,"git_blob":git("rev-parse",head+":"+path).decode().strip(),"sha256":sha(data)})
 return data.decode()
def write(name,text):(tests/name).write_bytes(text.encode())
def no_imports(text):return re.sub(r"^(?:@preconcurrency )?import [^\n]+\n","",text,flags=re.M)
owner_path="Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift"
owner_base=original(owner_path)
owner=(w/owner_path).read_bytes()
assert sha(owner)=="bf619f8e022c99d6f7f5f8e374b7213989639502801d36b754dcd95aedae9873"
assert sha(owner_base.encode())=="b0ae02be8c28c22246d29bf927cb154e10019d841f3b831771f968a8938f7d46"
(out/"Owner.candidate.swift").write_bytes(owner)
write("Owner.swift","import Foundation\n"+no_imports(owner.decode()))
life=original("Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteLifetime.swift")
write("Lifetime.swift",life+"""
extension EditorDocumentWriteLifetime {
    var probeAdmissionAndWaiterCounts: (Int, Int) {
        lock.lock()
        defer { lock.unlock() }
        return (admittedOperations.count, drainWaiters.count)
    }
}
""")
write("Operation.swift","import Foundation\n"+no_imports(original("Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOperation.swift")))
write("Binding.swift",original("Modules/ProtobufMessages/Sources/InvocationDispatchBinding.swift"))
write("AccountManager.swift","import Foundation\n"+no_imports(original("Anytype/Sources/ServiceLayer/Account/AccountManager.swift")))
participant=original("Modules/Services/Sources/Models/Participant.swift")
extensions=original("Anytype/Sources/Models/Extensions/Participant+Extensions.swift")
enums=[]
for name in ["ParticipantPermissions","ParticipantStatus","SpaceAccessType"]:
 text=original("Modules/ProtobufMessages/Sources/Protocol/Models/Anytype_Model_"+name+".swift")
 start=text.index("public enum ");end=text.index("\nextension ",start)
 value=text[start:end];assert value.count("SwiftProtobuf.Enum")==1
 enums.append(value.replace("SwiftProtobuf.Enum","RawRepresentable, Hashable, Sendable"))
value=participant[participant.index("public typealias ParticipantPermissions"):participant.index("extension Participant: DetailsModel {")]
def property_body(text,name):
 start=text.index("    var "+name+": Bool {");i=text.index("{",start)+1;balance=1
 while balance:
  if text[i]=="{":balance+=1
  elif text[i]=="}":balance-=1
  i+=1
 return text[start:i]+"\n"
values="import Foundation\n"+"\n".join(enums)+"\n"+value+"\nextension ParticipantPermissions {\n"+property_body(extensions,"canEdit")+"\n"+property_body(extensions,"isModerator")+"}\n"
values+="\n"+no_imports(original("Modules/Services/Sources/Models/Space/SpaceAccessType.swift"))
write("NativePermissionValues.swift",values)
write("SpacePermissions.swift","import Foundation\n"+no_imports(original("Anytype/Sources/ServiceLayer/ParticipantSpacesStorage/Model/SpacePermissions.swift")))
participants=original("Anytype/Sources/ServiceLayer/ParticipantStorage/ParticipantsStorage.swift")
assert sha(participants.encode())=="7fc5fc32d5dd7f21d6133f72511ccc133dea9dbe6bdabcbc9a5e435deffa8da1"
regions=participants[participants.index("// ORIGINAL_CHANNEL_PIN_PERMISSION_BEGIN"):participants.index("protocol ParticipantsStorageProtocol:")]
protocol=participants[participants.index("protocol ParticipantsStorageProtocol:"):participants.index("extension ParticipantsStorageProtocol {")]
actor=participants[participants.index("actor ParticipantsStorage:"):]
write("ParticipantsStorageProjection.swift","import Foundation\n\n"+regions+protocol+actor)
space=original("Anytype/Sources/ServiceLayer/SpaceStorage/SpaceViewsStorage.swift")
assert sha(space.encode())=="f1570f8cff28d87152ea455ded6bc0bdfeb729e0beb3a70e3a47fb06b4710a57"
space_packet=w/"docs/pinkha/torah-integration/production-space-authority-20261122/controls"
space_manifest=json.loads((space_packet/"INPUTS.json").read_bytes())
space_projection=(space_packet/"SpaceViewsStorageProjection.swift").read_bytes()
listed=space_manifest.get("swift_inputs",space_manifest.get("compiled_inputs",[]))
print(json.dumps({"space_manifest_keys":list(space_manifest),"space_projection_sha256":sha(space_projection),"space_projection_last_lines":space_projection.decode().splitlines()[-40:]}))
assert b"@main" not in space_projection and b"@Test" not in space_projection
(tests/"SpaceViewsStorageProjection.swift").write_bytes(space_projection)
space_view=original("Anytype/Sources/ServiceLayer/SpaceStorage/Models/SpaceView.swift")
original("Anytype/Sources/ServiceLayer/SubscriptionsToggler/Internals/SubscriptionStorage.swift")
original("Anytype/Sources/ServiceLayer/AccountParticipantsStorage/AcountParticipantSubscriptionBuilder.swift")
doc=json.loads("{\"name\":\"OriginalTypePermissionProbe.swift\",\"content\":\"import Foundation\\n\\n// Explicit disposable document model for exercising the actual production\\n// owner/lifetime code on a non-Apple host. This is not an editor or a backend.\\nenum DocumentMode: Equatable, Sendable {\\n    case handling\\n    case preview\\n    case version(String)\\n}\\n\\nstruct EditorPageObject: Sendable {\\n    let objectId: String\\n    let spaceId: String\\n    let mode: DocumentMode\\n}\\n\\n// Explicit minimal details values consumed by the unchanged original permission evaluator.\\n// These are portable value inputs, not a backend document or an editor implementation.\\nenum ObjectRestriction: Sendable { case typeChange, delete, duplicate, template, details, relations, blocks }\\nstruct Participant: Sendable { let canEdit: Bool }\\nstruct PermissionLayout: Sendable {\\n    let isFileOrMedia = false, isList = false, isParticipant = false, isChat = false\\n    let haveIcon = true, haveCover = false, isEditorLayout = false\\n}\\nstruct ObjectDetails: Sendable {\\n    let isArchived = false, isTemplate = false, isObjectType = true, canMakeTemplate = false\\n    let resolvedLayoutValue = PermissionLayout()\\n    let restrictionsValue: [ObjectRestriction]\\n}\\n\\nenum BlocksReadonlyReason: Equatable {\\n    case locked\\n    case archived\\n    case spaceIsReadonly\\n    case restrictions\\n}\\n\\nenum EditBlocksPermission: Equatable {\\n    case edit\\n    case readonly(BlocksReadonlyReason)\\n}\\n\\nextension EditBlocksPermission {\\n    var canEdit: Bool {\\n        switch self {\\n        case .edit:\\n            return true\\n        case .readonly:\\n            return false\\n        }\\n    }\\n}\\n\\nextension BlocksReadonlyReason: Sendable {}\\nextension EditBlocksPermission: Sendable {}\\n\\nstruct ObjectPermissions: Equatable {\\n    var canChangeType: Bool = false\\n    var canDelete: Bool = false\\n    var canRestore: Bool = false\\n    var canTemplateSetAsDefault: Bool = false\\n    var canArchive: Bool = false\\n    var canDuplicate: Bool = false\\n    var canUndoRedo: Bool = false\\n    var canMakeAsTemplate: Bool = false\\n    var canFavorite: Bool = false\\n    var canLinkItself: Bool = false\\n    var canLock: Bool = false\\n    var canChangeIcon: Bool = false\\n    var canChangeCover: Bool = false\\n    var canChangeLayout: Bool = false\\n    var canEditRelationValues: Bool = false\\n    var canEditPropertiesList: Bool = false\\n    var canApplyTemplates: Bool = false\\n    var canShare: Bool = false\\n    var canPublish: Bool = false\\n    var canEditBlocks: Bool = false\\n    var canEditMessages: Bool = false\\n    var canRestoreVersionHistory: Bool = false\\n    var canEditDetails: Bool = false\\n    var canShowRelations: Bool = false\\n    var canToggleDescription: Bool = false\\n    var canApplyUneditableActions: Bool = false\\n    var editBlocks: EditBlocksPermission = .readonly(.restrictions)\\n}\\n\\nextension ObjectPermissions {\\n    init(\\n        details: ObjectDetails,\\n        isLocked: Bool,\\n        participantCanEdit: Bool,\\n        isVersionMode: Bool,\\n        objectRestrictions: [ObjectRestriction]\\n    ) {\\n        let isArchive = details.isArchived\\n        let isTemplate = details.isTemplate\\n        let isObjectType = details.isObjectType\\n        \\n        let canEditRelations = !isLocked && !isArchive && participantCanEdit && !isVersionMode\\n        let canEdit = canEditRelations && !details.resolvedLayoutValue.isFileOrMedia\\n        \\n        let isChat = details.resolvedLayoutValue.isChat\\n        let specificTypes = !details.resolvedLayoutValue.isList && !details.resolvedLayoutValue.isParticipant && !isChat && !isObjectType\\n        \\n        self.canApplyUneditableActions = participantCanEdit && !isArchive\\n        self.canChangeType = !objectRestrictions.contains(.typeChange) && canEdit && !isTemplate\\n        self.canDelete = isArchive && participantCanEdit\\n        self.canRestore = canDelete\\n        self.canTemplateSetAsDefault = isTemplate && canEdit\\n        self.canArchive = !objectRestrictions.contains(.delete) && participantCanEdit\\n        self.canDuplicate = !objectRestrictions.contains(.duplicate) && canApplyUneditableActions && !isObjectType\\n        \\n        self.canUndoRedo = specificTypes && canEdit\\n        \\n        self.canMakeAsTemplate = details.canMakeTemplate\\n                                && !objectRestrictions.contains(.template)\\n                                && canApplyUneditableActions\\n\\n        self.canFavorite = canApplyUneditableActions && !isTemplate && !isObjectType\\n        self.canLinkItself = canApplyUneditableActions && !isTemplate && !isObjectType && !isChat\\n        self.canLock = specificTypes && canApplyUneditableActions && !isTemplate\\n        self.canChangeIcon = details.resolvedLayoutValue.haveIcon && canEdit\\n        self.canChangeCover = details.resolvedLayoutValue.haveCover && canEdit && !isObjectType\\n        self.canChangeLayout = details.resolvedLayoutValue.isEditorLayout && canEdit // && !objectRestrictions.contains(.layoutChange)\\n        self.canEditDetails = !objectRestrictions.contains(.details) && participantCanEdit\\n        self.canEditRelationValues = canEditRelations && canEditDetails\\n        self.canEditPropertiesList = canEditRelationValues && !objectRestrictions.contains(.relations)\\n        self.canShare = !isTemplate && !isObjectType\\n        self.canPublish = canShare && specificTypes && !isArchive\\n        self.canApplyTemplates = canEdit && !isTemplate\\n        self.canEditMessages = canEdit\\n        self.canShowRelations = !isObjectType\\n        \\n        if isLocked || isVersionMode {\\n            self.editBlocks = .readonly(.locked)\\n        } else if isArchive {\\n            self.editBlocks = .readonly(.archived)\\n        } else if !participantCanEdit {\\n            self.editBlocks = .readonly(.spaceIsReadonly)\\n        } else if objectRestrictions.contains(.blocks) {\\n            self.editBlocks = .readonly(.restrictions)\\n        } else {\\n            self.editBlocks = .edit\\n        }\\n        \\n        self.canEditBlocks = editBlocks.canEdit\\n        self.canRestoreVersionHistory = !isLocked && !isArchive && participantCanEdit\\n        self.canToggleDescription = !isChat\\n    }\\n}\\n\\nextension ObjectDetails {\\n    \\n    func permissions(participant: Participant?) -> ObjectPermissions {\\n        permissions(participantCanEdit: participant?.canEdit ?? false)\\n    }\\n    \\n    func permissions(participantCanEdit: Bool) -> ObjectPermissions {\\n        ObjectPermissions(\\n            details: self,\\n            isLocked: false,\\n            participantCanEdit: participantCanEdit, \\n            isVersionMode: false,\\n            objectRestrictions: restrictionsValue\\n        )\\n    }\\n}\\nextension ObjectPermissions: Sendable { }\\ntypealias PortablePermissions = ObjectPermissions\\n\\nprotocol BaseDocumentProtocol: AnyObject, Sendable {\\n    var objectId: String { get }\\n    var spaceId: String { get }\\n    var mode: DocumentMode { get }\\n    var isOpened: Bool { get }\\n    var isLocked: Bool { get }\\n    var permissions: PortablePermissions { get }\\n}\\n\\nfinal class PortableDocument: BaseDocumentProtocol, EditorDocumentWriteLifetimeProviding, Sendable {\\n    let objectId = \\\"owned\\\"\\n    let spaceId = \\\"owned-space\\\"\\n    let mode = DocumentMode.handling\\n    let isOpened = true\\n    let isLocked = false\\n    let permissions = PortablePermissions()\\n    let editorWriteLifetime = EditorDocumentWriteLifetime()\\n}\\n\",\"sha256\":\"0708d577f19f0c382cec913b990e949716c543536c4166575ed60e96f5c33f6a\"}")
assert sha(doc["content"].encode())==doc["sha256"]
assert doc["content"].count("struct Participant: Sendable { let canEdit: Bool }")==1
document=doc["content"].replace("struct Participant: Sendable { let canEdit: Bool }\n","")
document=document[:document.index("final class PortableDocument:")]
document+="""
final class CompositionDocument: BaseDocumentProtocol, EditorDocumentWriteLifetimeProviding, Sendable {
    let objectId: String
    let spaceId: String
    let mode = DocumentMode.handling
    let isOpened = true
    let isLocked = false
    let permissions = ObjectDetails(restrictionsValue: []).permissions(participantCanEdit: true)
    let editorWriteLifetime = EditorDocumentWriteLifetime()
    init(objectId: String = "native-target", spaceId: String = "space-A") {
        self.objectId = objectId
        self.spaceId = spaceId
    }
}
"""
write("DocumentDependencyProbe.swift",document)
prepared=json.loads("{\"name\":\"PreparedEditorPageDocument.swift\",\"content\":\"import Foundation\\n\\nenum PreparedEditorPageDocumentError: Error, Equatable {\\n    case emptyIdentity\\n    case objectMismatch\\n    case spaceMismatch\\n    case modeMismatch\\n    case documentNotOpened\\n}\\n\\n@MainActor\\nenum PreparedEditorPageDocument {\\n    static func validate(data: EditorPageObject, document: any BaseDocumentProtocol) throws {\\n        guard !data.objectId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,\\n              !data.spaceId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {\\n            throw PreparedEditorPageDocumentError.emptyIdentity\\n        }\\n        guard data.objectId == document.objectId else {\\n            throw PreparedEditorPageDocumentError.objectMismatch\\n        }\\n        guard data.spaceId == document.spaceId else {\\n            throw PreparedEditorPageDocumentError.spaceMismatch\\n        }\\n        guard data.mode == document.mode else {\\n            throw PreparedEditorPageDocumentError.modeMismatch\\n        }\\n        guard document.isOpened else {\\n            throw PreparedEditorPageDocumentError.documentNotOpened\\n        }\\n    }\\n}\\n\",\"sha256\":\"42e595c324e46947d4b964070994a193478d57072931b92be1451f155e2cb32e\"}")
assert sha(prepared["content"].encode())==prepared["sha256"]
write("PreparedEditorPageDocument.swift",prepared["content"])
(out/"Package.swift").write_bytes(b'''// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "OriginalSpaceEditComposition",
    targets: [.testTarget(name: "CompositionControls")],
    swiftLanguageModes: [.v5]
)
''')
record={"schema":1,"base":head,"candidate_sha256":sha(owner),"owner_base_sha256":sha(owner_base.encode()),"original_source_inputs":records,"space_projection_sha256":sha(space_projection),"space_projection_input_manifest_sha256":sha((space_packet/"INPUTS.json").read_bytes()),"document_dependency_probe_source_sha256":doc["sha256"],"prepared_document_sha256":prepared["sha256"],"participant_actor_sha256":sha(actor.encode()),"scope":"Source projection preparation only. Full original Owner/Lifetime/Operation/Binding and actors; explicit decoded values/DI/Combine/native subscription probes still to be written. No old tests copied or executed."}
(out/"SOURCE_PREPARATION.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"out":str(out),"source_record_sha256":sha((out/"SOURCE_PREPARATION.json").read_bytes()),"source_count":len(records),"swift_files":[{"name":p.name,"sha256":sha(p.read_bytes())} for p in sorted(tests.glob("*.swift"))],"participant_protocol":protocol,"space_actor_declarations":[line for line in space.splitlines() if any(key in line for key in ["protocol SpaceViews","extension SpaceViews","actor SpaceViews","func current","func spaceInfo","func set","func start","func stop"])]}))
