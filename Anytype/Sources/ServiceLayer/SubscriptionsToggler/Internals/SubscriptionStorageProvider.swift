import Foundation
import Services
import Combine
import AnytypeCore
import ProtobufMessages

protocol SubscriptionStorageProviderProtocol: AnyObject, Sendable {
    func createSubscriptionStorage(subId: String) -> any SubscriptionStorageProtocol
}

final class SubscriptionStorageProvider: SubscriptionStorageProviderProtocol, @unchecked Sendable {
    
    // MARK: - Private properties
    
    private let toggler: any SubscriptionTogglerProtocol = Container.shared.subscriptionToggler()
    
    private let lock = NSLock()
    // NSMapTable<NSString, SubscriptionStorage>.strongToWeakObjects() crashed on objc_loadWeakRetained method for iphone se 1 gen ios 15
    private var subscriptionCache = [String: Weak<SubscriptionStorage>]()
    
    // MARK: - Public properties
    
    func createSubscriptionStorage(subId: String) -> any SubscriptionStorageProtocol {
        
        lock.lock()
        defer { lock.unlock() }
        
        if let storage = subscriptionCache[subId]?.value {
            anytypeAssertionFailure("Subscription storage already created", info: ["sub id": subId])
            return storage
        }
        
        let storage = SubscriptionStorage(subId: subId, detailsStorage: ObjectDetailsStorage(), toggler: toggler)
        subscriptionCache[subId] = Weak(value: storage)
        return storage
    }

    /// A prepared History reader owns a fresh subscription ID. Its original
    /// cleanup retains the captured account, not a later matching account.
    func createOriginalAccountBoundStorage(
        subId: String, accountDispatch: InvocationDispatchBinding
    ) throws -> SubscriptionStorage {
        let originalToggler = try SubscriptionToggler.requireOriginal(toggler)
        lock.lock()
        defer { lock.unlock() }
        guard !subId.isEmpty, subscriptionCache[subId]?.value == nil else {
            throw EditorDocumentWriteError.rejected(.invalidLease)
        }
        let storage = SubscriptionStorage(
            subId: subId, detailsStorage: ObjectDetailsStorage(), toggler: originalToggler,
            originalAccountDispatch: accountDispatch
        )
        subscriptionCache[subId] = Weak(value: storage)
        return storage
    }
}
