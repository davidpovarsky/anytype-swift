import Foundation
import Services

struct ObjectPermissions: Equatable {
    var canChangeType: Bool = false
    var canDelete: Bool = false
    var canRestore: Bool = false
    var canTemplateSetAsDefault: Bool = false
    var canArchive: Bool = false
    var canDuplicate: Bool = false
    var canUndoRedo: Bool = false
    var canMakeAsTemplate: Bool = false
    var canFavorite: Bool = false
    var canLinkItself: Bool = false
    var canLock: Bool = false
    var canChangeIcon: Bool = false
    var canChangeCover: Bool = false
    var canChangeLayout: Bool = false
    var canEditRelationValues: Bool = false
    var canEditPropertiesList: Bool = false
    var canApplyTemplates: Bool = false
    var canShare: Bool = false
    var canPublish: Bool = false
    var canEditBlocks: Bool = false
    var canEditMessages: Bool = false
    var canRestoreVersionHistory: Bool = false
    var canEditDetails: Bool = false
    var canShowRelations: Bool = false
    var canToggleDescription: Bool = false
    var canApplyUneditableActions: Bool = false
    var editBlocks: EditBlocksPermission = .readonly(.restrictions)
}

