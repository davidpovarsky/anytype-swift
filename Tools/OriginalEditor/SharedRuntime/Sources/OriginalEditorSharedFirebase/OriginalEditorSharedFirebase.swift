import Foundation
import FirebaseCore
import FirebaseMessaging

/// A real dynamic linkage boundary. Original public modules retain their names.
public enum OriginalEditorSharedFirebase {
    public static var firebaseClassNames: [String] {
        [NSStringFromClass(FirebaseApp.self), NSStringFromClass(Messaging.self)]
    }
}
