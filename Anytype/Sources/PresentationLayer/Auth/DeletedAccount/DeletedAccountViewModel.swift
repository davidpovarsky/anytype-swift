import UIKit

@MainActor
@Observable
final class DeletedAccountViewModel {

    @ObservationIgnored @Injected(\.authService)
    private var service: any AuthServiceProtocol
    @ObservationIgnored
    private let deadline: Date
    @ObservationIgnored
    private let originalEditorCaller: OriginalEditorAuthCaller?

    private var originalAuthService: any AuthServiceProtocol {
        if let originalEditorCaller { return originalEditorCaller }
        return service
    }
    private var acceptsOriginalUI: Bool { originalEditorCaller?.isCurrent ?? true }

    @ObservationIgnored @Injected(\.applicationStateService)
    private var applicationStateService: any ApplicationStateServiceProtocol
    
    // MARK: - Initializer
    
    init(deadline: Date, originalEditorCaller: OriginalEditorAuthCaller? = nil) {
        self.deadline = deadline
        self.originalEditorCaller = originalEditorCaller
    }
    
    // MARK: - Internal var
    
    var deletionProgress: CGFloat {
        let daysToDeletion = CGFloat(daysToDeletion)
        let maxDaysDeadline = CGFloat(Constants.maxDaysDeadline)
        let progress: CGFloat = (daysToDeletion / maxDaysDeadline).clamped(0.1, 0.9)
        return 1.0 - progress
    }
    
    var title: String {
        return Loc.daysToDeletionVault(daysToDeletion)
    }
    
    // MARK: - Internal funcs
    
    func logOut() {
        guard acceptsOriginalUI else { return }
        AnytypeAnalytics.instance().logLogout(route: .screenDeletion)
        Task {
            do {
                try await OriginalEditorAuthCaller.withUIOperation(originalEditorCaller) {
                    try await originalAuthService.logout(removeData: true)
                    try originalEditorCaller?.validateCurrent()
                    applicationStateService.state = .auth
                }
            } catch {
                if acceptsOriginalUI { UINotificationFeedbackGenerator().notificationOccurred(.error) }
            }
        }
    }
    
    func cancel() {
        guard acceptsOriginalUI else { return }
        AnytypeAnalytics.instance().logCancelDeletion()
        Task { @MainActor in
            do {
                try await OriginalEditorAuthCaller.withUIOperation(originalEditorCaller) {
                    let status = try await originalAuthService.restoreAccount()
                    try originalEditorCaller?.validateCurrent()
                    if case .active = status {
                        applicationStateService.state = .home
                    } else {
                        UINotificationFeedbackGenerator().notificationOccurred(.error)
                        return
                    }
                }
            } catch {
                if acceptsOriginalUI { UINotificationFeedbackGenerator().notificationOccurred(.error) }
            }
        }
    }
    
    // MARK: - Private vars
    
    private var daysToDeletion: Int {
        Calendar.current
            .numberOfDaysBetween(Date(), and: deadline)
            .clamped(0, Constants.maxDaysDeadline)
    }
}

// MARK: - Constants

private extension DeletedAccountViewModel {
    
    enum Constants {
        static let maxDaysDeadline: Int = 30
    }
    
}
