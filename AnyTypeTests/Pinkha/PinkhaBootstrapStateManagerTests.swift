import PinkhaKit
import Testing
@testable import Anytype

@Suite("Pinkha bootstrap single-flight")
struct PinkhaBootstrapStateManagerTests {
    @Test("Only one concurrent caller can claim provisioning for a Space")
    func onlyOneProvisioningOwner() async {
        let manager = PinkhaBootstrapStateManager()
        let claims = await withTaskGroup(of: Bool.self, returning: [Bool].self) { group in
            for _ in 0..<64 {
                group.addTask {
                    manager.beginProvisioningIfNeeded(spaceId: "pinkha-acceptance-space")
                }
            }

            var values: [Bool] = []
            for await value in group {
                values.append(value)
            }
            return values
        }

        #expect(claims.filter { $0 }.count == 1)
        guard case .provisioning = manager.state(for: "pinkha-acceptance-space") else {
            Issue.record("The winning claim must publish provisioning before returning")
            return
        }
    }
}
