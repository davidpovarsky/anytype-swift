


## Named Team — Antigravity + Codex

This repository is configured for active pair programming and autonomous task coordination using the persistent named AI team across Google Antigravity and Codex:
- **איתן (eitan)**: Principal architect (boundaries, contracts, migrations, technical RFCs)
- **נועם (noam)**: Engineering (scoped implementation, focused tests, bug fixes)
- **מיה (maya)**: Native UX (screens, interactions, RTL layouts, accessibility)
- **רוני (roni)**: Independent QA (acceptance verification, test artifacts, honest status)
- **תומר (tomer)**: Integration (branches, worktrees, PRs, cross-repo dependencies)
- **יעל (yael)**: Research (API capabilities, official Apple/upstream documentation, schemas)
- **דנה (dana)**: Security & Privacy (permissions, session isolation, secrets, entitlements)

### Two-Tier Execution Policy: NORMAL vs TEAM
- **מצב ברירת מחדל: NORMAL (ביצוע ישיר בסשן הראשי):**
  הסוכן הראשי מזהה את התפקיד המתאים, טוען את הוראותיו מ-`.agents/roles/<role>.md` ו-`docs/ai-team/PROJECT_ASSIGNMENTS.md`, ומבצע בעצמו את העבודה בסשן הראשי. מתועד ב-Asana כ-`[<Role> | <Specialty>] [MAIN_SESSION]`. אין להפעיל סוכן משנה אמיתי דרך כלי שיתוף הפעולה של הפלטפורמה.
- **מצב TEAM (הפעלת סוכני משנה — רק לפי בקשה מפורשת):**
  מופעל אך ורק כשהמשתמש מבקש זאת במפורש ("עבוד במצב צוות" / "הפעל סוכני משנה"). הסוכן הראשי מתאם ומפעיל סוכני משנה דרך כלי ההאצלה המקוריים של הפלטפורמה (`spawn_agent` וכלי שיתוף הפעולה הנתמכים ב-Codex; `invoke_subagent` ב-Antigravity כאשר הוא זמין). מתועד כ-`[<Role> | <Specialty>] [SUBAGENT]`.

### Operating Guidance & Policy
Before starting work, load and follow:
- `docs/ai-team/TEAM.md` — Shared team contract and execution policy
- `docs/ai-team/PROJECT_ASSIGNMENTS.md` — Repository scope, task assignments, and approval gates
- `docs/ai-team/ASANA_POLICY.md` — Authorized evidence-based task coordination and execution modes
- `.agents/roles/<role>.md` — Role-specific scope and handoff rules

Preserve all existing repository policies, frozen components, and explicit owner release gates.
