import Foundation

public typealias ObjectId = String

final class AtomicBox<T>: @unchecked Sendable {
    private let lock = NSLock()
    private var stored: T
    init(_ value: T) { stored = value }
    var value: T {
        get { lock.withLock { stored } }
        set { lock.withLock { stored = newValue } }
    }
    func access<R>(_ body: (inout T) -> R) -> R { lock.withLock { body(&stored) } }
}

enum InitializationProbeFailure: Error { case timeout, missingURL }

final class ServiceProbe: UnsplashServiceProtocol, @unchecked Sendable {
    let queries = AtomicBox<[String]>([])
    func searchUnsplashImages(query: String) async throws -> [UnsplashItem] {
        queries.access { $0.append(query) }
        return []
    }
    func downloadImage(spaceId: String, id: String, createdInContext: String, createdInContextRef: String) async throws -> ObjectId {
        throw InitializationProbeFailure.timeout
    }
}

enum ProbeRegistry {
    static let service = AtomicBox<ServiceProbe?>(nil)
    static let resolutions = AtomicBox(0)
    static func resolve() -> any UnsplashServiceProtocol {
        guard let service = service.value else { preconditionFailure("Required initialization probe dependency") }
        resolutions.access { $0 += 1 }
        return service
    }
}

public protocol SharedContainer: AnyObject {
    static var shared: Self { get }
}
public final class Container: SharedContainer, @unchecked Sendable {
    public static let shared = Container()
    public var unsplashService: Factory<any UnsplashServiceProtocol> { Factory { ProbeRegistry.resolve() } }
}
public struct Factory<T> {
    private let body: () -> T
    public init(_ body: @escaping () -> T) { self.body = body }
    public func callAsFunction() -> T { body() }
    public func resolve() -> T { body() }
    public func reset(_ options: FactoryResetOptions) {}
}
public enum FactoryResetOptions { case none }
public protocol BoxedFactoryReference {
    func factory<U>() -> Factory<U>
}
public struct FactoryReference<C: SharedContainer, T>: BoxedFactoryReference {
    public init(keypath: KeyPath<C, Factory<T>>) {}
    public func factory<U>() -> Factory<U> {
        preconditionFailure("Factory reference resolution is outside this initializer control")
    }
}

protocol GridItemViewModelProtocol {}
struct GridItemSection<T> {
    let title: String?
    let items: [T]
}
struct UnsplashItemViewModel {
    let item: UnsplashItem
    init(item: UnsplashItem) { self.item = item }
}
enum SearchAvailability { case available(placeholder: String) }
enum Loc { static let search = "Probe search" }
final class AnyCancellable {}
enum ProbeInterval { case seconds(Double) }
struct ProbePublisher<T> {
    func debounce(for interval: ProbeInterval, scheduler: RunLoop) -> Self { self }
    func sink(_ receive: @escaping (T) -> Void) -> AnyCancellable { AnyCancellable() }
}
@propertyWrapper
struct Published<T> {
    var wrappedValue: T
    var projectedValue: ProbePublisher<T> { ProbePublisher() }
}

@MainActor
final class EditorDocumentWriteOwner {
    let identity: String
    var synchronousChecks = 0
    var readNames: [[String]] = []
    init(identity: String) { self.identity = identity }
    func performSynchronousOperation<T>(requiresEditing: Bool, operation: () -> T) throws -> T {
        synchronousChecks += 1
        return operation()
    }
    func performRead<T: Sendable>(rpcNames: Set<String>, operation: @Sendable () async throws -> T) async throws -> T {
        readNames.append(rpcNames.sorted())
        return try await operation()
    }
    func performMutation<T: Sendable>(spaceId: String, createdInContext: String, operation: @Sendable () async throws -> T) async throws -> T {
        try await operation()
    }
}
