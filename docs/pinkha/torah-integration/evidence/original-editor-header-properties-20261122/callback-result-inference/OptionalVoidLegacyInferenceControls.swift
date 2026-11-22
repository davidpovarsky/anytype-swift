import Foundation
enum Failure: Error { case wrongDocument }
struct Owner {
    let rejects: Bool
    func validateDocument(_ document: Int) throws {
        if rejects { throw Failure.wrongDocument }
    }
}
struct Session { let owner: Owner }
struct LegacyGenericInference {
    let preparedSession: Session?
    let document = 7
    // Exact legacy branch of the original generic helper: no external scope.
    func withCurrentSource<Value>(_ operation: () throws -> Value) throws -> Value {
        return try operation()
    }
    func original() -> Bool {
        guard (try? withCurrentSource {
            try preparedSession?.owner.validateDocument(document)
        }) != nil else { return false }
        return true
    }
    func explicitVoid() -> Bool {
        guard (try? withCurrentSource { () -> Void in
            try preparedSession?.owner.validateDocument(document)
        }) != nil else { return false }
        return true
    }
}
@main struct Controls {
    static func main() {
        let legacy = LegacyGenericInference(preparedSession: nil)
        let admitted = LegacyGenericInference(preparedSession: Session(owner: Owner(rejects: false)))
        let rejected = LegacyGenericInference(preparedSession: Session(owner: Owner(rejects: true)))
        precondition(legacy.original() == false)
        precondition(legacy.explicitVoid() == true)
        precondition(admitted.original() == true)
        precondition(admitted.explicitVoid() == true)
        precondition(rejected.original() == false)
        precondition(rejected.explicitVoid() == false)
        print("PASS six extracted optional-Void inference observations: original nil-session false; fixed nil-session true; admitted and thrown-error behavior retained. No original Owner, Apple module or Native UI executed.")
    }
}
