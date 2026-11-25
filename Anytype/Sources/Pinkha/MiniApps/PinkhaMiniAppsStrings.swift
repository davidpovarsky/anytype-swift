import Foundation

enum PinkhaMiniAppsStrings {
    private static var hebrew: Bool { Locale.current.language.languageCode?.identifier == "he" }
    static var title: String { hebrew ? "מיני־אפליקציות" : "MiniApps" }
    static var attachment: String { hebrew ? "קובץ מצורף" : "Attachment" }
    static var close: String { hebrew ? "סיום" : "Done" }
    static var documentUnavailable: String { hebrew ? "המסמך המקורי עדיין לא זמין. התוצאה נשמרה ותחזור כשהמסמך ייפתח." : "The original document is not ready. The result is saved and will return when it opens." }
    static var attachmentUnavailable: String { hebrew ? "לא ניתן היה להכין את הקובץ לשיתוף." : "The attachment could not be prepared for sharing." }
    static var sourceChanged: String { hebrew ? "התוכן המקורי השתנה. תוצאת המיני־אפליקציה נשמרה בנפרד במסמך." : "The original content changed. The MiniApp result was saved separately in the document." }
    static var unsupportedResult: String { hebrew ? "המיני־אפליקציה לא החזירה פעולה שניתן לבצע במסמך. התוצאה נשמרה." : "The MiniApp did not return an edit that can be applied to this document. Its result is saved." }
    static var resultNotSaved: String { hebrew ? "שמירת תוצאת המיני־אפליקציה עדיין לא אומתה. התוצאה נשמרה להמשך." : "The MiniApp edit has not been verified as saved. Its result is retained." }
    static var companionMissing: String { hebrew ? "לא ניתן לפתוח את Hanlin MiniApps. יש להתקין את האפליקציה כדי להפעיל מיני־אפליקציות." : "Hanlin MiniApps could not be opened. Install the app to run MiniApps." }
}
