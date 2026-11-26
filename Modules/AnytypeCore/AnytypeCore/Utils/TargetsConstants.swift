import Foundation

public struct TargetsConstants {    
    public static var appGroup: String  {
        // A separate owner build declares its native group in every host bundle.
        // Existing configurations retain their original storage group below.
        if let ownerGroup = Bundle.main.object(forInfoDictionaryKey: "PinkhaNativeAppGroup") as? String,
           !ownerGroup.isEmpty, !ownerGroup.contains("$(") {
            return ownerGroup
        }
        switch CoreEnvironment.targetType {
        case .debug:
            return "group.io.anytype.app.dev"
        case .releaseAnytype:
            return "group.io.anytype.app"
        }
    }
}
