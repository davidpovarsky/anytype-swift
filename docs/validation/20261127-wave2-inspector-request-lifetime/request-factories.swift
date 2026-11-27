    // Capture while the button callback or view body still owns this picker.
    // The returned operation is awaited directly, preserving caller cancellation.
    public func makeSearchRequest(debounce: Duration = .zero) -> @MainActor () async -> Void {
        let generation = presentationGeneration
        return { [weak self] in
            guard let self, self.ownsPresentation(generation) else { return }
            await self.performSearch(debounce: debounce)
        }
    }

    public func makeAssociationRefreshRequest() -> @MainActor () async -> Void {
        let generation = presentationGeneration
        return { [weak self] in
            guard let self, self.ownsPresentation(generation) else { return }
            await self.refreshAssociations()
        }
    }

    public func makeOpenReferenceRequest(_ result: SearchResult) -> @MainActor () async -> Void {
        let generation = presentationGeneration
        return { [weak self] in
            guard let self, self.ownsPresentation(generation) else { return }
            await self.openReference(result)
        }
    }

    public func makeLinkRequest(_ result: SearchResult) -> @MainActor () async -> Void {
        let generation = presentationGeneration
        return { [weak self] in
            guard let self, self.ownsPresentation(generation) else { return }
            await self.link(result)
        }
    }

    public func makeUnlinkRequest(_ item: TorahAssociationItem) -> @MainActor () async -> Void {
        let generation = presentationGeneration
        return { [weak self] in
            guard let self, self.ownsPresentation(generation) else { return }
            await self.unlinkAssociation(item)
        }
    }

    private func ownsPresentation(_ generation: UUID) -> Bool {
        presentationGeneration == generation && !Task.isCancelled
    }

