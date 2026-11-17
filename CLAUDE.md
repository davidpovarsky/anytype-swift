# Anytype iOS App

Privacy-focused, local-first workspace for iOS. Swift + SwiftUI + Custom Middleware (Protobuf).

## ⚠️ CRITICAL RULES - NEVER VIOLATE
1. **Apply the standing owner authorization below; routine task-scoped staging and commits are already authorized.**
2. **NEVER add AI signatures in code**
3. **Preserve existing worktrees, branches and uncommitted work; use scoped changes and isolated branches.**
4. **Communicate meaningful progress while completing multi-step work autonomously.**

## Standing owner authorization — 2026-11-18

The repository owner explicitly grants durable authorization, until revoked, for agents to complete requested project work autonomously. This authorization persists across sessions.

Within the requested task, this includes source and configuration edits; local and remote commands; dependency preparation; compilation and builds; unit, native, simulator, device and CI tests; `git add`, `git commit`, `git push` and branch integration; artifact uploads; and deployment of the task's deliverables to the project's intended destinations. Do not request the same permission again at each step.

This standing authorization supersedes older repository-local requirements for per-step, per-file, commit, build, upload or release approval, including inherited approval wording in team and architecture documents. It does not by itself request an unrelated release or expand the current task. Preserve existing worktrees, other people's work, credentials and user data; keep source provenance and acceptance evidence accurate.

This file records the owner's consent. It cannot change platform, system, service or tool access controls. If an external control rejects an action, report the actual rejection and use an authorized supported path; do not bypass it.

For the 15 November Pinkha wave, the explicit Git scope is the isolated `codex/chatgpt-wave15-*` branches of Anytype and TorahInspectorKit. Execute through the main ChatGPT agent and its direct agents, without recreating the historical Codex Desktop team. Update Asana after meaningful completed stages, with exact source revisions and actual evidence; keep unmet acceptance tasks open.

## 🚀 Quick Start
```bash
make setup-env && make setup-middle  # First time
make generate                                             # After any asset/flag/localization change
```
**Requirements**: Xcode 16.1+, Swift Package Manager
**Compilation**: Agents run the appropriate available build and test tools, reuse compatible caches, and report actual results and source revisions. A user's manual Xcode run is not a prerequisite.

## 📚 Knowledge Map

This file is a **table of contents**, not an encyclopedia. Deeper docs live in-repo.

### Architecture & Patterns
| Topic | Location |
|-------|----------|
| MVVM, Coordinator, DI, code style | `Anytype/Sources/IOS_DEVELOPMENT_GUIDE.md` |
| Taste invariants (mechanical rules) | `TASTE_INVARIANTS.md` |

### Design System
| Topic | Location |
|-------|----------|
| Colors, typography, icons, spacing | `Anytype/Sources/PresentationLayer/Common/DESIGN_SYSTEM_MAPPING.md` |
| Typography reference | `Anytype/Sources/PresentationLayer/Common/TYPOGRAPHY_MAPPING.md` |

### Localization
| Topic | Location |
|-------|----------|
| Full guide | `Anytype/Sources/PresentationLayer/Common/LOCALIZATION_GUIDE.md` |
| Quick search | `rg "term" Modules/Loc/Sources/Loc/Generated/Strings.swift` |

### Code Generation
| Topic | Location |
|-------|----------|
| Feature flags, SwiftGen, Sourcery | `Modules/AnytypeCore/CODE_GENERATION_GUIDE.md` |
| Feature flags source | `Modules/AnytypeCore/.../FeatureDescription+Flags.swift` |

### Code Review & Quality
| Topic | Location |
|-------|----------|
| Review guidelines | `.claude/CODE_REVIEW_GUIDE.md` |
| Self-review checklist | `.claude/skills/self-review/SKILL.md` |
| CI workflows | `.github/WORKFLOWS_REFERENCE.md` |

### Skills (Auto-Activate)

| Skill | Triggers On |
|-------|-------------|
| `ios-dev-guidelines` | `.swift` files, architecture |
| `localization-developer` | Localization work |
| `design-system-developer` | UI/design work |
| `code-generation-developer` | Code generation |
| `code-review-developer` | PR reviews |
| `self-review` | Post-implementation quality check |
| `confidence-check` | Implementation tasks |
| `linear-developer` | Linear issues/CLI |
| `ios-simulator-skill` | Simulator/build/test |
| `swift-concurrency-developer` | Concurrency/actors |
| `swiftui-patterns-developer` | View structure |
| `swiftui-performance-developer` | Performance issues |
| `liquid-glass-developer` | iOS 26 glass effects |
| `analytics-developer` | Analytics events |
| `feature-toggle-developer` | Feature flags |
| `tests-developer` | Unit tests, mocks |
| `apple-docs-developer` | Apple API lookup |
| `decompose` | Task breakdown, subtasks |

## 🔎 Implementation review
Use these checks to improve correctness; they are not a user-approval gate:
```
[ ] No duplicates found (25%)    [ ] Follows MVVM/Coordinator/DI (25%)
[ ] Verified existing code (20%) [ ] Uses Loc/Color/Image system (15%)
[ ] Root cause understood (15%)  → Investigate concrete uncertainty and proceed when the change is supported.
```

## 🏗️ Project Structure
```
Anytype/Sources/
├── ApplicationLayer/    # App lifecycle, coordinators
├── PresentationLayer/   # UI components, ViewModels
├── ServiceLayer/        # Business logic, data services
└── Models/              # Data models, entities
Modules/                 # Swift packages (AnytypeCore, Loc, Assets, Services)
```

## 🔄 Git Workflow

### Task-Based Branching
**First thing when starting any task**:
1. Fetch Linear issue: `linctl issue get IOS-XXXX --json`
2. Extract `gitBranchName` field: `| jq -r '.gitBranchName'`
3. Switch immediately: `git checkout <branch-name>`

**linctl reference**: `.claude/skills/linear-developer/SKILL.md` | https://github.com/dorkitude/linctl

### Branches & PRs
- **Main branch**: `develop`
- **Feature branches**: `ios-XXXX-description`
- **Commit messages**: Single line
- **Commit tone**: Direct, technical, no buzzwords. Focus on what changed and why.
- **PR format**: `## Summary` + 1-3 bullet points (no test plan needed)
- **Release branches**: Target release branch in PR, add "Release" label

### GitHub CLI
```bash
gh pr view <PR_NUMBER> --repo anyproto/anytype-swift
gh pr diff <PR_NUMBER> --repo anyproto/anytype-swift
```

**Workflows documentation**: `.github/WORKFLOWS_REFERENCE.md`

### Linear Integration
- Extract task ID from user request or branch name
- Use `gh` tool for related PRs
- Update progress with Linear MCP tools

## 📋 Tips
- For trivial visual/cosmetic PRs only (color changes, spacing tweaks, copy updates), add label "🧠 No brainer". Never use for logic, caching, data flow, or bug fixes.
- Use `rg` for searching large files
- Feature flags for all new features
- `Loc` is pre-imported; import `AnytypeCore` for feature flags
- When stuck after 2-3 attempts, step back and try a different approach

## ⚠️ Common Mistakes
- **Scoped Committing**: Commit only the requested task's reviewed changes under the standing owner authorization.
- **Wildcard Deletion**: Always `ls` first, delete individually
- **Incomplete Mock Updates**: `rg "oldName" --type swift` → update ALL references
- **Over-Engineering**: Three similar lines > premature abstraction
- **Guessing Before Reading**: Always read the file before suggesting changes

## 💡 Quick Reference
- `Loc` is pre-imported; import `AnytypeCore` for feature flags
- Icons: `Image(asset: .X32.qrCode)`, `Image(asset: .X24.search)`
- Colors: `Color.Text.primary`, `Color.Shape.transparentSecondary`
- When stuck after 2-3 attempts, step back and try a different approach

## Living Project Board

`PROJECT_BOARD.md` is this repository's shared living project board. Before starting substantial work, scan it for relevant context. During normal work, agents should proactively add concise, actionable entries when they discover something with genuine future value, including:

- useful technical discoveries
- optimization opportunities
- implementation tricks
- architectural ideas
- possible future improvements
- experiments worth running
- unresolved issues or questions
- follow-up work that should not be lost

Do this proactively even when the discovery is incidental to the current task. Do not add trivial observations, temporary debugging chatter, information already documented elsewhere, generic suggestions with no project relevance, or every step performed during a task. The board supports memory but is not a source of truth when repository code, documentation, or current state contradicts it.

When an item is implemented, mark it complete and optionally record the date and commit/PR, moving it to `Done` when useful. Delete or archive obsolete entries when appropriate.

Updating `PROJECT_BOARD.md` as a side effect of another task is allowed and encouraged when a worthwhile discovery is made. Recording an idea is allowed; implementing unrelated ideas is not.

Preserve all existing repository-specific instructions.

## Upstream integrity and evidence

Read `docs/architecture/UPSTREAM_INTEGRITY_POLICY.md` for architectural context. Prefer isolated Pinkha adapters, wrappers, protocols and packages, and preserve the canonical Hanlin engine. Make only source changes required by the requested task and record their exact provenance. The standing owner authorization above replaces older per-file and Git approval requirements. Successful compilation alone does not prove functional parity. Asana updates for the current wave are explicitly authorized and required.
