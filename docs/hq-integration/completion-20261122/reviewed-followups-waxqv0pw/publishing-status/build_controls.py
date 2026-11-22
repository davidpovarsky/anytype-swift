from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib, json, re

root=Path(__file__).resolve().parent
out=root/'validation/portable-inputs'
out.mkdir(parents=True,exist_ok=True)
inputs=[]

def sha(data): return hashlib.sha256(data).hexdigest()
def add(name, data, source, canonical=None, transform='none'):
    if isinstance(data,str): data=data.encode()
    (out/name).write_bytes(data)
    inputs.append({'name':name,'source':source,'canonical_sha256':sha(canonical or data),
                   'staged_sha256':sha(data),'bytes':len(data),'transform':transform})

pin=root.parent/'anytype_channel_pin_role_qualification'
old_manifest=json.loads((pin/'validation/INPUTS.json').read_text())
with ZipFile(pin/'validation/role-controls-r1.zip') as z:
    for name in ['Lifetime.swift','Operation.swift','Binding.swift','Owner.swift',
                 'OriginalTypePermissionProbe.swift','PreparedEditorPageDocument.swift']:
        data=z.read(name)
        original=next(x for x in old_manifest['files'] if x['name']==name)
        assert sha(data)==original['staged_sha256']
        (out/name).write_bytes(data)
        inputs.append({**original,'bytes':len(data),'reused_without_old_test_execution':True})

participants=(pin/'source/Anytype/Sources/ServiceLayer/ParticipantStorage/ParticipantsStorage.swift').read_bytes()
a=participants.index(b'// ORIGINAL_CHANNEL_PIN_PERMISSION_BEGIN')
b=participants.index(b'// ORIGINAL_CHANNEL_PIN_PERMISSION_END',a)+len(b'// ORIGINAL_CHANNEL_PIN_PERMISSION_END')
add('RoleSource.swift',b'import Foundation\n'+participants[a:b]+b'\n',
    'unchanged exact production passive role region required by current Owner',canonical=participants,
    transform='extract exact marked region; only Foundation import added; no role tests rerun')

generated=root/'reference/anytype/Modules/ProtobufMessages/Sources/Protocol/Commands'
for name in ['Anytype_Rpc.swift','Anytype_Rpc.Publishing.swift','Anytype_Rpc.Publishing.GetStatus.swift',
             'Anytype_Rpc.Publishing.PublishState.swift','Anytype_Rpc.Publishing.PublishStatus.swift',
             'Anytype_Rpc.Publishing.Remove.swift']:
    add(name,(generated/name).read_bytes(),str((generated/name).relative_to(root)))

source=(root/'source/Modules/ProtobufMessages/Sources/Invocation.swift').read_text()
start=source.index('// ORIGINAL_PUBLISHING_STATUS_ABSENCE_BEGIN')
end=source.index('public struct Invocation<Request, Response>',start)
classifier_and_policy=source[start:end]
start=source.index('            result = try await withCheckedThrowingContinuation')
end=source.index('\n        } catch {\n            log(message:',start)
gcd=source[start:end]
start=source.index('        if !result.error.isNull {')
end=source.index('\n        \n        if result.hasEvent {',start)
policy=source[start:end]
adoption=(root/'reference/anytype/Modules/ProtobufMessages/Sources/Generated/CommandsInvocation/invocation-adoption.generated.swift').read_text()
getter='    public var isNull: Bool { code == .null && description_p.isEmpty }'
for name in ['GetStatus','Remove']:
    expected='extension Anytype_Rpc.Publishing.'+name+'.Response.Error: ResponseError {\n'+getter+'\n}'
    assert expected in adoption
assert 'extension Anytype_Rpc.Publishing.GetStatus.Response: ResultWithError {}' in adoption
assert 'hasEvent' not in (generated/'Anytype_Rpc.Publishing.GetStatus.swift').read_text()
protocols=(root/'reference/anytype/Modules/ProtobufMessages/Sources/ResponceProtocols.swift').read_text()
assert 'public var hasEvent: Bool { false }' in protocols

support='''import Foundation
import SwiftProtobuf

// Explicit protocol adaptation only for the extracted native-result controls.
// All request/response values are the actual unmodified generated messages.
private protocol ProbeNativeError: Swift.Error { var isNull: Bool { get } }
private protocol ProbeNativeResponse: SwiftProtobuf.Message, Sendable {
    associatedtype Error: ProbeNativeError
    var error: Error { get }
}
'''
for name in ['GetStatus','Remove']:
    support+='extension Anytype_Rpc.Publishing.'+name+'.Response.Error: ProbeNativeError {\n'+getter+'\n}\n'
    support+='extension Anytype_Rpc.Publishing.'+name+'.Response: ProbeNativeResponse {}\n'
support+='\n'+classifier_and_policy+'''
// The native admission/body-completion and result-policy blocks below are
// byte-for-byte excerpts from production Invocation.swift, wrapped only with
// explicit request/effect inputs. Logging, event dispatch, cancellation helper
// and the public cross-module Services wrapper are not executed by this probe.
private func invokeOriginalAdmissionProbe<Request: SwiftProtobuf.Message & Sendable, Response: ProbeNativeResponse>(
    messageName: String, request: Request, responsePolicy: InvocationResponsePolicy,
    invokeTask: @escaping @Sendable (Request) throws -> Response
) async throws -> Response {
    let qos = DispatchQoS.QoSClass.default
    let dispatchPermit = try await InvocationDispatchContext.binding?.prepare(messageName: messageName)
    let result: Response
    do {
'''+gcd+'''
    } catch { throw error }
'''+policy+'''
    return result
}

'''+(root/'PublishingStatusControls.swift').read_text()
add('PublishingControls.swift',support,'exact production classifier/native-result blocks plus 14 new controls',
    canonical=source.encode(),transform='exact marked classifier/policy/GCD blocks; actual generated error getter; explicit isolated protocol/document/effect inputs')
inputs[-1]['regions']={
    'classifier_and_policy_sha256':sha(classifier_and_policy.encode()),
    'gcd_body_sha256':sha(gcd.encode()),'result_policy_sha256':sha(policy.encode()),
    'control_sha256':sha((root/'PublishingStatusControls.swift').read_bytes())}
report={'expected_controls':14,'compiler_jobs':1,'dependency_builds':0,
        'scope':'Actual generated GetStatus/Remove/PublishState and cached pinned SwiftProtobuf. Exact new production classifier, existing native-result admission block and new result-policy block, unchanged Owner/lifetime/operation/dispatch. Explicit document/effect inputs; no Lib, network, UIKit or full Invocation logging/cancellation/event execution.',
        'source_patch':json.loads((root/'SOURCE_MANIFEST.json').read_text())['combined_patch'],
        'get_status_has_event':{'generated_response':'No event field or override',
            'adoption':'extension Anytype_Rpc.Publishing.GetStatus.Response: ResultWithError {}',
            'original_default':'public var hasEvent: Bool { false }'},
        'files':inputs,'prior_suites_rerun':False,'native':'NOT_RUN','apple_typecheck':'NOT_RUN'}
(out/'INPUTS.json').write_text(json.dumps(report,indent=2)+'\n')
(root/'validation/CONTROL_INPUTS.json').write_text(json.dumps(report,indent=2)+'\n')
archive=root/'validation/publishing-controls-r2.zip'
with ZipFile(archive,'w',compression=ZIP_DEFLATED) as z:
    for p in sorted(out.iterdir()): z.writestr(p.name,p.read_bytes())
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes()),
                  'files':len(inputs),'expected_controls':14,'owner_sha256':next(x['canonical_sha256'] for x in inputs if x['name']=='Owner.swift')}))
