# Pinkha on Anytype — Data Model Specification

## 1. Object Types

Pinkha registers and utilizes native Anytype Object Types:

| Logical Type | Localized Name | Purpose | Anytype Representation |
|--------------|----------------|---------|------------------------|
| `pinkha.folder` | תיקייה | Organizational navigation folder | Custom Object Type |
| `pinkha.bookFolder` | תיקיית ספרים | Hierarchy folder containing Books | Custom Object Type |
| `pinkha.chiddush` | חידוש | Torah innovation / insight document | Custom Object Type (with default template) |
| `pinkha.article` | מאמר | Structured essay / article | Custom Object Type (with default template) |
| `pinkha.research` | מחקר | Structured in-depth Torah research | Custom Object Type (with default template) |

## 2. Properties (Relations)

Logical roles are mapped to concrete Anytype Property IDs in `PinkhaSpaceManifest`:

| Logical Role | Target Anytype Format | Description |
|--------------|-----------------------|-------------|
| `pinkha.parent` | `.object` | Points to navigation parent (Folder or Document) |
| `pinkha.order` | `.number` | Sparse numeric rank for deterministic sibling ordering |
| `pinkha.torahAssociations` | `.text` (JSON payload) | Document-level Torah context associations |

### Hierarchy Domain Representation (`Modules/PinkhaKit`)

- **`PinkhaHierarchyNode`**: Domain node with `objectId`, `typeId`, `title`, `parentId?`, `order?`, `kind: .folder | .writingDocument`, and `children: [PinkhaHierarchyNode]`.
- **Root Semantics**: An object with no parent relation (`parentId == nil`) is a root node.
- **Order Semantics**: Dense threshold `< 0.001`; default step `1000.0`; unranked items deterministically placed after ranked items, ordered by title, then objectId.
- **`PinkhaReparentPlan`**: Result of `PinkhaHierarchyOrdering.planSafeFolderDeletion(targetFolderId:in:)`, specifying target folder deletion, target parent ID, and child updates with new parent ID and non-colliding order ranks.
- **`PinkhaHierarchyReconciler`**: Pure domain state reconciler in `Modules/PinkhaKit` managing optimistic state:
  - `registerPending(item:)`: Optimistically inserts a pending item and rebuilds snapshot.
  - `receiveSubscription(items:)`: Merges pending unconfirmed items with incoming subscription items, clears confirmed items, deduplicates IDs strictly, and rebuilds snapshot.
  - `rename(objectId:newName:)`: Optimistic title update.
  - `updateOrder(objectId:newRank:)`: Optimistic sparse rank update.
  - `move(objectId:newParentId:newRank:)`: Optimistic reparenting and rank update.
  - `delete(objectId:)`: Optimistic deletion of node and unregisters any pending creations.
- **`PinkhaHierarchySnapshot` Path Helpers**:
  - `ancestorPath(for objectId: String) -> [PinkhaHierarchyNode]`
  - `fullNodePath(for objectId: String) -> [PinkhaHierarchyNode]`
  - `pathString(for objectId: String, separator: String) -> String`
  - `parentPathString(for objectId: String, separator: String) -> String?`
- **Query Scale**: Native unbounded query limit (`limit: 0`) used across search and subscription builders.


## 3. Block Fields

Custom block-level Pinkha data is stored in `BlockInformation.fields`:

| Field Key | Payload | Description |
|-----------|---------|-------------|
| `pinkha.torah.associations.v1` | JSON (`items[]`) | Block-level Torah references, topics, and words |
| `pinkha.torah.sourceQuote.v1` | JSON (`providerID`, `reference`, `labelHe`, `readOnly`) | Metadata converting a Quote block into a Torah Source |
| `pinkha.textDirection.v1` | String (`"auto"`, `"rtl"`, `"ltr"`) | Explicit or auto-detected text direction |
