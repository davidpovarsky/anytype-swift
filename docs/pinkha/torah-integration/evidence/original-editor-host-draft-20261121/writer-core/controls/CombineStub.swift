// Type-only portable test fixture; publisher delivery is not exercised here.
public struct AnyPublisher<Output: Sendable, Failure: Error>: Sendable {
    public init() { }
    public func removeDuplicates() -> Self { self }
    public func eraseToAnyPublisher() -> Self { self }
}
