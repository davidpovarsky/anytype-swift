import Foundation
public enum Anytype_Model_ParticipantPermissions: RawRepresentable, Hashable, Sendable, Swift.CaseIterable {
  public typealias RawValue = Int
  case reader // = 0
  case writer // = 1
  case owner // = 2
  case noPermissions // = 3
  case admin // = 4
  case UNRECOGNIZED(Int)

  public init() {
    self = .reader
  }

  public init?(rawValue: Int) {
    switch rawValue {
    case 0: self = .reader
    case 1: self = .writer
    case 2: self = .owner
    case 3: self = .noPermissions
    case 4: self = .admin
    default: self = .UNRECOGNIZED(rawValue)
    }
  }

  public var rawValue: Int {
    switch self {
    case .reader: return 0
    case .writer: return 1
    case .owner: return 2
    case .noPermissions: return 3
    case .admin: return 4
    case .UNRECOGNIZED(let i): return i
    }
  }

  // The compiler won't synthesize support with the UNRECOGNIZED case.
  public static let allCases: [Anytype_Model_ParticipantPermissions] = [
    .reader,
    .writer,
    .owner,
    .noPermissions,
    .admin,
  ]

}

public enum Anytype_Model_ParticipantStatus: RawRepresentable, Hashable, Sendable, Swift.CaseIterable {
  public typealias RawValue = Int
  case joining // = 0
  case active // = 1
  case removed // = 2
  case declined // = 3
  case removing // = 4
  case canceled // = 5
  case UNRECOGNIZED(Int)

  public init() {
    self = .joining
  }

  public init?(rawValue: Int) {
    switch rawValue {
    case 0: self = .joining
    case 1: self = .active
    case 2: self = .removed
    case 3: self = .declined
    case 4: self = .removing
    case 5: self = .canceled
    default: self = .UNRECOGNIZED(rawValue)
    }
  }

  public var rawValue: Int {
    switch self {
    case .joining: return 0
    case .active: return 1
    case .removed: return 2
    case .declined: return 3
    case .removing: return 4
    case .canceled: return 5
    case .UNRECOGNIZED(let i): return i
    }
  }

  // The compiler won't synthesize support with the UNRECOGNIZED case.
  public static let allCases: [Anytype_Model_ParticipantStatus] = [
    .joining,
    .active,
    .removed,
    .declined,
    .removing,
    .canceled,
  ]

}

public enum Anytype_Model_SpaceAccessType: RawRepresentable, Hashable, Sendable, Swift.CaseIterable {
  public typealias RawValue = Int
  case `private` // = 0
  case personal // = 1
  case shared // = 2
  case UNRECOGNIZED(Int)

  public init() {
    self = .private
  }

  public init?(rawValue: Int) {
    switch rawValue {
    case 0: self = .private
    case 1: self = .personal
    case 2: self = .shared
    default: self = .UNRECOGNIZED(rawValue)
    }
  }

  public var rawValue: Int {
    switch self {
    case .private: return 0
    case .personal: return 1
    case .shared: return 2
    case .UNRECOGNIZED(let i): return i
    }
  }

  // The compiler won't synthesize support with the UNRECOGNIZED case.
  public static let allCases: [Anytype_Model_SpaceAccessType] = [
    .private,
    .personal,
    .shared,
  ]

}

public typealias ParticipantPermissions = Anytype_Model_ParticipantPermissions
public typealias ParticipantStatus = Anytype_Model_ParticipantStatus

public struct Participant: Identifiable, Equatable, Sendable, Hashable {
    
    public let id: String
    public let localName: String
    public let globalName: String
    public let icon: ObjectIcon?
    public let status: ParticipantStatus
    public let permission: ParticipantPermissions
    public let identity: String
    public let identityProfileLink: String
    public let spaceId: String
    public let type: String
    
    public init(
        id: String,
        localName: String,
        globalName: String,
        icon: ObjectIcon?,
        status: ParticipantStatus,
        permission: ParticipantPermissions,
        identity: String,
        identityProfileLink: String,
        spaceId: String,
        type: String
    ) {
        self.id = id
        self.localName = localName
        self.globalName = globalName
        self.icon = icon
        self.status = status
        self.permission = permission
        self.identity = identity
        self.identityProfileLink = identityProfileLink
        self.spaceId = spaceId
        self.type = type
    }
}


extension ParticipantPermissions {
    var canEdit: Bool {
        switch self {
        case .reader, .noPermissions, .UNRECOGNIZED:
            return false
        case .writer, .owner, .admin:
            return true
        }
    }

    var isModerator: Bool {
        switch self {
        case .owner, .admin:
            return true
        case .reader, .writer, .noPermissions, .UNRECOGNIZED:
            return false
        }
    }
}


public typealias SpaceAccessType = Anytype_Model_SpaceAccessType

public extension SpaceAccessType {
    var isSharable: Bool {
        switch self {
        case .private, .shared:
            true
        case .personal, .UNRECOGNIZED:
            false
        }
    }
    
    var isShared: Bool {
        switch self {
        case .shared:
            true
        case .private, .personal, .UNRECOGNIZED:
            false
        }
    }
    
    var isDeletable: Bool {
        switch self {
        case .private, .personal, .shared:
            true
        case .UNRECOGNIZED:
            false
        }
    }
}

extension Participant {
    var isOwner: Bool {
        permission == .owner
    }

    var canEdit: Bool {
        permission.canEdit
    }
}
