# Anytype × Pinkha — תוכנית אב מחייבת להעברת המערכת התורנית

> **מסמך שליטה ראשי | גרסה 1.0 | 15 באוקטובר 2026 | סטטוס: תוכנית מאושרת לביצוע בשלבים, טרם התחיל שלב 1**  
> מסמך זה מתייחס להעברת המערכת התורנית מ־Pinkha לתוך המזלג של Anytype (`davidpovarsky/anytype-swift`). הוא **אינו** תוכנית להחלפת מנוע Anytype או למיזוג גורף של Pinkha אליה.  
> המסמך המשלים **`Anytype_Torah_Integration_STAGE_01_AGENT_v1.md`** הוא הוראת הביצוע לשלב הראשון בלבד. אין להשתמש בו כאישור לביצוע השלבים הבאים.

---

## 0. חוזה הפרויקט והעיקרון המנחה

**המטרה:** אפליקציית כתיבה וידע תורנית טבעית, קלה ומהירה כמו Apple Notes, המשתמשת בעורך ובמנוע האובייקטים והסנכרון המקוריים של Anytype, ומוסיפה מנגנוני מקורות, חיבורי ידע, פירושים, ציטוטים והערות המבוססים על Pinkha ועל `TorahInspectorKit` העדכני.

**המסלול המרכזי שחייב לעבוד בסוף:**

1. המשתמש כותב חידוש או פותח מסמך קיים ב־Anytype.
2. הוא מקשר מסמך, בלוק או קטע טקסט ל**מקור תורני**, ל**נושא** או ל**ערך מילוני**.
3. המערכת מזהה ושומרת `providerID` + מזהה קנוני, ולא מסתפקת בכותרת או URL.
4. המשתמש פותח **Inspector מקורי בהקשר המסמך**, מעיין בקטע, במפרשים, בקישורים ובנושאים.
5. הוא מכניס ציטוט שלם או קטע נבחר כ־Quote קריא ולא־עריך, עם provenance מלא וקישור למקור המדויק.
6. אפשר להוסיף הערה/חידוש ולפתוח את מסמך Anytype המתאים מתוך אזור Notes ב־Inspector.
7. בלשונית הידע ניתן לצאת ממקור/מילה/נושא ולמצוא את כל המסמכים המקושרים אליו — באופן דו־כיווני.
8. התוכן, החיבורים וההערות נשמרים במודל הנתונים של Anytype ומסונכרנים בהתאם להרשאות Space; מטמון מקורות חיצוניים אינו מאגר האמת.

**לא מספיק להציג Inspector בלבד.** הפרויקט מסתיים רק לאחר שבוצע המסלול מקצה לקצה, כולל שמירה, שחזור, סנכרון, טיפול בכשלים ובדיקות התנהגות העורך.

### מקורות האמת, סדר קדימויות

1. הקוד בפועל ב־commit המאומת של כל מאגר — המקור לקביעה מה קיים, ולא קובצי תוכנית בלבד.
2. תוכנית אב זו והחלטות ADR שתועדו — מקור האמת לדרישות ולבחירת ארכיטקטורה.
3. מסמך השלב הפעיל — מקור האמת למשימות ולקריטריוני המעבר של אותו שלב.
4. תוצאות CI, build, מבחני מכשיר והדגמה — מקור האמת למצב האימות; קוד קיים אינו שקול ל־PASS.

אין לשנות החלטה אדריכלית מחייבת בשקט. במקרה של מידע חדש: לתעד, להסביר השפעה, להציע ADR; לא להסיט את היישום בלי תיעוד ואישור במקומות שמשנים scope.

---

## 1. Baseline מאומת — נעול לצורך התחלת העבודה

הענפים והקוד נבדקו באמצעות GitHub בתאריך 15.10.2026. כל SHA להלן הוא **נקודת עוגן לתחילת המשימה**, ולא הבטחה שיישאר הענף האחרון בעתיד.

| תפקיד | Repository / ref | SHA מאומת |
|---|---|---|
| יעד, בסיס הפיתוח | [`davidpovarsky/anytype-swift`, `pinkha/hierarchy-home-v1`](https://github.com/davidpovarsky/anytype-swift/tree/pinkha/hierarchy-home-v1) | `e9ae976ca7882ac0b1fa8efb2f75e20618c82718` |
| מקור יכולות Pinkha | [`davidpovarsky/pinkha`, `torah-ux-knowledge-tab`](https://github.com/davidpovarsky/pinkha/tree/torah-ux-knowledge-tab) | `24e074d5557dba632d36dbb71fda8cf9acb8d3ac` |
| ספריית Inspector המעודכנת | [`davidpovarsky/TorahInspectorKit`, `codex/shared-torah-inspector-maktabah`](https://github.com/davidpovarsky/TorahInspectorKit/tree/codex/shared-torah-inspector-maktabah) | `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418` |
| ענף ברירת המחדל של Anytype | `develop` | `50bba7deb59ecb76d20ace5312f0343c9256bf84` בבדיקה |

**הערות קריטיות:**

- `develop` היה בעל commit מאוחר יותר בזמן, אך `pinkha/hierarchy-home-v1` מכיל את בסיס הפיצ'רים הייעודיים שאנו רוצים לשמר. **אין למזג אליו `develop` אוטומטית.** סקר הפערים מול upstream הוא משימה נפרדת.
- מקור Pinkha מצמיד ב־`app/Packages/PinkhaTorah/Package.swift` את TorahInspectorKit ל־`0.1.0`, ואילו בספרייה קיימת תגית `0.1.2` וענף `maktabah` מתקדם עוד יותר. הפיתוח החדש יצמיד **revision מפורש** ל־SHA המעודכן ולא `main`/טווח גרסאות בלתי מבוקר. עדכון עתידי מחייב audit ובדיקות.
- `TorahInspectorKit` ב־revision שנבדק מציע שני מוצרי SPM: `TorahInspectorCore` ו־`TorahInspectorUI` (Swift tools 6.0; iOS 17+, macOS 14+).
- `Modules/PinkhaKit` ב־Anytype הוא package טהור של מודלים ו־domain, ללא תלות קיימת ב־TorahInspectorKit. נכון לעכשיו נמצאים בו בעיקר `TorahAssociationModels.swift` ו־`TorahAssociationRepository.swift` (פרוטוקול בלבד), לא מימוש אחסון.
- `docs/pinkha/PORTED_CODE.md` ב־Anytype מתאר קוד כ"הועבר", אך חלק מהקבצים המוזכרים **אינם בעץ הענף שנבדק**. אין לראות במסמך זה ראיית מימוש.
- Anytype כולל `.github/workflows/pinkha-tests.yaml` (`swift test --package-path Modules/PinkhaKit`) ו־`.github/workflows/pinkha-validation.yml` (בדיקות + בניית IPA unsigned). יש להשתמש במסלולים הקיימים ולא לייצר CI כפול ללא צורך.

### נקודות חיבור קיימות שזוהו ב־Anytype

- `Modules/PinkhaKit/Package.swift` — יעד למודלים, ספקי API, ה־core ולטסטים.
- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationModels.swift` — לשמור מודלים קיימים ותאימות אחורה.
- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationRepository.swift` — חוזה האחסון, שימומש בשלב 2.
- `Anytype/Sources/Pinkha/` — integration, UI וממשקים כלפי העורך וה־Space.
- `Anytype/Sources/PresentationLayer/Flows/EditorPageFlow/EditorPageCoordinatorView.swift` — מארח אפשרי ל־Inspector בשלב 3.
- `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Models/BlockViewModelBuilder.swift` — עיטור/הצגה מינימליים בלבד בשלב 4, תוך שמירת row identity.
- `Modules/Services/Sources/Services/BlockService/BlockServiceProtocol.swift` — `add`, `delete`, `setFields` וממשקי בלוקים מקוריים.
- `Anytype/Sources/ServiceLayer/Block/BlockActionHandler/BlockActionService/BlockActionService.swift` — `add(..., setFocus: Bool)`; ציטוט תורני חייב `setFocus: false`.
- `Modules/Services/Sources/Models/Block/BlockInformation/BlockInformationConverter.swift` — מסלול ההמרה **מאפס כרגע את `fields` בעת יצירת block protobuf**. אין להניח שמטא־דאטה תשרוד יצירה אוטומטית; בשלב 4 יש לשמור שדות באמצעות API מתאים ולבדוק round-trip.
- `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Common/LinkToSearchHandling.swift` — קישורים קיימים (`link`, `linkToObject`); לא להמציא קישורים חדשים במנוע Heart.

---

## 2. סקר יכולות: מה מועבר ומה אינו קיים עדיין

**סיווג:** `קיים במקור` = אותר בקוד Pinkha; `תשתית יעד` = קיים בסיס ב־Anytype; `חדש` = דורש פיתוח מעבר למה שמומש במקור.

| מזהה | יכולת | מצב מקור | דרישת היעד / תנאי קבלה | שלב |
|---|---|---|---|---|
| C01 | חיפוש/אימות מראה מקום בעברית/אנגלית | קיים במקור (`SefariaReferenceProvider`) | autocomplete; canonical ref; הצגת שגיאות | 1,3 |
| C02 | קריאת טקסט, גרסה, רישיון, כיוון | קיים (`SefariaTextProvider`) | text + metadata ללא אובדן | 1 |
| C03 | קישורים, פירושים, נושאים על מקור | קיים (`SefariaRelationshipProvider`) | פרק ופסוק מדויקים, קטגוריות | 1,3 |
| C04 | נושאים ומילים (כולל הקשר lookup_ref) | קיים | searchable, selectable, canonical | 1,3 |
| C05 | היררכיית מקורות מתוך TOC | קיים | עץ ספרים מסונן לפי שימוש | 1,5 |
| C06 | חיבור למיקום במסמך/בלוק | קיים במקור, תשתית יעד | שמירה Anytype, הרשאות וסנכרון | 2 |
| C07 | ניהול חיבורים ב־UI | קיים במקור | add/remove/list; גלוי במקום הנכון | 3 |
| C08 | Inspector ברמת המסמך | קיים במקור | session מוגדר space+object; UI native | 3 |
| C09 | UI Inspector משודרג | קיים בענף `maktabah` | Commentaries / Links / Notes; קבוצות ו־RTL | 3,5 |
| C10 | Quote מקור קריא עם קישור חזרה | קיים במקור | Quote רגיל + source metadata + no autofocus | 4 |
| C11 | הוספת קטע נבחר / preview | קיים במקור | provenance כולל טווח מדויק | 4 |
| C12 | גרירה, הקשר, פקודת `/` | קיים במקור | משתלב ב־slash menu של Anytype | 4 |
| C13 | אינדקס הפוך + לשונית ידע | קיים במקור | מקור/מילה/נושא -> כל מסמכי Anytype | 5 |
| C14 | הערות בלשונית Notes | API ב־kit החדש | הערה היא מסמך Anytype, callbacks פעילים | 5 |
| C15 | שחזור ו־sync בין מכשירים | Anytype מספק בסיס | E2E, לא רק mock | 2,6 |
| C16 | תמיכה מלאה בעברית ו־RTL | חלקית במקור/יעד | mixed script, selection, cursor, נגישות | 3–6 |
| X01 | זיהוי אוטומטי מלא של מראי מקום בטקסט | **לא נמצא כיכולת כללית ממומשת** | אופציונלי, עם הצעת קישור מבוקרת | הרחבה נפרדת |
| X02 | ספק Otzaria פעיל | **לא נמצא ספק עובד במקור** | חיבור חיצוני בכפוף לזמינות/רישוי | הרחבה נפרדת |
| X03 | `[[שם מסמך]]` + backlinks תורניים משופרים | חזון פרויקט, לא חלק מבוקר ממימוש Torah | להשתמש ב־Anytype native links, לפתח כנדרש | הרחבה נפרדת |
| X04 | Automation/Scripting triggers | חזון פרויקט, לא חלק מה־port | API נפרד, הרשאות, quotas ו־sandbox | הרחבה נפרדת |

### פערים שיש לשמר במעקב

- ספריית `TorahInspectorKit` החדשה מגדירה `TorahInspectorSelection.scope = .section | .segment`, `TorahInspectorFocus`, `TorahStudyTool`, `TorahInspectorChrome` ו־callbacks עבור Notes. אסור להתבסס על API ה־`segmentRelationships` הישן בלי audit.
- במודל Pinkha הערך השמור של תפקיד ציטוט הוא `source_quote`; ב־Anytype `TorahAssociationRole.sourceQuote` משתמש כרגע במחרוזת `sourceQuote`. צריך codec/version migration בשלב 2; לא להניח שזה אותו serialization.
- במודל Anytype הקיים אין provenance עשיר זהה ל־Pinkha: מקור/גרסה/רישיון/זמן שליפה/טווח בחירה. להוסיף בגרסה חדשה תואמת אחורה, לא להחליף payload ישן או לשבור מסמכים.
- `TorahInspectorKit` מציג UI של הערות, אבל אינו מספק אחסון Anytype: נתוני Notes יוזנו מן ה־Host רק בשלב 5.

---

## 3. ארכיטקטורת היעד (מחייבת)

```text
Anytype native UI / UIKit block editor / SwiftUI navigation
        |                  |
        |          narrow guarded editor hooks
        v                  v
Anytype Torah Integration (Anytype/Sources/Pinkha/Torah/)
  - DocumentTorahSession (spaceId + objectId + selected blockId)
  - InspectorHost / HostActions
  - TorahAssociationService / Anytype repository adapter
  - TorahSourceInsertionCoordinator / quote decoration
  - TorahKnowledgeQueryService / notes adapter
        |                               |
        v                               v
Modules/PinkhaKit                  Anytype native services
  - semantic models/codec          - Object/Details/BlockService
  - Sefaria providers              - Heart sync and permissions
  - TorahInspectorRepository       - native links and search
  - hierarchy/parser
        |
        v
TorahInspectorKit @ fixed revision
  - TorahInspectorCore
  - TorahInspectorUI (host layer, introduced with UI stage)
        |
        v
Sefaria API (first provider); optional Otzaria adapter later
```

### חוקים שאסור לשבור

1. **לא לשנות Heart, anyproto, סכמת protobuf, מנוע הסנכרון או מבנה בלוק חדש.** לעשות שימוש ב־Quote הקיים, fields, details, relations ובשירותים המקוריים.
2. **המשתמש שומר מידע אישי ב־Anytype.** תכני חידושים, חיבורים, הערות ועוגני קישור אינם נשמרים ב־SQLite חיצוני כ־source of truth. מטמון טקסטים חיצוניים מותר; עליו להיות מתאפס/מחושב מחדש.
3. **העורך קודם לכול.** אסור לפגוע בזהות row, `first responder`, caret, selection, Enter, Undo, copy/paste או קצב הקלדה. אין לבצע reload מבני של כל העורך לצורך תוספת חיבורים.
4. **Lifecycle תמיד בהקשר הנכון.** session מזוהה על ידי `(spaceId, objectId)`; מעבר מסמך/Space, מחיקת מסמך וביטול חלונית חייבים לנתק callbacks וקישורים, ולא להכניס מקור למסמך ישן.
5. **שינויים ב־upstream מצומצמים ומגודרים.** הוספות ב־`Modules/PinkhaKit` ו־`Anytype/Sources/Pinkha` ככל האפשר; hook קטן ל־upstream רק אם הכרחי, עם `PinkhaRuntime.enabled` ותיעוד ב־`docs/pinkha/UPSTREAM_HOOKS.md`.
6. **API נייטיבי ולא Web UI.** Swift/SwiftUI לרוב הממשק, UIKit bridging רק עבור ה־editor הקיים והזמן/selection שלו.
7. **עברית ו־RTL מלאים, כולל mixed content.** labels מקומיים, locale, bidi, גלילה וקריאה מימין לשמאל, בלי לכפות RTL על כל האפליקציה.
8. **הפרדה בין מקור ומסמך:** אותו canonicalRef יכול להיות משויך למספר מסמכים ובלוקים, בלי ליצור עותקים של טקסטי המשתמש.
9. **הגנות כשל:** error visible, retry, cancellation, no silent `try?` במסלולי שמירה קריטיים, no empty fake success.
10. **לא לקדם גרסת dependency ללא audit.** commit נעול בתחילת המימוש, החלטת upgrade מתועדת, הרצת suite מחדש.

### מדיניות נתונים וזהויות

- `providerID` נפרד מ־`canonicalKey`; לא להשתמש בטקסט התצוגה כמזהה, ולא להניח שספק אחר משתמש באותו key.
- `TorahTarget`: מסמך שלם `(spaceId, objectId)` או בלוק `(spaceId, objectId, blockId)`. `blockId` לעולם אינו גלובלי ללא מסמך/Space.
- `kind`: `ref | topic | word`; `role`: `context | sourceQuote` (תאימות לקריאת `source_quote`).
- `TorahInspectorSelection`: מסמך/פרק או קטע מפורש — לכבד `.section` מול `.segment` ולא לייצר preferredSegmentRef יש מאין.
- sourceQuote כולל canonicalRef + providerID + displayed label + captured text + version metadata + license + retrievedAt + exact excerpt/selection, כאשר המידע זמין; אין להמציא provenance חסר.
- הרשאות Anytype חלות על יצירה/עריכה/מחיקה של associations. לקריאה בלבד אפשר לפתוח Inspector אך לא לשמור חיבור או ציטוט.
- ספירת תוצאות ידע = מספר אובייקטים ייחודיים, לא מספר בלוקים/חיבורים כפולים בתוך אותו אובייקט.

### החלטת אחסון שמחייבת gate בשלב 2

קיים כבר עיצוב בסכמת Anytype:

- Property מסמך `pinkha.torahAssociations`: מטען JSON גרסאי.
- Field בלוק `pinkha.torah.associations.v1`.
- Field ציטוט `pinkha.torah.sourceQuote.v1`.

זהו **בסיס יישום**, לא פתרון מוכח להתנגשות בין עורכים. JSON אחד ברמת מסמך עלול לסבול מעדכוני concurrent `read-modify-write` (lost update). לכן שלב 2 חייב להכריע לאחר ניסוי מוכח בין:

A. payload מרוכז עם מנגנון שמונע אובדן עדכונים גם בעת כתיבה מקבילה; או  
B. association כאובייקט/יחס native נפרד, עם אינדקס ומפתח ייחודיות.  

**אסור לסמן סנכרון מלא PASS אם לא נבדקו עדכונים מקבילים.** ההכרעה תתועד ב־ADR במאגר לפני סיום שלב 2. בשלב 1 לא מממשים אחסון כלל.

---

## 4. שלבי הביצוע המחייבים

> כל שלב בנוי מ־**מטרה, תכולה, איסורים ותנאי קבלה**. אין לפתח מראש שלב אחר "על הדרך". מסמך agent ייעודי יוכן לכל שלב לאחר בדיקת דו"ח השלב הקודם. מצב `DONE` ייקבע רק לפי ראיות.

### T0 — עיגון baseline, ביקורת ופיקוח על scope

**מטרה:** עבודה על נקודת מוצא מזוהה עם תיעוד החלטות ופערים.

- לאמת remote/refs/SHAs, סטטוס working tree ותשתית CI; לפתוח ענף פיתוח חדש מן SHA של Anytype שנבחר.
- להכניס תוכנית זו למאגר תחת `docs/pinkha/torah-integration/MASTER_PLAN.md` וליצור `PROGRESS.md` עם stages וראיות.
- לדווח על אי־התאמות קוד/תיעוד, לא להסתיר.

**Gate:** baseline recorded; branch isolated; no branch merges; no modifications to original source repos.

### T1 — תשתית Core, תלות Inspector עדכנית וספק Sefaria (מסמך סוכן ראשון)

**מטרה:** שכבה תורנית עובדת ובדיקה, אך ללא UI וללא שינוי מסמכי משתמש.

- להצמיד `TorahInspectorCore` מ־revision נעול של TorahInspectorKit כ־SPM dependency בתוך `Modules/PinkhaKit`.
- להעביר **באופן מותאם** את `SefariaClient`, `SefariaReferenceProvider`, `SefariaTextProvider`, `SefariaRelationshipProvider`, `SefariaTopicProvider`, `SefariaLexicalProvider`, היררכיית TOC, utilities ומודלי חיפוש שאינם קיימים ביעד.
- להגדיר שירותים/registry ו־factory של `TorahInspectorRepository` עם text/links/topics fetchers, notesFetcher ריק במפורש (שלב 5).
- ליצור transport injectable לצורך בדיקות ללא רשת, cancellation, retries ניתנים לבקרה וקודי שגיאה.
- להסיר תלות בפועל ב־`TorahStore`/SQLite ממודלי המשתמש; להשתמש במטמון in-memory לספק בשלב זה בלבד.
- להוסיף unit/contract tests ו־CI באמצעות המסלולים הקיימים.

**אסור:** UI, שינוי BlockService/Heart, הוספה למסמך, שמירת associations, יצירת notes, Otzaria, מיזוג ל־`develop`.

**Gate T1:** package unit tests PASS; provider mocks ו־contract tests PASS; אחד ממסלולי iOS build הקיימים מאשר תאימות; dependency pin verified; source maps והגבלות ידועות מתועדים. ללא שינוי התנהגות משתמש.

### T2 — מודל אחסון ומימוש `TorahAssociationRepository` על Anytype

**מטרה:** מקור אמת מסונכרן של associations ברמת מסמך ובלוק, ללא UI מלא.

- audit של manifest ו־Property/Block fields קיימים; ADR אחסון והתנגשויות concurrent.
- מימוש Add/List/Update/Remove, ייחודיות, merge/conflict policy, הרשאות, טיפול בבלוק/מסמך שנמחק.
- round-trip של `sourceQuote` ו־provenance כולל migration/legacy codec (`source_quote`), במידת הצורך.
- separation של cache מול user data; schema v2 בעת שינוי פורמט; מיגרציה idempotent, קדימה/אחורה לפי מדיניות.
- unit, integration וכלי fixture להדגמת שני clients ו־two-space isolation.

**Gate T2:** persist/reopen, offline/retry, concurrent writes, device/Space isolation ללא lost update מוכחים; אין נתונים יתומים; PASS לאימות real middleware.

### T3 — Inspector native, UI לניהול חיבורים ו־Session לכל מסמך

**מטרה:** המשתמש יכול לשייך מקור/נושא/מילה למסמך או לבלוק, לפתוח Inspector ולהמשיך לכתוב.

- להוסיף `TorahInspectorUI` מן **אותו revision** של Core.
- ליצור `DocumentTorahSession`, `InspectorHost` ו־HostActions עם `spaceId/objectId/blockId` + active anchor.
- להציג Inspector דרך presentation במארח הניווט של Anytype, באופן אדפטיבי לאייפד/אייפון; להשתמש ב־`.inspector` כשהוא מתאים, לא לחקות Inspector ידנית.
- להוסיף UI חיפוש/בחירה וניהול חיבורים בראש מסמך ובתפריט בלוק, תוך שימוש בנתונים משלב T2.
- להשתמש ב־API החדש: `entryMode` (`sourceReader`/`relationships`), `scope`, `chrome` ו־selectedTool; לא לחבר Notes אמיתי לפני T5.
- לוודא close/pop/switch Space, no stale callbacks, no clipboard/selection bugs.

**Gate T3:** source selection -> Inspector; Commentary/Links accessible; add/remove persisted; can type normally; iPad+iPhone UI/device scenarios pass.

### T4 — הוספת ציטוטים, preview, excerpt, slash, drag/drop וקישורי טקסט

**מטרה:** הכנסת מקור לתוך מסמך בצורה בטוחה, מבלי לגרום לפוקוס או לקריסה.

- reuse של Quote native; `TorahSourceTransfer` כנתיב יחיד לכל פעולות ההוספה.
- Preview, entire quote, exact excerpt, context menu, drag/drop ותפריט slash של Anytype (לא לדרוס פקודת `/` הכללית).
- מקור גדול מדי -> Inspector/reader, לא inline megablock.
- Quote עם metadata מדויק (גרסה, רישיון, זמן, טווח) ו־read-only decoration; למשתמש מותר לבחור/להעתיק/למחוק בלוק לפי הרשאה, אך לא לשנות את טקסט המקור עצמו בטעות.
- insertion uses `setFocus: false`; generic insertion retains normal focus. Save block + field in safe sequence; rollback או recoverable status על כשל.
- native `link`/`linkToObject` לקישורי טקסט, בתוספת association metadata לצורך חיפוש סמנטי.
- Undo/Redo, paste, selection, cursors, view model reuse ו־cell identity regression suite.

**Gate T4:** ציטוט מוזן, נפתח מחדש, שומר מקור; no-flicker/no unwanted keyboard/no crash; undo-cleanup and error-rollback pass.

### T5 — לשונית ידע תורני, reverse lookup ו־Notes כ־Anytype documents

**מטרה:** מראי מקום, מילים ונושאים הופכים למרכזי ידע עם קישורים דו־כיווניים.

- להעביר את `TorahKnowledgeViewModel`/`TorahSourceHierarchy` אל Anytype עם אינדקס נגזר ומוגבל־Space.
- שלושה מצבים: **מקור / מילה / נושא**; לעץ המקורות יופיעו רק ענפים עם חיבורים בפועל.
- drill-down לרשימת מסמכים ייחודיים, שמירה על הקשר וניווט ישיר למסמך/בלוק.
- Notes: `notesFetcher`, `onAddNote`, `onOpenNote`, `onDeleteNote` ממופים למסמכי Anytype אמיתיים. "מחיקת הערה" ב־Inspector אינה מוחקת חידוש שלם ללא כוונה/אישור.
- cache invalidation ו־incremental search, ללא full scan בזמן הקלדה.

**Gate T5:** מהמקור אל חידוש ובחזרה, גם לאחר restart/sync; counts deduplicated; edit note in native editor, correct Space, searchable at scale.

### T6 — אימות סופי, ביצועים, נגישות, RTL ומוכנות לשחרור

**מטרה:** סימון DONE לכל C01–C16 בהתנהגות אמת, ללא רגרסיות.

- consolidated matrix unit, integration, UI, iPhone/iPad, large library, offline, concurrent sync, accessibility, RTL, iOS supported version.
- build unsigned דרך workflow קיים; signing/release רק אם נדרש בתהליך פריסה אחר ובאישור מפורש.
- סקירת UX Apple Notes-like: הפעולות העיקריות קצרות וברורות; פונקציונליות מתקדמת אינה חוסמת כתיבה.
- policy לרישיון/ייחוס טקסטים; לשמור source/version/license בפרובננס ולוודא תנאי הצגה/שיתוף.
- בדיקת פערים מול Anytype upstream **בנפרד** מ־merge, אין שינויים נסתרים ב־Heart.

**Gate T6:** regression suite green, device UX verified, no unresolved P0/P1, evidence + remaining known limitations; owner decision on release.

### T7 — הרחבות עתידיות, שאינן מעכבות את C01–C16

- מתאם Otzaria מאומת חוקית וטכנית (מיפוי ספרים ומראי מקום, חיפוש, local/offline, רישוי).
- Smart autolinking במראי מקום חופשיים, previews, בחירת ביטחון לפני יצירת קישור.
- `[[מסמך]]`, backlinks ומפת ידע תוך ניצול native Anytype linking.
- Automation/Scripting API לשאילתות מקורות, בחירה, הוספת קישורים ושמירת שינויים עם הרשאות ו־audit trail.

**כל אחד מחייב ADR, שלב נפרד ובדיקות משלו.** אין למכור אותם כיכולת קיימת או להכניסם בטעות לתוך T1–T6.

---

## 5. מיפוי מקורות לקוד יעד

| קוד המקור ב־Pinkha / Kit | אחריות | יעד מוצע ב־Anytype | מדיניות |
|---|---|---|---|
| `PinkhaTorahCore/SefariaClient.swift` | HTTP | `Modules/PinkhaKit/.../Torah/Providers/SefariaClient.swift` | port/adapt |
| `PinkhaTorahCore/SefariaProviders.swift` | reference/topic/lexicon | `.../Torah/Providers/` | split/adapt; no SQLite |
| `PinkhaTorahCore/SefariaTextRelationships.swift` | text/links/topics | `.../Torah/Providers/` | split/adapt |
| `PinkhaTorahCore/ProviderProtocols.swift` | registry | `.../Torah/` | build stable API with kit types |
| `PinkhaTorahCore/TorahWorkspace.swift` | composition | `.../Torah/AnytypeTorahWorkspace.swift` | **rewrite** without databasePath |
| `PinkhaTorahCore/TorahReferenceUtil.swift` | parsing utility | `.../Torah/` | port/test |
| `PinkhaTorahCore/Hierarchy/*` | hierarchy | `.../Torah/Hierarchy/` | port/cache strategy |
| `PinkhaTorahCore/TorahStore.swift` | SQLite user associations/cache | **לא מעתיקים כמאגר משתמש** | replace with native Anytype + optional cache |
| `TorahInspectorKit/Sources/TorahInspectorCore/*` | source models/repository | SPM product `TorahInspectorCore` | **לא להעתיק קוד** |
| `TorahInspectorKit/Sources/TorahInspectorUI/*` | native inspector UI | SPM product `TorahInspectorUI` | **לא להעתיק קוד** |
| `LeafView/TorahDocumentInsertionBridge.swift` | document session | `Anytype/Sources/Pinkha/Torah/` | adapt to objectId/spaceId |
| `LeafViewModel+TorahInsertion.swift` | quote insertion | `Anytype/Sources/Pinkha/Torah/` | rewrite around BlockService |
| `TorahAssociationSheet`, `TorahAddLinkControl` | manage UI | `Anytype/Sources/Pinkha/Torah/Views/` | adapt native UX |
| `ReferenceCommandPopover` | preview/select | `Anytype/Sources/Pinkha/Torah/Editor/` | adapt slash/selection integration |
| `TorahKnowledgeView(Model)` | reverse index UI | `Anytype/Sources/Pinkha/Torah/Knowledge/` | adapt to Anytype search |

נתיבים תחת `...` הם **תוכנית ליצירה**, לא טענה שקבצים אלה קיימים כבר בענף.

---

## 6. תוכנית בדיקות (Test Pyramid) ו־PASS/FAIL

### בדיקות Core ו־Contract (T1)

- HTTP transport מוקלט/מזויף בלבד; responses חוקיים, לא־חוקיים, 404/429/500, timeout, cancellation.
- Hebrew/English partial/exact reference, range + Daf/Yerushalmi examples לפי הנתונים הקיימים; canonical normalization; wide reference non-embeddable.
- Text V3 metadata and fallback; noText, Hebrew RTL, source license/version; segments + previous/next.
- Linked sources grouped by commentary vs other, canonical book and anchors; topic links.
- Topic index/caching expiration; lexical `lookup_ref` context; hierarchy + path compression.
- Kit repository cache; provider mismatch rejected; note fetcher intentionally empty at T1; source transfer round trip.

### בדיקות אחסון (T2)

- Create/read/update/remove both object and block targets; source quote full metadata round-trip.
- Same canonical source on multiple objects/blocks; no accidental dedup across targets.
- Concurrent edits from two clients; restart/offline/online; absent deleted block; permission enforcement.
- Schema migration forward and old `source_quote` codec; tests before/after migration.

### בדיקות Editor, UI ו־Device (T3–T5)

- Generic insertion retains normal focus; Torah quote never autofocuses; read-only quote never enters text editing.
- Native `.inspector` scoped to active document; switch document, pop stack, switch Space, dismiss; never insert into previous document.
- Slash existing actions preserved; source search preview, excerpt, context menu, drag drop; Undo/Redo.
- iPhone/iPad, RTL mixed Hebrew/English and keyboard, navigation, Dynamic Type, VoiceOver labels.
- Knowledge tab source/word/topic + unique counts + backlinks + notes callbacks.

### כלל ראיות

- **NOT RUN** = לא בוצע, **BLOCKED** = סביבה/הרשאה מונעת, **FAIL** = נכשל, **PASS** = בדיקה בוצעה והצליחה. אין להמיר `BLOCKED` ל־`PASS`.
- Unit tests על fixtures אינם מוכיחים סנכרון מכשירים. Build unsigned אינו מוכיח UI acceptance. חייבים לתעד ראיות לכל סוג.
- להריץ CI לאחר audit + בניית suite מרוכזת, **לא מחזור אינסופי של ניסוי–CI–עוד כיסוי**. בכל ריצה: לתעד Git SHA, workflow, run URL, תוצאות ותקלה ספציפית.
- אין לשנות Xcode toolchain/SDK או עשרות קבצי upstream כדי "לתקן" build סביבתי בלי root-cause ומדיניות שינוי מאושרת.

---

## 7. סיכונים והגנות

| סיכון | חומרה | מניעה/בדיקה מחייבת |
|---|---|---|
| כשלי first responder / `inputAccessoryView` | גבוהה | `setFocus:false`, no forced reconfiguration, real device UI tests |
| metadata שנאבדת ביצירת בלוק | גבוהה | audited `BlockInformationConverter`, explicit setFields, round-trip |
| JSON property overwritten ב־sync | גבוהה | T2 ADR/concurrency tests, native association alternative |
| session ישן מכניס למסמך לא נכון | גבוהה | scope `(spaceId,objectId)` + session lifecycle tests |
| טעינת טקסט רחב מדי | בינונית/גבוהה | resolve & reject/browse broad refs, bounded sections |
| חיבור נוסף כ־duplicate | בינונית | uniqueness and idempotency, object-count semantics |
| שינוי API ב־Kit | בינונית/גבוהה | pinned SHA, semantic adapter, contract tests, controlled upgrade |
| רגרסיות ב־slash menu / editor | גבוהה | narrow hook, baseline comparison, focus and Undo tests |
| חיפוש ידע איטי | בינונית | incremental derived index, provider cache, no on-typing full scans |
| Sefaria offline/rate limits | בינונית | error/retry/backoff/cache, no mutation on failed fetch |
| כותרות עבריות מול IDs שונים | בינונית | canonical provider ID, explicit section/segment, Unicode normalization tests |
| הערה נמחקת יחד עם מסמך חשוב | גבוהה | unlink by default, explicit confirmation for deleting object |
| branch/CI שונה מהנחת הבסיס | גבוהה | SHA verification, no silent upstream merge, evidence |
| רישוי טקסטים ומקור | בינונית/גבוהה | version/license/provenance and review before release |

---

## 8. כללי העבודה המחייבים לכל סוכן בכל שלב

1. **קודם קוראים**: את תוכנית האב הזו, מסמך השלב, `docs/pinkha/ARCHITECTURE.md`, `DATA_MODEL.md`, `SCHEMA.md`, `UPSTREAM_HOOKS.md`, ואת הקוד הרלוונטי בעצמו.
2. **לא משנים ענפי מקור**: לא לגעת ב־`davidpovarsky/pinkha`, לא ב־`TorahInspectorKit`; לא למזג ל־`develop`/`dev`/`main`, לא לבצע rebase/force-push של ענפי בסיס. כל שלב בענף ייעודי משלו, מעוגן ל־SHA.
3. **לא עושים שינוי שלא בשלב**: כל דרישה מחוץ ל־scope מתועדת ב־`PROGRESS.md`/`PROJECT_BOARD.md`, לא ממומשת על הדרך.
4. **לא מניחים שתיעוד = קוד**: לעדכן registry של קוד שהועבר רק כאשר הקובץ באמת קיים, מתקמפל ונבדק.
5. **בכל שיטת קוד שונו קבצי upstream?** יש לפרט justification, feature gate וסיכון merge ב־`UPSTREAM_HOOKS.md`.
6. **ממזערים קריאות CI**: audit/tests/compile locally or preflight runner, ואז validation consolidating once; אם נדרשת עוד ריצה, להסביר את הסיבה.
7. **לא מוחקים נתונים/Branches**; לא עושים `git reset --hard`, `git clean -fdx`, `push --force`; במקרה של working tree מלוכלך — להשתמש בעץ עבודה נפרד.
8. **בטיחות ויציבות**: no secrets in logs, no background daemons, no infrastructure deployment, no signing/provisioning changes unless explicitly requested.
9. **עוצרים בגבול השלב**: לאחר PASS/FAIL מסודר מוסרים דו"ח ותוכנית השלב הבא *כהצעה בלבד*; לא מממשים שלב נוסף אוטומטית.
10. **מונעים הרחבת עיצוב**: אין redesign של Home/Hierarchy/Editor, אין שינוי במפרטים לא קשורים, אין שינוי בלוגיקה של Anytype native syncing.

---

## 9. פורמט מעקב התקדמות חובה

סוכן השלב הראשון ייצור במאגר:

`docs/pinkha/torah-integration/PROGRESS.md`

מבנה מחייב:

```markdown
# Torah Integration Progress
Master plan: MASTER_PLAN.md, v1.0
Base Anytype SHA: e9ae976ca7882ac0b1fa8efb2f75e20618c82718
Source Pinkha SHA: 24e074d5557dba632d36dbb71fda8cf9acb8d3ac
TorahInspectorKit pinned SHA: e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418

| Stage | Status | Working branch | Evidence | Outstanding |
|---|---|---|---|---|
| T0 | NOT RUN | | | |
| T1 | NOT RUN | | | |
| T2 | NOT RUN | | | |
| T3 | NOT RUN | | | |
| T4 | NOT RUN | | | |
| T5 | NOT RUN | | | |
| T6 | NOT RUN | | | |
| T7 | DEFERRED | | | |

## Decisions / ADRs
## Known risks and blockers
## Changes from approved scope
## Next authorized action
```

**שדות חובה בכל מסירת שלב:** original SHA, new branch/HEAD, רשימת קבצים שנוספו/שונו, החלטות אדריכליות, `swift test` (מספר מבחנים, PASS/FAIL), build + workflow/run URL, תוצאות acceptance מפורטות, known gaps, והשורה המדויקת שבה יש להמשיך.

### Exit criteria לכלל הפרויקט

- כל C01–C16 ב־PASS מוכח או חריגה מוסכמת ומתועדת.
- לא נדרשה החלפת Heart/סכמת protobuf ולא נפגעה יציבות עורך Anytype.
- קישור/הערה/ציטוט שורדים restart, Space switching וסנכרון, ללא metadata orphaned.
- תצוגת Inspector וידע תורני מבוססת `TorahInspectorKit` עדכני וגרסת dependency מאומתת.
- כל שינוי upstream מתועד, כל schema migration נבדק, ו־UX בעברית/RTL נבדק במכשיר.
- דו"ח release מסכם מה באמת פועל ומה עדיין דחוי; אין PASS מדומה.

---

## 10. קישורי קוד עיקריים לעבודה

- מקור Pinkha: <https://github.com/davidpovarsky/pinkha/tree/torah-ux-knowledge-tab>
- מודלי המקור: <https://github.com/davidpovarsky/pinkha/blob/torah-ux-knowledge-tab/app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/Models.swift>
- ProviderProtocols: <https://github.com/davidpovarsky/pinkha/blob/torah-ux-knowledge-tab/app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/ProviderProtocols.swift>
- Sefaria providers: <https://github.com/davidpovarsky/pinkha/blob/torah-ux-knowledge-tab/app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/SefariaProviders.swift>
- Text/links: <https://github.com/davidpovarsky/pinkha/blob/torah-ux-knowledge-tab/app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/SefariaTextRelationships.swift>
- Hierarchy: <https://github.com/davidpovarsky/pinkha/blob/torah-ux-knowledge-tab/app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/Hierarchy/TorahSourceHierarchy.swift>
- InspectorKit: <https://github.com/davidpovarsky/TorahInspectorKit/tree/codex/shared-torah-inspector-maktabah>
- Kit Core model: <https://github.com/davidpovarsky/TorahInspectorKit/blob/codex/shared-torah-inspector-maktabah/Sources/TorahInspectorCore/Models.swift>
- Kit HostActions: <https://github.com/davidpovarsky/TorahInspectorKit/blob/codex/shared-torah-inspector-maktabah/Sources/TorahInspectorUI/TorahInspectorHostActions.swift>
- Anytype PinkhaKit: <https://github.com/davidpovarsky/anytype-swift/tree/pinkha/hierarchy-home-v1/Modules/PinkhaKit>
- Anytype documents: <https://github.com/davidpovarsky/anytype-swift/tree/pinkha/hierarchy-home-v1/docs/pinkha>

---

## 11. Revision policy

- גרסה זו היא **1.0**. שינוי בהיקף/סדר/מקור אמת מחייב סעיף `Decision/ADR`, ציון הסיבה ושינוי גרסה.
- תיקוני טעות/קישור ופרטי מימוש פנימיים שלא משנים את ההחלטות יכולים להתבצע ב־patch עם log.
- אם ענפים מתקדמים: לבצע diff ו־impact analysis, לשמור baseline הישן ו־baseline החדש בדו"ח; לא לשכתב את ההיסטוריה.
- ה־master הוא המסגרת לכל המשימה; מסמך שלב לעולם אינו רשאי לסתור אותו בשקט.

**סוף תוכנית האב, v1.0.**
