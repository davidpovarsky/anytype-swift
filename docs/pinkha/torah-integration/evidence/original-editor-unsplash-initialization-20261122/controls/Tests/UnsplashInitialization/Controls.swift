import Foundation
import Testing

@MainActor
private func waitForInitialization(_ condition: @MainActor () -> Bool) async throws {
    for _ in 0..<100_000 {
        if condition() { return }
        await Task.yield()
    }
    throw InitializationProbeFailure.timeout
}

@Suite(.serialized)
struct UnsplashInitializationBoundary {
    @Test @MainActor
    func exactInitializerRetainsInjectedIdentityOwnerCallbackAndNilLegacy() async throws {
        let service = ServiceProbe()
        ProbeRegistry.service.value = service
        ProbeRegistry.resolutions.value = 0
        let owner = EditorDocumentWriteOwner(identity: "owner-A")
        let selected = AtomicBox<[UnsplashItem]>([])
        let callbackAdmissionCounts = AtomicBox<[Int]>([])
        let model = UnsplashViewModel(onItemSelect: { item in
            selected.access { $0.append(item) }
            callbackAdmissionCounts.access { $0.append(owner.synchronousChecks) }
        }, documentWriteOwner: owner)
        #expect(model.initializationProbeOwner === owner)
        #expect((model.initializationProbeService as? ServiceProbe) === service)
        #expect(ProbeRegistry.resolutions.value == 1)
        #expect(selected.value.isEmpty)
        try await waitForInitialization { service.queries.value == [""] && !model.isLoading }
        #expect(owner.readNames == [["UnsplashSearch"]])
        guard let url = URL(string: "https://example.invalid/initialization-probe") else {
            throw InitializationProbeFailure.missingURL
        }
        let item = UnsplashItem(id: "item-A", url: url, artistName: "Artist", artistURL: url)
        let previousChecks = owner.synchronousChecks
        model.didSelectItem(item: UnsplashItemViewModel(item: item))
        #expect(selected.value.count == 1)
        #expect(selected.value.first?.id == item.id)
        #expect(selected.value.first?.url == item.url)
        #expect(selected.value.first?.artistName == item.artistName)
        #expect(selected.value.first?.artistURL == item.artistURL)
        #expect(callbackAdmissionCounts.value == [previousChecks + 1])
        let legacySelected = AtomicBox<[String]>([])
        let legacy = UnsplashViewModel(onItemSelect: { item in legacySelected.access { $0.append(item.id) } })
        #expect(legacy.initializationProbeOwner === nil)
        #expect((legacy.initializationProbeService as? ServiceProbe) === service)
        #expect(ProbeRegistry.resolutions.value == 2)
        try await waitForInitialization { service.queries.value.count == 2 && !legacy.isLoading }
        #expect(service.queries.value == ["", ""])
        #expect(owner.readNames == [["UnsplashSearch"]])
        legacy.didSelectItem(item: UnsplashItemViewModel(item: item))
        #expect(legacySelected.value == ["item-A"])
        #expect(selected.value.count == 1)
    }
}
