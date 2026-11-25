import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Binds derived fields to the exact signed creation in native history. The
/// author timestamp is native operation data, never a trusted wall clock or a
/// claim that an imported source fact was authored by the destination account.
struct AnyDestinationImmutableRecordAuthority: Sendable {
    let intentID: String
    let specSHA256: String
    let recordID: String
    let changeID: String
    let author: String
    let timestampSeconds: Int64
    let timestampMilliseconds: Int64
    let recordAtChange: AnyJSON

    init(change: AnyJSON, snapshot: AnyJSON, intent: AnyPreparedImmutableRecordIntent,
         recordID: String, expectedChangeID: String) throws {
        let native = try AnyNativeHistoryChange(native: change)
        let (milliseconds, overflow) = native.timestamp.multipliedReportingOverflow(by: 1000)
        func same(_ actual: String?, _ expected: String) -> Bool {
            actual.map { Data($0.utf8) } == Data(expected.utf8)
        }
        guard !overflow, !native.truncated,
              same(native.version, expectedChangeID),
              same(native.author, intent.binding.workspace.accountID),
              same(native.dataset, intent.schema.dataset),
              let touched = native.native["touched"]?.array, touched.count == 1,
              same(touched[0]["dataset"]?.string, intent.schema.dataset),
              same(touched[0]["recordId"]?.string, recordID),
              same(snapshot["version"]?.string, expectedChangeID),
              same(snapshot["dataset"]?.string, intent.schema.dataset),
              same(snapshot["recordId"]?.string, recordID),
              snapshot["exists"]?.bool == true,
              snapshot["deleted"] == nil || snapshot["deleted"]?.bool == false,
              let record = snapshot["record"], record.object != nil,
              same(record["id"]?.string, recordID) else {
            throw AnyDestinationContentVerificationError.mismatch(
                sourceKey: intent.sourceKey, field: "exact signed immutable record history")
        }
        self.intentID = intent.intentID
        self.specSHA256 = intent.specSHA256
        self.recordID = recordID
        self.changeID = expectedChangeID
        self.author = native.author
        self.timestampSeconds = native.timestamp
        self.timestampMilliseconds = milliseconds
        self.recordAtChange = record
    }
}
