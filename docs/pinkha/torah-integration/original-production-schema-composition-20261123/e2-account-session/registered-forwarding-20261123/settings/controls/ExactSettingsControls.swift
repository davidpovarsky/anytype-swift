import Foundation
enum Loc { static let error = "fixture error" }
enum ToastKind { case failure }
struct ToastBarData { let value: String; let kind: ToastKind; init(_ value: String, type: ToastKind) { self.value=value;kind=type } }
enum AnalyticsNetworkType { case anytype, localOnly, selfHost }
enum AnalyticsRoute { case onboarding }
enum NetworkServerConfig: Equatable {
    case anytype, localOnly, file(String)
    var isLocalOnly: Bool { self == .localOnly }
    var title: String { String(reflecting: self) }
    var analyticsType: AnalyticsNetworkType {
        switch self { case .anytype:return .anytype;case .localOnly:return .localOnly;case .file:return .selfHost }
    }
}
@MainActor
final class AnytypeAnalytics {
    static let value = AnytypeAnalytics()
    static func instance() -> AnytypeAnalytics { value }
    var uploads=0, selections=0
    func logUploadNetworkConfiguration() { uploads+=1 }
    func logSelectNetwork(type: AnalyticsNetworkType, route: AnalyticsRoute) { selections+=1 }
    func reset() { uploads=0; selections=0 }
}
@MainActor
final class StorageBoundary {
    var installs=0, completed=0, setups=0
    var fail=false
    var configuration=NetworkServerConfig.anytype
    var duringInstall: (() -> Void)?
    func addConfiguration(filePath: URL, setupAsCurrent: Bool) throws {
        installs+=1
        duringInstall?()
        if fail { throw TestError.synthetic }
        completed+=1
        if setupAsCurrent { configuration = .file("fixture") }
    }
    func setupCurrentConfiguration(config: NetworkServerConfig) { setups+=1; configuration=config }
    func installedConfigurations() -> [NetworkServerConfig] { [.file("fixture")] }
    func currentConfiguration() -> NetworkServerConfig { configuration }
}
@MainActor
protocol ServerConfigurationModuleOutput: AnyObject { func onAddServerSelected() }
@MainActor
final class OutputBoundary: ServerConfigurationModuleOutput {
    var count=0
    func onAddServerSelected() { count+=1 }
}
struct ServerConfigurationRow { let title: String; let isSelected: Bool; let onTap: () -> Void }

@MainActor
final class ExactDocumentPickerMethod {
    private let storage: StorageBoundary
    private let originalEditorCaller: OriginalEditorAuthCaller?
    var toast: ToastBarData?
    init(_ storage: StorageBoundary, caller: OriginalEditorAuthCaller?) {
        self.storage=storage;originalEditorCaller=caller
    }
    func onSelectFile(url: URL) {
        do {
            // The original storage operation is synchronous. Keep its real
            // scoped file-copy/configuration/publisher effects within this lease.
            try OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
                try storage.addConfiguration(filePath: url, setupAsCurrent: true)
                AnytypeAnalytics.instance().logUploadNetworkConfiguration()
                AnytypeAnalytics.instance().logSelectNetwork(type: .selfHost, route: .onboarding)
            }
        } catch {
            guard originalEditorCaller?.isCurrent ?? true else { return }
            toast = ToastBarData(Loc.error, type: .failure)
        }
    }
}

@MainActor
final class ExactConfigurationMethods {
    private let storage: StorageBoundary
    private let originalEditorCaller: OriginalEditorAuthCaller?
    private weak var output: (any ServerConfigurationModuleOutput)?
    var mainRows: [ServerConfigurationRow] = []
    var rows: [ServerConfigurationRow] = []
    var showLocalConfigurationAlert = false
    init(_ storage: StorageBoundary, caller: OriginalEditorAuthCaller?, output: (any ServerConfigurationModuleOutput)?) {
        self.storage=storage;originalEditorCaller=caller;self.output=output
    }
    func onTapAddServer() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            output?.onAddServerSelected()
        
        }
    }

    func setup(config: NetworkServerConfig) {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            storage.setupCurrentConfiguration(config: config)
            updateRows()
            AnytypeAnalytics.instance().logSelectNetwork(type: config.analyticsType, route: .onboarding)
        
        }
    }

    private func updateRows() {
        mainRows = [makeRow(config: .anytype), makeRow(config: .localOnly)]
        rows = storage.installedConfigurations().map { config in
            makeRow(config: config)
        }
    }

    private func makeRow(config: NetworkServerConfig) -> ServerConfigurationRow {
        ServerConfigurationRow(
            title: config.title,
            isSelected: config == storage.currentConfiguration(),
            onTap: { [weak self] in
                self?.handleOnTap(config: config)
            }
        )
    }

    private func handleOnTap(config: NetworkServerConfig) {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            guard config != storage.currentConfiguration() else { return }
            if config.isLocalOnly {
                showLocalConfigurationAlert.toggle()
            } else {
                setup(config: config)
            }
        
        }
    }
}

@main
struct SettingsControls {
    @MainActor static func main() async {
        do {
            let url=URL(fileURLWithPath:"/owned-fixture.yaml")
            do {
                AnytypeAnalytics.instance().reset()
                let storage=StorageBoundary()
                let model=ExactDocumentPickerMethod(storage, caller:nil)
                model.onSelectFile(url:url)
                try Check.that(storage.installs==1 && storage.completed==1, "nil caller retains exact original synchronous install")
                try Check.that(AnytypeAnalytics.instance().uploads==1 && AnytypeAnalytics.instance().selections==1, "nil analytics sequence retained")
                storage.fail=true
                model.onSelectFile(url:url)
                try Check.that(storage.installs==2 && storage.completed==1 && model.toast != nil, "nil original install error path preserved")
                try Check.that(AnytypeAnalytics.instance().uploads==1, "failed original install does not log success")
                Check.pass("exact_picker_standalone_success_and_error")
            }
            do {
                AnytypeAnalytics.instance().reset()
                let service=PinkhaHanlinAuthService(base:AuthBoundaryDouble())
                let old=try await service.makeOriginalEditorCaller()
                let storage=StorageBoundary()
                let model=ExactDocumentPickerMethod(storage,caller:old)
                _=try await old.closeAuthentication()
                try await old.releaseAfterRuntimeDrain()
                let next=try await service.makeOriginalEditorCaller()
                model.onSelectFile(url:url)
                try Check.that(storage.installs==0 && storage.completed==0, "retired picker cannot borrow later owner")
                try Check.that(model.toast==nil && AnytypeAnalytics.instance().uploads==0, "retired callback has no old UI/analytics continuation")
                _=try await next.closeAuthentication()
                try await next.releaseAfterRuntimeDrain()
                Check.pass("exact_picker_rejects_retired_and_replaced_owner")
            }
            do {
                let service=PinkhaHanlinAuthService(base:AuthBoundaryDouble())
                let caller=try await service.makeOriginalEditorCaller()
                let storage=StorageBoundary()
                storage.duringInstall={ caller.retire() }
                let model=ExactDocumentPickerMethod(storage,caller:caller)
                model.onSelectFile(url:url)
                try Check.that(storage.installs==1 && storage.completed==1, "already admitted synchronous storage call completes honestly")
                try Check.that(model.toast==nil, "retired caller cannot append error UI after historical effect")
                model.onSelectFile(url:url)
                try Check.that(storage.installs==1, "late callback never begins a second install")
                try Check.that(Check.neverStarted(try await caller.closeAuthentication()), "synchronous action completes before drain-only close")
                try await caller.releaseAfterRuntimeDrain()
                Check.pass("exact_picker_preserves_admitted_historical_effect")
            }
            do {
                let service=PinkhaHanlinAuthService(base:AuthBoundaryDouble())
                let caller=try await service.makeOriginalEditorCaller()
                let storage=StorageBoundary(), output=OutputBoundary()
                let model=ExactConfigurationMethods(storage,caller:caller,output:output)
                model.setup(config:.anytype)
                try Check.that(storage.setups==1 && model.mainRows.count==2 && model.rows.count==1, "exact setup and original rows retained")
                let savedRow=model.rows[0]
                model.onTapAddServer()
                try Check.that(output.count==1, "current original coordinator callback retained")
                caller.retire()
                savedRow.onTap()
                model.setup(config:.localOnly)
                model.onTapAddServer()
                try Check.that(storage.setups==1 && storage.configuration == .anytype, "escaped row and local alert setup reject retired caller")
                try Check.that(output.count==1 && !model.showLocalConfigurationAlert, "retired coordinator cannot present picker")
                _=try await caller.closeAuthentication()
                try await caller.releaseAfterRuntimeDrain()
                Check.pass("exact_settings_row_alert_and_coordinator_callbacks")
            }
            let result:[String:Any]=["status":"PASS","controls":Check.passed.count,"assertions":Check.assertions,"passed":Check.passed,"scope":"Exact synchronous source method bodies plus unchanged Foundation owner source; explicit storage/UI boundary doubles; no actual file copy, Combine, UIKit or native credit."]
            print("RESULT_JSON "+String(data:try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]),encoding:.utf8)!)
        } catch {
            print("RESULT_JSON "+String(data:try! JSONSerialization.data(withJSONObject:["status":"FAIL","passed":Check.passed,"assertions":Check.assertions,"error":String(reflecting:error)],options:[.sortedKeys]),encoding:.utf8)!)
            exit(1)
        }
    }
}
