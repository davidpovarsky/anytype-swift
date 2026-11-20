"""Mechanically host the original PropertyProbe15 in a real iOS AnyLib XCTest."""
from pathlib import Path
import hashlib,json,re,textwrap

APP=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
PROBE=APP/'Modules/PinkhaAnyHost/Sources/PinkhaAnyHostProbe'
DEST=APP/'Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativePropertyWorkflowTests.swift'
OUT=APP/'build/any-engine-port/native-property-hosted-source-v1'

def sha(data):return hashlib.sha256(data).hexdigest()
sources={name:(PROBE/name).read_bytes() for name in ('PropertyProbe.swift','CreationProbe.swift','Probe.swift')}
texts={name:data.decode('utf-8').replace('\r\n','\n') for name,data in sources.items()}
property_source=texts['PropertyProbe.swift']
creation_source=texts['CreationProbe.swift']
cli_source=texts['Probe.swift']
original_property=property_source[property_source.index('struct PropertyProbeFixture:'):]
original_helpers=creation_source[creation_source.index('func creationProbeMutationID()'):]
original_error=cli_source[cli_source.index('enum ProbeError:'):cli_source.index('@main')].rstrip()+'\n'
checks=re.findall(r'checks\.append\("([^"\n]+)"\)',original_property)
assert len(checks)==15 and len(set(checks))==15

# These mechanical changes alter linkage/isolation/output plumbing only.
# Every assertion, mutation, native read, fence and cleanup statement remains.
property_replacements=[
 ('func runNativePropertyProbe(client:', 'nonisolated static func runNativePropertyProbe(client:'),
 ('owner: AnyApplicationSession, fixture: PropertyProbeFixture) async throws {',
  'owner: AnyApplicationSession, fixture: PropertyProbeFixture) async throws -> [String] {'),
 ('private func propertyProbeVerified(', 'private nonisolated static func propertyProbeVerified('),
]
adapted_property=original_property
for before,after in property_replacements:
    assert adapted_property.count(before)==1
    adapted_property=adapted_property.replace(before,after,1)
output_start=adapted_property.index('        let result: AnyJSON = .object([')
output_end=adapted_property.index('\n    } catch {',output_start)
original_output=adapted_property[output_start:output_end]
assert original_output.count('print(')==1 and 'checks.map(AnyJSON.string)' in original_output
adapted_property=adapted_property[:output_start]+'        return checks'+adapted_property[output_end:]
recovered_property=adapted_property.replace('        return checks\n    } catch {',original_output+'\n    } catch {',1)
for before,after in reversed(property_replacements):recovered_property=recovered_property.replace(after,before,1)
assert recovered_property==original_property
adapted_helpers=original_helpers.replace('func creationProbeMutationID()', 'nonisolated static func creationProbeMutationID()',1)
assert adapted_helpers.replace('nonisolated static func creationProbeMutationID()', 'func creationProbeMutationID()',1)==original_helpers
adapted_error=original_error.replace('func require(', 'nonisolated static func require(',1)
assert adapted_error.replace('nonisolated static func require(', 'func require(',1)==original_error

scaffold='''#if os(iOS)
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaAnyRuntime
import PinkhaAnyNative

/// Actual iOS AnyLib, normal application authentication and a fresh owned Space.
/// The private workflow below is mechanically extracted from PropertyProbe.swift:
/// its fifteen ordered business checks, native calls and strict receipts remain.
/// Its creation journal is the original in-memory metadata fixture; protected
/// persistence and UIKit gestures have their own acceptance tests.
@MainActor
final class NativePropertyWorkflowTests: XCTestCase {
    func testOriginalFifteenPropertyAssertionsOnRealNativeLibrary() async throws {
        XCTAssertEqual(AnyEmbeddedBuild.linked, .pinkhaNativeV1,
                       "This acceptance must link the source-verified patched Any library.")
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("native-property-proof-" + UUID().uuidString, isDirectory: true)
        let credentialService = "io.pinkha.property.native.tests." + UUID().uuidString
        let application = try AnyNativeApplication(dataDirectory: directory, credentialService: credentialService)
        var accountID: String?
        var ownedSpaceID: String?
        do {
            try await application.start(network: .official)
            let account = try await application.createAccount()
            accountID = account.id
            try await application.acknowledgeRecoveryBackup(accountID: account.id)
            let spaceID = try await application.createSpace(name: "Disposable iOS native property acceptance")
            ownedSpaceID = spaceID
            let owner = try await application.connectSpace(id: spaceID)
            let fixture = try await makeFixture(owner: owner)
            let completed = try await NativePropertyWorkflowProbe.runNativePropertyProbe(
                client: owner.client, workspace: owner.workspace, owner: owner.session, fixture: fixture)
            XCTAssertEqual(completed, Self.expectedChecks,
                           "Every original property assertion must complete in the original order.")
            try await application.deleteSpace(id: spaceID)
            ownedSpaceID = nil
            try await application.signOut()
            try await application.removeSavedAccount(id: account.id)
            await application.stop()
            try await AnyProtectedCreationJournal.removeAccountData(accountID: account.id)
            try FileManager.default.removeItem(at: directory)
        } catch {
            if let ownedSpaceID { try? await application.deleteSpace(id: ownedSpaceID) }
            await application.stop()
            if let accountID {
                try? AnyNativeCredentialVault(service: credentialService).remove(accountID: accountID)
                try? await AnyProtectedCreationJournal.removeAccountData(accountID: accountID)
            }
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }

    /// Same real Type/Collection requests as the executed native Property15
    /// fixture builder. IDs are returned by native APIs, never invented here.
    private func makeFixture(owner: AnyNativeWorkspaceOwner) async throws -> NativePropertyWorkflowProbe.PropertyProbeFixture {
        let client = owner.client
        let spacePath = ["v1", "spaces", owner.workspace.spaceID]
        let nonce = UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
        return try await owner.session.perform { lease in
            let type = try await client.requestJSON(method: "POST", path: spacePath + ["types"],
                body: .object(["name": .string("Native property canonical document"),
                               "xKey": .string("native_prop_type_" + nonce)]),
                authorize: { try await lease.validate() })
            let typeID = try type.requireString("typeId")
            _ = try await client.requestJSON(method: "POST", path: spacePath + ["types", typeID, "parts"],
                body: .object(["key": .string("body"),
                               "datasets": .array([.object(["module": .string("editor")])])]),
                authorize: { try await lease.validate() })
            let policy = try await client.requestJSON(method: "GET",
                path: spacePath + ["pinkha", "document-types", typeID],
                authorize: { try await lease.validate() })
            try NativePropertyWorkflowProbe.require(policy["eligible"] == .bool(true) &&
                policy["canonicalEditorDataset"] == .string("editor_blocks"),
                "actual custom Type does not declare a canonical editor")
            let collection = try await client.requestJSON(method: "POST", path: spacePath + ["collections"],
                body: .object(["name": .string("Native property preserved values"),
                               "xKey": .string("native_prop_values_" + nonce)]),
                authorize: { try await lease.validate() })
            let collectionID = try collection.requireString("collectionId")
            let text = try await client.requestJSON(method: "POST",
                path: spacePath + ["collections", collectionID, "properties"],
                body: .object(["name": .string("Text value"), "xKey": .string("text_value"),
                               "kind": .string("string"), "scope": .string("synced")]),
                authorize: { try await lease.validate() })
            let number = try await client.requestJSON(method: "POST",
                path: spacePath + ["collections", collectionID, "properties"],
                body: .object(["name": .string("Number value"), "xKey": .string("number_value"),
                               "kind": .string("number"), "scope": .string("synced")]),
                authorize: { try await lease.validate() })
            return try NativePropertyWorkflowProbe.PropertyProbeFixture(arguments: [
                "--custom-type-id", typeID, "--collection-id", collectionID,
                "--text-property-id", text.requireString("propId"),
                "--number-property-id", number.requireString("propId")])
        }
    }

    private static let expectedChecks: [String] = [
__EXPECTED_CHECKS__
    ]
}

// Test-only namespace. There is no executable @main, transport override,
// production API hook, mock HTTP response, or alternate acknowledgment rule.
private enum NativePropertyWorkflowProbe {
__EXTRACTED_WORKFLOW__
}
#endif
'''
scaffold=scaffold.replace('__EXPECTED_CHECKS__',',\n'.join('        '+json.dumps(c) for c in checks))
namespace='\n'.join((adapted_error,adapted_property,adapted_helpers))
generated=scaffold.replace('__EXTRACTED_WORKFLOW__',textwrap.indent(namespace,'    ').rstrip())
assert re.findall(r'checks\.append\("([^"\n]+)"\)',generated)==checks
assert '@main\nenum' not in generated
assert 'URLSession' not in generated and '@testable' not in generated
assert not DEST.exists() and not OUT.exists()
DEST.parent.mkdir(parents=True,exist_ok=True)
DEST.write_text(generated,encoding='utf-8',newline='\n')
OUT.mkdir(parents=True)
proof={'status':'SOURCE_READY_NOT_APPLE_EXECUTED','testClass':'NativePropertyWorkflowTests',
 'testMethod':'testOriginalFifteenPropertyAssertionsOnRealNativeLibrary','checkCount':15,'orderedOriginalChecks':checks,
 'testPath':str(DEST.relative_to(APP)).replace('\\','/'),'testSHA256':sha(DEST.read_bytes()),
 'sourceInputs':{str((PROBE/name).relative_to(APP)).replace('\\','/'):{'sha256':sha(data),'normalizedLFSourceSHA256':sha(texts[name].encode())} for name,data in sources.items()},
 'mechanicalComparisons':{'propertyFixtureAndWorkflowRecoveredByteExactlyAfterAllowedTransforms':recovered_property==original_property,
 'creationJournalAndIDHelpersRecoveredByteExactlyAfterAllowedTransforms':adapted_helpers.replace('nonisolated static func creationProbeMutationID()', 'func creationProbeMutationID()',1)==original_helpers,
 'requireAndErrorHelpersRecoveredByteExactlyAfterAllowedTransforms':adapted_error.replace('nonisolated static func require(', 'func require(',1)==original_error,
 'all15CheckAppendExpressionsInOriginalOrder':True},
 'allowedTransforms':['Test-only namespace indentation','Nonisolated static linkage for namespace helper functions','Workflow return type becomes [String]','Replace final CLI JSON printing with returning the same completed checks'],
 'unchangedBusinessSpanSHA256':sha(original_property[:original_property.index('        let result: AnyJSON = .object([')].encode()),
 'nativeFixture':'Normal AnyNativeApplication official-network account creation/recovery acknowledgment/Space connect; authenticated client/session; actual custom canonical editor Type and synced string/number Collection; own Space/account cleanup',
 'creationJournalScope':'Original metadata-only in-memory journal retained; protected persistence is a separate acceptance',
 'noCLIEntryPoint':True,'noProductionAPITestHooks':True,'noTransportChanges':True,'noHTTPMocks':True,
 'appleSemanticCompileAndRuntime':'PENDING','generatorSHA256':sha(Path(__file__).read_bytes())}
(OUT/'source-proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
(OUT/'original-property-output.txt').write_text(original_output,encoding='utf-8',newline='\n')
(OUT/'executed-generator.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'status':proof['status'],'testPath':str(DEST),'testSHA256':proof['testSHA256'],'checkCount':15,'sourceProofPath':str(OUT/'source-proof.json'),'sourceProofSHA256':sha((OUT/'source-proof.json').read_bytes()),'mechanicalComparisons':proof['mechanicalComparisons']}))
