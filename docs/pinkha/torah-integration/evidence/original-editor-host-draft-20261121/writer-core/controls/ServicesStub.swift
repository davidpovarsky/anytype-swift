public struct AccountData: Sendable, Equatable {
    public let id: String
    public init(id: String) { self.id = id }
    public static let empty = AccountData(id: "")
}
