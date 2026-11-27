import Foundation
import PinkhaKit
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// A display projection is intentionally a different type from a native row.
/// Optimistic values cannot masquerade as an authoritative _ver/CAS snapshot.
public struct AnyHierarchyPresentationItem: Identifiable, Sendable, Equatable {
    public var id: String { native.objectID }
    public let native: AnyHierarchyItem
    public let title: String
    public let parentID: String?
    public let position: String
    public let isPending: Bool
    public var objectID: String { native.objectID }
    public var typeID: String { native.typeID }
    public var kind: PinkhaHierarchyNodeKind { native.kind }
}

/// Feed replacement is a read barrier, not a guessed ordering of opaque native
/// hashes. A fresh subscription is opened only after a confirmed mutation.
public struct AnyHierarchyPresentationState: Sendable {
    public let workspace: AnyTorahWorkspace
    public private(set) var feed = UUID()
    public private(set) var snapshot: AnyHierarchySnapshot?
    private var names: [String: String] = [:]
    private var placements: [String: AnyHierarchyPlacementPlan] = [:]
    private var retained: [String: AnyHierarchyItem] = [:]
    private var settlementSourceFeeds: [String: UUID] = [:]

    public init(workspace: AnyTorahWorkspace) { self.workspace = workspace }

    @discardableResult
    public mutating func beginFeed() -> UUID { feed = UUID(); return feed }
    public func isCurrent(_ value: UUID) -> Bool { value == feed }

    @discardableResult
    public mutating func receive(_ value: AnyHierarchySnapshot, feed token: UUID) throws -> Bool {
        guard token == feed else { return false }
        guard value.workspace == workspace else { throw AnyEngineError.invalidIdentity("hierarchy presentation workspace") }
        if let snapshot, value.schema != snapshot.schema { throw AnyHierarchyError.incompatibleSchema }
        snapshot = value
        for (id, sourceFeed) in settlementSourceFeeds where sourceFeed != token { finish(id) }
        return true
    }

    public var items: [AnyHierarchyPresentationItem] {
        var byID = snapshot?.itemsByID ?? [:]
        for (id, item) in retained where byID[id] == nil { byID[id] = item }
        return byID.values.map { item in
            let placement = placements[item.objectID]
            return AnyHierarchyPresentationItem(native: item,
                title: names[item.objectID] ?? item.title,
                parentID: placement.map(\.parentID) ?? item.parentID,
                position: placement?.position ?? item.position,
                isPending: names[item.objectID] != nil || placement != nil)
        }.sorted { $0.position == $1.position ? $0.id < $1.id : $0.position < $1.position }
    }

    public var itemsByID: [String: AnyHierarchyPresentationItem] {
        Dictionary(uniqueKeysWithValues: items.map { ($0.id, $0) })
    }
    public func children(of parentID: String?) -> [AnyHierarchyPresentationItem] {
        items.filter { $0.parentID == parentID }
    }
    public func hasPending(_ objectID: String) -> Bool { names[objectID] != nil || placements[objectID] != nil }

    public mutating func rename(objectID: String, title: String) throws {
        guard let item = snapshot?.itemsByID[objectID] else {
            throw PinkhaHierarchyError.nodeNotFound(objectId: objectID)
        }
        retained[objectID] = item; names[objectID] = title
    }

    public mutating func place(_ plan: AnyHierarchyPlacementPlan) throws {
        guard plan.workspace == workspace, plan.schema == snapshot?.schema else {
            throw AnyHierarchyError.incompatibleSchema
        }
        guard let item = snapshot?.itemsByID[plan.objectID] else {
            throw PinkhaHierarchyError.nodeNotFound(objectId: plan.objectID)
        }
        retained[plan.objectID] = item; placements[plan.objectID] = plan
    }

    /// Once dispatch has resolved (success or uncertainty), only a replacement
    /// feed may settle its display overlay. A buffered old frame is insufficient.
    public mutating func settleAfterFeedReplacement(_ objectID: String) {
        if hasPending(objectID) { settlementSourceFeeds[objectID] = feed }
    }

    public mutating func finish(_ objectID: String) {
        settlementSourceFeeds.removeValue(forKey: objectID)
        retained.removeValue(forKey: objectID)
        names.removeValue(forKey: objectID); placements.removeValue(forKey: objectID)
    }

    public mutating func reset() {
        _ = beginFeed(); snapshot = nil; retained = [:]; names = [:]; placements = [:]; settlementSourceFeeds = [:]
    }
}
