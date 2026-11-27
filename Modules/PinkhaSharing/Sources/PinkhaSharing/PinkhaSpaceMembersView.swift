import Foundation
import Observation
#if canImport(SwiftUI)
import SwiftUI
#endif

@MainActor @Observable
final class PinkhaSharingViewModel {
    let service: any PinkhaSpaceSharingService
    private(set) var state: PinkhaSharingSnapshot?
    private(set) var problem: String?
    private(set) var busy = false
    private var active = false
    private var generation = UUID()
    private var operation: Task<Void, Never>?

    init(service: any PinkhaSpaceSharingService) { self.service = service }

    func observe() async {
        let current = UUID()
        generation = current
        active = true
        defer { if generation == current { close() } }
        while active && generation == current && !Task.isCancelled {
            await refresh()
            do { try await Task.sleep(for: .seconds(5)) }
            catch { return }
        }
    }

    func refresh() async {
        guard active, !busy else { return }
        let current = generation
        busy = true
        defer { if generation == current { busy = false } }
        do {
            let snapshot = try await service.snapshot()
            try Task.checkCancellation()
            guard active, generation == current else { return }
            guard snapshot.scope == service.scope else { throw PinkhaSharingError.invalidResponse }
            state = snapshot
            problem = nil
        } catch {
            guard active, generation == current, !Task.isCancelled else { return }
            problem = "Unable to refresh. Check the connection and try again."
            // Do not keep invitation secrets or grant controls after failed authority readback.
            state = nil
        }
    }

    func apply(_ mutation: PinkhaSharingMutation?) {
        guard active, !busy, let state else { return }
        if let mutation {
            do { try mutation.validate(in: state) }
            catch { problem = "Your permission changed. Refresh this space."; return }
        } else if !state.capabilities.canCreateInvitation { return }
        let current = generation
        busy = true
        operation = Task { [weak self] in
            guard let self else { return }
            defer {
                if self.generation == current { self.busy = false; self.operation = nil }
            }
            do {
                let result: PinkhaSharingSnapshot
                if let mutation { result = try await self.service.apply(mutation) }
                else {
                    _ = try await self.service.createInvitation()
                    result = try await self.service.snapshot()
                }
                try Task.checkCancellation()
                guard self.active, self.generation == current else { return }
                guard result.scope == self.service.scope else { throw PinkhaSharingError.invalidResponse }
                self.state = result
                self.problem = nil
            } catch {
                guard self.active, self.generation == current, !Task.isCancelled else { return }
                self.problem = "The action could not be confirmed. Refresh before trying again."
                self.state = nil
            }
        }
    }

    func close() {
        active = false
        generation = UUID()
        operation?.cancel()
        operation = nil
        busy = false
        state = nil
        problem = nil
    }
}

#if canImport(SwiftUI)
@MainActor
public struct PinkhaSpaceMembersView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var model: PinkhaSharingViewModel
    @State private var proposed: PinkhaSharingMutation?
    @State private var createProposed = false
    @State private var confirming = false

    public init(service: any PinkhaSpaceSharingService) {
        _model = State(initialValue: PinkhaSharingViewModel(service: service))
    }

    public var body: some View {
        NavigationStack {
            List {
                if let problem = model.problem {
                    Section {
                        Text(LocalizedStringKey(problem), bundle: .module)
                            .foregroundStyle(.secondary)
                        Button { Task { await model.refresh() } } label: {
                            Text("Refresh", bundle: .module)
                        }
                    }
                }
                if let state = model.state {
                    Section {
                        ForEach(state.members.filter { $0.status != .joining }) { member in
                            memberRow(member, state: state)
                        }
                    } header: { Text("Members", bundle: .module) }
                    let requests = state.members.filter { $0.status == .joining }
                    if !requests.isEmpty {
                        Section {
                            ForEach(requests) { member in requestRow(member, state: state) }
                        } header: { Text("Requests to join", bundle: .module) }
                    }
                    Section {
                        ForEach(state.invitations) { invitation in
                            VStack(alignment: .leading, spacing: 8) {
                                if let value = invitation.shareValue {
                                    ShareLink(item: value) { Text("Share invitation", bundle: .module) }
                                        .accessibilityIdentifier("pinkha.sharing.shareInvitation")
                                } else {
                                    Text("The invitation is held by another account.", bundle: .module)
                                        .foregroundStyle(.secondary)
                                }
                                if state.capabilities.canRevokeInvitation {
                                    Button(role: .destructive) { propose(.revokeInvitation(id: invitation.id)) } label: {
                                        Text("Revoke invitation", bundle: .module)
                                    }
                                }
                            }
                        }
                        if state.capabilities.canCreateInvitation {
                            Button {
                                proposed = nil
                                createProposed = true
                                confirming = true
                            } label: { Text("Create invitation", bundle: .module) }
                            .accessibilityIdentifier("pinkha.sharing.createInvitation")
                        }
                        if state.invitations.isEmpty && !state.capabilities.canCreateInvitation {
                            Text("There are no invitations to display.", bundle: .module)
                                .foregroundStyle(.secondary)
                        }
                    } header: { Text("Invitations", bundle: .module) }
                    footer: {
                        Text("New members request access. Their role is chosen when the request is approved.", bundle: .module)
                    }
                } else if model.problem == nil {
                    ProgressView()
                }
            }
            .disabled(model.busy)
            .overlay(alignment: .topTrailing) {
                if model.busy { ProgressView().padding() }
            }
            .navigationTitle(Text("Members and invitations", bundle: .module))
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button { dismiss() } label: { Text("Close", bundle: .module) }
                }
            }
            .refreshable { await model.refresh() }
            .alert(Text("Confirm access change", bundle: .module), isPresented: $confirming) {
                Button(role: .cancel) { proposed = nil; createProposed = false } label: {
                    Text("Cancel", bundle: .module)
                }
                Button {
                    if createProposed { model.apply(nil) }
                    else if let proposed { model.apply(proposed) }
                    proposed = nil
                    createProposed = false
                } label: { Text("Confirm", bundle: .module) }
            } message: {
                confirmationText
            }
            .task { await model.observe() }
            .onDisappear { model.close() }
        }
        .accessibilityIdentifier("pinkha.sharing.members")
    }

    private func memberRow(_ member: PinkhaSharingMember, state: PinkhaSharingSnapshot) -> some View {
        HStack {
            VStack(alignment: .leading) {
                Text(member.name.isEmpty ? member.id : member.name)
                    .textSelection(.enabled)
                HStack {
                    Text(LocalizedStringKey(member.role.rawValue), bundle: .module)
                    if member.status != .active {
                        Text(LocalizedStringKey(member.status.rawValue), bundle: .module)
                    }
                    if member.id == state.currentIdentity { Text("You", bundle: .module) }
                }
                .font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            if state.capabilities.editableMemberIDs.contains(member.id)
                || state.capabilities.removableMemberIDs.contains(member.id) {
                Menu {
                    if state.capabilities.editableMemberIDs.contains(member.id) {
                        ForEach(state.capabilities.grantableRoles.filter { $0 != member.role }, id: \.rawValue) { role in
                            Button { propose(.changeRole(identity: member.id, role: role)) } label: {
                                Text(LocalizedStringKey(role.rawValue), bundle: .module)
                            }
                        }
                    }
                    if state.capabilities.removableMemberIDs.contains(member.id) {
                        Button(role: .destructive) { propose(.remove(identity: member.id)) } label: {
                            Text("Remove member", bundle: .module)
                        }
                    }
                } label: { Image(systemName: "ellipsis.circle") }
                .accessibilityLabel(Text("Change access", bundle: .module))
            }
        }
    }

    private func requestRow(_ member: PinkhaSharingMember, state: PinkhaSharingSnapshot) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(member.name.isEmpty ? member.id : member.name)
            if state.capabilities.canApproveRequests, let requestID = member.requestID {
                HStack {
                    Menu {
                        ForEach(state.capabilities.grantableRoles, id: \.rawValue) { role in
                            Button { propose(.approve(identity: member.id, requestID: requestID, role: role)) } label: {
                                Text(LocalizedStringKey(role.rawValue), bundle: .module)
                            }
                        }
                    } label: { Text("Approve as", bundle: .module) }
                    Button(role: .destructive) { propose(.decline(identity: member.id)) } label: {
                        Text("Decline", bundle: .module)
                    }
                }
            }
        }
    }

    private var confirmationText: Text {
        if createProposed {
            return Text("Create an invitation that allows someone to request access to this space?", bundle: .module)
        }
        func name(_ identity: String) -> String {
            let member = model.state?.members.first { $0.id == identity }
            return member?.name.isEmpty == false ? member!.name : identity
        }
        func role(_ value: PinkhaSharingRole) -> String {
            NSLocalizedString(value.rawValue, bundle: .module, comment: "Membership role")
        }
        switch proposed {
        case let .approve(identity, _, value):
            return Text("Allow \(name(identity)) to join as \(role(value))?", bundle: .module)
        case let .changeRole(identity, value):
            return Text("Change the role of \(name(identity)) to \(role(value))?", bundle: .module)
        case let .remove(identity):
            return Text("Remove \(name(identity)) from this space?", bundle: .module)
        case let .decline(identity):
            return Text("Decline the request from \(name(identity))?", bundle: .module)
        case .revokeInvitation:
            return Text("Revoke this invitation? It will no longer allow requests to join.", bundle: .module)
        case nil:
            return Text("Refresh this space before changing access.", bundle: .module)
        }
    }

    private func propose(_ mutation: PinkhaSharingMutation) {
        proposed = mutation
        createProposed = false
        confirming = true
    }
}

@MainActor
public struct PinkhaJoinSpaceView: View {
    @Environment(\.dismiss) private var dismiss
    private let join: @MainActor @Sendable (String) async throws -> PinkhaSharingJoinResult
    private let joined: @MainActor @Sendable (PinkhaSharingJoinResult) -> Void
    @State private var invitation = ""
    @State private var result: PinkhaSharingJoinResult?
    @State private var failed = false
    @State private var work: Task<Void, Never>?
    @State private var generation = UUID()

    public init(join: @escaping @MainActor @Sendable (String) async throws -> PinkhaSharingJoinResult,
                joined: @escaping @MainActor @Sendable (PinkhaSharingJoinResult) -> Void = { _ in }) {
        self.join = join
        self.joined = joined
    }

    public var body: some View {
        NavigationStack {
            Form {
                if let result {
                    switch result.status {
                    case .active: Text("You have joined the space.", bundle: .module)
                    case .awaitingApproval: Text("Your request was sent. Waiting for approval.", bundle: .module)
                    case .loading: Text("The space is loading. Refresh the space list to continue.", bundle: .module)
                    }
                } else {
                    Section {
                        TextField(text: $invitation, axis: .vertical) {
                            Text("Invitation", bundle: .module)
                        }
                        .autocorrectionDisabled()
                        .accessibilityIdentifier("pinkha.sharing.invitationInput")
                        Button(action: submit) { Text("Request to join", bundle: .module) }
                            .disabled(work != nil || invitation.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                            .accessibilityIdentifier("pinkha.sharing.join")
                        if work != nil { ProgressView() }
                        if failed {
                            Text("The request could not be confirmed. Check the space list before trying again.", bundle: .module)
                        }
                    }
                }
            }
            .navigationTitle(Text("Join a space", bundle: .module))
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button { dismiss() } label: { Text("Close", bundle: .module) }
                }
            }
            .onDisappear {
                generation = UUID()
                work?.cancel()
                work = nil
                invitation = ""
            }
        }
    }

    private func submit() {
        guard work == nil else { return }
        let current = generation, value = invitation
        failed = false
        work = Task {
            defer { if generation == current { work = nil } }
            do {
                let response = try await join(value)
                try Task.checkCancellation()
                guard generation == current else { return }
                invitation = ""
                result = response
                joined(response)
            } catch {
                guard generation == current, !Task.isCancelled else { return }
                failed = true
            }
        }
    }
}
#endif
