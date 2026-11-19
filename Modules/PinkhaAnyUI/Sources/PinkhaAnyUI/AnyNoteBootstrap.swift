
import Foundation
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration

public enum AnyNoteBootstrap {
    public static let bundleID = "pinkha/note/v1"

    /// Explicit schema installation. Ordinary Notes remain deletable page objects;
    /// only this shared marker declaration uses the engine's derived bundle root.
    public static func install(client: AnyHTTPClient, session: AnyApplicationSession) async throws -> AnyNativeNoteMarker {
        guard client.expectedAccountID == session.workspace.accountID else { throw AnyHostError.wrongWorkspace }
        return try await session.perform { lease in
            _ = try await client.requestJSON(method: "POST",
                path: ["v1", "spaces", lease.workspace.spaceID, "bundles"],
                body: .object(["id": .string(bundleID), "name": .string("Pinkha Notes"),
                               "derived": .bool(true), "hidden": .bool(true),
                               "collection": .bool(true), "xKey": .string(AnyNativeNoteMarker.xKey)]),
                authorize: {
                    try await lease.validate()
                    let member = try await client.requestJSON(method: "GET",
                        path: ["v1", "spaces", lease.workspace.spaceID, "members", "me"])
                    try AnyHTTPTorahTargetAccess.validateMember(member, workspace: lease.workspace, intent: .write)
                })
            let value = try await readMarker(client: client, workspace: lease.workspace)
            try await lease.validate()
            return value
        }
    }

    /// Opening a Note reader does not create or repair schema.
    public static func read(client: AnyHTTPClient, session: AnyApplicationSession) async throws -> AnyNativeNoteMarker {
        guard client.expectedAccountID == session.workspace.accountID else { throw AnyHostError.wrongWorkspace }
        return try await session.perform { lease in
            let value = try await readMarker(client: client, workspace: lease.workspace)
            try await lease.validate()
            return value
        }
    }

    private static func readMarker(client: AnyHTTPClient, workspace: AnyTorahWorkspace) async throws -> AnyNativeNoteMarker {
        let value = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", workspace.spaceID, "bundles", bundleID])
        guard let bundle = value["bundle"], bundle["id"]?.string == bundleID,
              bundle["derived"]?.bool == true,
              bundle["losers"] == nil || bundle["losers"]?.array == [],
              let root = bundle["rootId"]?.string, !root.isEmpty else {
            throw AnyUIActivationError.incompatibleSchema
        }
        return try await AnyNativeNoteMarker.verify(client: client, workspace: workspace, collectionID: root)
    }
}
