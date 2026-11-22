    // ORIGINAL_SPACE_EDIT_BINDING_BEGIN
    private init(restricting original: Self, additionalCaptures: [EditorDocumentWriteCapture]) {
        lifetime = original.lifetime
        captures = original.captures + additionalCaptures
        accountCapture = original.accountCapture
        parentOwner = original.parentOwner
        rpcRestriction = original.rpcRestriction
        isCurrent = original.isCurrent
    }

    /// Adds the original participant and SpaceView permission generations to an
    /// already bound source. This does not select a destination or grant creation.
    /// No source/account/role/view lifetime is recaptured or replaced.
    func requiringSpaceEditPermission(
        participant: OriginalParticipantEditPermission,
        spaceView: OriginalSpaceViewPermission,
        spaceId: String
    ) throws -> Self {
        try validate()
        guard let accountCapture else {
            throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
        }
        let participantCapture = try participant.capture(matching: accountCapture, spaceId: spaceId)
        let viewCapture = try spaceView.capture(matching: accountCapture, spaceId: spaceId)
        let permissions = SpacePermissions(
            spaceView: spaceView.originalSpaceView,
            participant: participant.originalParticipant,
            isLocalMode: Container.shared.serverConfigurationStorage().currentConfiguration().middlewareNetworkMode == .localOnly
        )
        guard permissions.canEdit else {
            throw EditorDocumentWriteError.rejected(.notEditable)
        }
        let restricted = Self(
            restricting: self, additionalCaptures: [participantCapture, viewCapture]
        )
        try restricted.validate()
        return restricted
    }
    // ORIGINAL_SPACE_EDIT_BINDING_END

