import Foundation
import HanlinMiniAppsBridge

enum PinkhaMiniAppsStrings {
    private static var hebrew: Bool { Locale.current.language.languageCode?.identifier == "he" }
    static var title: String { hebrew ? "מיני־אפליקציות" : "MiniApps" }
    static var operationChangeTitle: String { hebrew ? "אישור שינוי הפעולה" : "Confirm changed action" }
    static var apply: String { hebrew ? "החלת התוצאה" : "Apply result" }
    static var cancel: String { hebrew ? "ביטול" : "Cancel" }
    static func operationChangeMessage(_ operation: MiniAppOperation) -> String {
        let action: String
        switch operation {
        case .replaceDocument: action = hebrew ? "להחליף את תוכן המסמך" : "replace the document content"
        case .replaceSelection: action = hebrew ? "להחליף את הטקסט שנבחר" : "replace the selected text"
        default: action = hebrew ? "להוסיף תוכן למסמך" : "add content to the document"
        }
        return hebrew
            ? "המיני־אפליקציה מבקשת \(action), בשונה מהפעולה שנבחרה. להחיל את התוצאה?"
            : "The MiniApp asks to \(action), which differs from the action you selected. Apply this result?"
    }
    static var attachment: String { hebrew ? "קובץ מצורף" : "Attachment" }
    static var close: String { hebrew ? "סיום" : "Done" }
    static var documentUnavailable: String { hebrew ? "המסמך המקורי עדיין לא זמין. התוצאה נשמרה ותחזור כשהמסמך ייפתח." : "The original document is not ready. The result is saved and will return when it opens." }
    static var attachmentUnavailable: String { hebrew ? "לא ניתן היה להכין את הקובץ לשיתוף." : "The attachment could not be prepared for sharing." }
    static var sourceChanged: String { hebrew ? "התוכן המקורי השתנה. תוצאת המיני־אפליקציה נשמרה בנפרד במסמך." : "The original content changed. The MiniApp result was saved separately in the document." }
    static var unsupportedResult: String { hebrew ? "המיני־אפליקציה לא החזירה פעולה שניתן לבצע במסמך. התוצאה נשמרה." : "The MiniApp did not return an edit that can be applied to this document. Its result is saved." }
    static var resultNotSaved: String { hebrew ? "שמירת תוצאת המיני־אפליקציה עדיין לא אומתה. התוצאה נשמרה להמשך." : "The MiniApp edit has not been verified as saved. Its result is retained." }
    static var companionMissing: String { hebrew ? "לא ניתן לפתוח את Hanlin MiniApps. יש להתקין את האפליקציה כדי להפעיל מיני־אפליקציות." : "Hanlin MiniApps could not be opened. Install the app to run MiniApps." }
}
