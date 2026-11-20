import Services

@MainActor
struct ObjectHeaderViewModelDependencies {
    let objectHeaderUploadingService: any ObjectHeaderUploadingServiceProtocol

    static func original() -> Self {
        Self(
            objectHeaderUploadingService: Container.shared.objectHeaderUploadingService()
        )
    }
}
