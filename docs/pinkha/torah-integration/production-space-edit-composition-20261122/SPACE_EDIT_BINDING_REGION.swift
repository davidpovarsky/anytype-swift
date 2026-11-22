    private init(restricting original: Self, additionalCaptures: [EditorDocumentWriteCapture]) {
        lifetime = original.lifetime
        captures = original.captures + additionalCaptures
        accountCapture = original.accountCapture
        parentOwner = original.parentOwner
        rpcRestriction = original.rpcRestriction
        isCurrent = original.isCurrent
    }

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

