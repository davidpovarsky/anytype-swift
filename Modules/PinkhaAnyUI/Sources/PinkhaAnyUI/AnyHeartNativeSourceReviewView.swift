#if canImport(SwiftUI)
import Foundation
import SwiftUI
import PinkhaAnyHost

/// Read-only presentation of a real source capture. A capture review is not
/// destination admission. The app owns capture/cancel/release and navigation.
public struct AnyHeartNativeSourceReviewView: View {
    private let review: AnyHeartNativeSourceCaptureReview
    private let spaceName: String
    private let objectNames: [Data: String]

    public init(review: AnyHeartNativeSourceCaptureReview, spaceName: String = "") {
        self.review = review; self.spaceName = spaceName
        objectNames = Dictionary(uniqueKeysWithValues: review.bundle.objects.map {
            (Data($0.sourceObjectID.utf8), $0.details["name"]?.string ?? "")
        })
    }

    public var body: some View {
        List {
            Section {
                Label(t("המקור נשמר לבדיקה", "Source captured for review"), systemImage: "doc.text.magnifyingglass")
                    .font(.headline)
                    .accessibilityIdentifier("heart-source-review-status")
                Text(t(
                    "העברת המרחב עדיין דורשת השלמת התאמות ואימות. נתוני המקור נשמרו באפליקציה, ולא נכתבו ליעד.",
                    "Moving this space still requires mapping and verification. The captured source is retained in the app; no destination data has been written."
                ))
                .font(.callout).foregroundStyle(.secondary)
                .accessibilityIdentifier("heart-source-review-pending-migration")
                if !spaceName.isEmpty { LabeledContent(t("מרחב", "Space"), value: spaceName) }
            }

            Section(t("פרטי אימות המקור", "Source verification details")) {
                DisclosureGroup(t("זהות המקור והצילום", "Source and capture identity")) {
                    identity(t("חשבון", "Account"), review.descriptor.sourceAccountID, id: "account")
                    identity(t("מרחב", "Space ID"), review.descriptor.sourceSpaceID, id: "space")
                    identity(t("מזהה צילום", "Capture ID"), review.descriptor.requestID, id: "capture-id")
                    identity(t("טביעת אצבע של הצילום", "Capture fingerprint"), review.descriptor.manifestSHA256, id: "fingerprint")
                    count(t("עצים מקוריים", "Native trees"), review.descriptor.nativeTrees, id: "trees")
                    if let census = review.bundle.nativeStoreContext?.headCensus {
                        count(t("רשומות מקור, לרבות הגדרות והרשאות", "Source identities, including settings and permissions"),
                              census.sourceHeadIDs.count, id: "native-heads")
                    }
                }
                .accessibilityIdentifier("heart-source-review-identity")
                Text(t(
                    "שינוי בחשבון, במרחב או בתוכן מחייב בדיקה חוזרת של המקור לפני העברה.",
                    "An account, space or content change requires the source to be checked again before transfer."
                )).font(.footnote).foregroundStyle(.secondary)
            }

            Section(t("התוכן שנלכד", "Captured content")) {
                count(t("אובייקטים", "Objects"), review.descriptor.capturedObjects, id: "objects")
                count(t("בלוקים", "Blocks"), review.bundle.objects.reduce(0) { $0 + $1.blocks.count }, id: "blocks")
                count(t("סוגי אובייקטים", "Object types"), review.definitionPlan.catalog.types.count, id: "types")
                count(t("מאפיינים", "Properties"), review.definitionPlan.catalog.relations.count, id: "properties")
                count(t("אפשרויות בחירה", "Choice options"), review.definitionPlan.catalog.options.count, id: "options")
                count(t("קבצים מצורפים", "Attachments"), review.descriptor.capturedFiles, id: "files")
                Text(review.descriptor.currentFilePayloadCompleteness
                     ? t("כל תוכן הקבצים הנוכחי נכלל בצילום המקור.", "All current file content is included in this capture.")
                     : t("חלק מתוכן הקבצים חסר בצילום המקור. נדרשת לכידה מלאה לפני העברה.", "Some file content is missing from this capture. A complete capture is required before transfer."))
                    .font(.footnote).foregroundStyle(.secondary)
                    .accessibilityIdentifier("heart-source-review-file-completeness")
            }

            sourceLimits
            pinkhaMappings
            definitions
            currentPages
            unmappedObjects
        }
        .navigationTitle(t("בדיקת מרחב Heart", "Review Heart space"))
        .accessibilityIdentifier("heart-source-review")
    }

    private var sourceLimits: some View {
        Section(t("השלמות נדרשות במקור", "Source requirements")) {
            count(t("פערים בהתאמת סוגים ומאפיינים", "Type and property mapping requirements"),
                  review.definitionPlan.issues.count, id: "definition-issues")
            count(t("דפים עם התאמת תוכן נוכחי", "Pages with current content mapping"),
                  review.currentPagePlans.count, id: "page-plans")
            count(t("אובייקטים ללא התאמה מלאה", "Objects without a complete mapping"),
                  review.unmappedObjects.count, id: "unmapped")
            if !review.bundle.sourceGaps.isEmpty {
                count(t("פערים בצילום המקור", "Capture gaps"), review.bundle.sourceGaps.count, id: "capture-gaps")
            }
            if !review.bundle.resolverUnmapped.isEmpty {
                count(t("שדות מקור שדורשים מיפוי", "Source fields requiring mapping"),
                      review.bundle.resolverUnmapped.count, id: "resolver-gaps")
            }
            if !review.bundle.bundledDefinitionsUsed.isEmpty {
                DisclosureGroup(t("הגדרות מובנות שדורשות התאמה", "Built-in definitions requiring mapping")) {
                    ForEach(Array(review.bundle.bundledDefinitionsUsed.enumerated()), id: \.offset) { _, name in
                        Text(name).font(.footnote).textSelection(.enabled)
                    }
                }
            }
            let collections = review.bundle.nativeStoreContext?.unmappedCollectionNames.count ??
                review.bundle.retainedOtherCollections.count
            if collections > 0 {
                count(t("אוספי מקור נוספים שדורשים התאמה", "Additional source collections requiring mapping"),
                      collections, id: "collections")
            }
            if review.bundle.nativeStoreContext?.headCensus == nil {
                Text(t("ספירת נתוני המקור המלאה טרם אומתה.", "The complete source identity census has not been verified."))
                    .font(.footnote).foregroundStyle(.secondary)
                    .accessibilityIdentifier("heart-source-review-incomplete-census")
            }
            ForEach(Array(review.bundle.issues.enumerated()), id: \.offset) { index, issue in
                DisclosureGroup(t("פרט מקור שדורש בדיקה", "Source detail requiring review")) {
                    Text(issue.code).font(.footnote).textSelection(.enabled)
                    Text(issue.field).font(.footnote).textSelection(.enabled)
                }
                .accessibilityIdentifier("heart-source-review-source-issue-\(index)")
            }
            Text(t(
                "היסטוריה, הגדרות, הרשאות וכל סוג תוכן דורשים התאמה למנוע היעד ואימות פתיחה מחדש.",
                "History, settings, permissions and every content type require a destination mapping and reopen verification."
            )).font(.footnote).foregroundStyle(.secondary)
        }
    }

    @ViewBuilder
    private var pinkhaMappings: some View {
        if let source = review.pinkhaSource {
            Section(t("מבנה ומקורות של Pinkha", "Pinkha structure and sources")) {
                count(t("פריטי היררכיה", "Hierarchy items"), source.hierarchy.count, id: "pinkha-hierarchy")
                count(t("מסמכים עם שדה מקורות", "Documents with a source field"),
                      source.canonicalDocuments.count, id: "pinkha-source-documents")
                count(t("קישורים למקורות", "Source associations"),
                      source.canonicalDocuments.reduce(0) { $0 + $1.records.count }, id: "pinkha-associations")
                count(t("פרטי מבנה שדורשים התאמה", "Structure mapping requirements"),
                      source.issues.count, id: "pinkha-issues")
                Text(t(
                    "המבנה זוהה לפי מזהי ההגדרות שנשמרו במקור. ההעברה ממתינה להשלמת ההתאמות והאימות.",
                    "The structure was identified from the original stored definition IDs. Transfer still requires complete mapping and verification."
                )).font(.footnote).foregroundStyle(.secondary)
            }
        } else if let issue = review.pinkhaSourceIssue {
            Section(t("מבנה Pinkha דורש בדיקה", "Pinkha structure requires review")) {
                Text(t(
                    "הגדרות המבנה המקוריות אינן שלמות או אינן חד־משמעיות. הנתונים נשמרו לבדיקה.",
                    "The original structure definitions are incomplete or ambiguous. The source data is retained for review."
                )).font(.callout)
                DisclosureGroup(t("פרטי הבדיקה", "Review details")) {
                    Text(issue).font(.footnote).textSelection(.enabled)
                }
            }
            .accessibilityIdentifier("heart-source-review-pinkha-schema-issue")
        }
    }

    private var definitions: some View {
        Section(t("סוגים ומאפיינים", "Types and properties")) {
            DisclosureGroup(t("סוגי האובייקטים שנלכדו", "Captured object types")) {
                ForEach(Array(review.definitionPlan.types.enumerated()), id: \.offset) { _, binding in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(binding.definition.name)
                        Text(binding.definition.recommendedLayout == 0
                             ? t("פריסת דף", "Page layout")
                             : t("פריסה שעדיין דורשת התאמה", "Layout still requires mapping"))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
            ForEach(Array(review.definitionPlan.issues.enumerated()), id: \.offset) { index, issue in
                DisclosureGroup {
                    identity(t("אובייקט מקור", "Source object"), issue.sourceObjectID)
                    Text(issue.field).font(.footnote).textSelection(.enabled)
                    Text(issue.reason).font(.footnote).textSelection(.enabled)
                } label: {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(objectName(issue.sourceObjectID))
                        Text(requirementLabel(field: issue.field)).font(.caption).foregroundStyle(.secondary)
                    }
                }
                .accessibilityIdentifier("heart-source-review-definition-issue-\(index)")
            }
        }
    }

    private var currentPages: some View {
        Section(t("טיוטות התאמת דפים", "Draft page mappings")) {
            Text(t(
                "הטיוטות כוללות כותרת, ערכי מאפיינים ותוכן נתמכים. הן ממתינות להשלמת כל דרישות המרחב.",
                "These drafts include supported titles, property values and body content. They remain pending until every space requirement is met."
            )).font(.footnote).foregroundStyle(.secondary)
            ForEach(Array(review.currentPagePlans.enumerated()), id: \.offset) { index, page in
                DisclosureGroup(objectName(page.sourceObjectID)) {
                    identity(t("אובייקט מקור", "Source object"), page.sourceObjectID)
                    count(t("ערכי מאפיינים קיימים", "Present property values"), page.presentDetailKeys.count,
                          id: "page-\(index)-values")
                    ForEach(Array(page.sourceIssues.enumerated()), id: \.offset) { _, issue in
                        Text(issue).font(.footnote).textSelection(.enabled)
                    }
                }
                .accessibilityIdentifier("heart-source-review-page-\(index)")
            }
        }
    }

    private var unmappedObjects: some View {
        Section(t("אובייקטים שעדיין דורשים התאמה", "Objects still requiring mapping")) {
            ForEach(Array(review.unmappedObjects.enumerated()), id: \.offset) { index, object in
                DisclosureGroup(objectName(object.sourceObjectID)) {
                    identity(t("אובייקט מקור", "Source object"), object.sourceObjectID)
                    Text(object.reason).font(.footnote).textSelection(.enabled)
                }
                .accessibilityIdentifier("heart-source-review-unmapped-\(index)")
            }
        }
    }

    private func objectName(_ id: String) -> String {
        let name = objectNames[Data(id.utf8)] ?? ""
        return name.isEmpty ? t("אובייקט ללא שם", "Unnamed object") : name
    }

    private func requirementLabel(field: String) -> String {
        if field.contains("Layout") || field.contains("recommend") {
            return t("פריסה והצגת מאפיינים", "Layout and property presentation")
        }
        if field == "relationDefaultValue" {
            return t("התנהגות ערכי ברירת מחדל", "Default-value behavior")
        }
        if field == "relationReadonlyValue" || field == "isReadonly" {
            return t("ערכים נגזרים או לקריאה בלבד", "Derived or read-only values")
        }
        if field == "isArchived" { return t("מצב ארכיון", "Archive state") }
        return t("התאמת הגדרה", "Definition mapping")
    }

    private func count(_ label: String, _ value: Int, id: String) -> some View {
        LabeledContent(label, value: value.formatted())
            .accessibilityElement(children: .combine)
            .accessibilityIdentifier("heart-source-review-" + id)
            .accessibilityValue(String(value))
    }

    private func identity(_ label: String, _ value: String, id: String? = nil) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label).font(.caption).foregroundStyle(.secondary)
            if let id {
                Text(value).font(.footnote.monospaced()).textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityIdentifier("heart-source-review-" + id)
            } else {
                Text(value).font(.footnote.monospaced()).textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func t(_ hebrew: String, _ english: String) -> String { AnyUIErrorText.text(hebrew, english) }
}
#endif
