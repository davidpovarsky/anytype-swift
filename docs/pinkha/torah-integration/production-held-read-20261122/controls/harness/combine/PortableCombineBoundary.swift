public struct AnyPublisher<Output: Sendable, Failure: Error>: Sendable {
    public init() {}
    public func removeDuplicates() -> Self where Output: Equatable { self }
    public func eraseToAnyPublisher() -> Self { self }
}
