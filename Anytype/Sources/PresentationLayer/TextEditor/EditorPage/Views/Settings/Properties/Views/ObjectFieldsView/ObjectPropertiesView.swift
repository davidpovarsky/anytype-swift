import SwiftUI
import Services
import AnytypeCore
import Loc
import PinkhaKit


struct ObjectPropertiesView: View {

    @State private var model: ObjectPropertiesViewModel
    @State private var torahProperties: PinkhaTorahPropertiesModel?
    private let preparedSession: PreparedEditorPageSession?

    init(document: some BaseDocumentProtocol, output: (any PropertiesListModuleOutput)?, torahSession: TorahEditorSession? = nil,
         preparedSession: PreparedEditorPageSession? = nil) {
        self.preparedSession = preparedSession
        if preparedSession == nil {
            _torahProperties = State(initialValue: PinkhaTorahPropertiesModel(document: document, session: torahSession))
        } else {
            // The original Torah model resolves schema during initialization.
            // The prepared page uses its current-account property reader only.
            _torahProperties = State(initialValue: nil)
        }
        _model = State(initialValue: ObjectPropertiesViewModel(document: document, output: output, preparedSession: preparedSession))
    }

    private var legacyTorahProperties: PinkhaTorahPropertiesModel? {
        // State can outlive a View value. A prepared route must never reuse a
        // previously retained legacy model or its separate Torah session.
        preparedSession == nil ? torahProperties : nil
    }

    private var visibleSections: [PropertiesSection] {
        if let legacyTorahProperties {
            return legacyTorahProperties.visibleSections(model.sections)
        }
        return model.sections
    }
    
    var body: some View {
        content
            .task { await model.setupSubscriptions() }
            .task(id: preparedSession == nil) {
                // This original observer can provision the Space schema. Its
                // separate Torah ownership path is not a page-write admission.
                if let legacyTorahProperties { await legacyTorahProperties.observeDocument() }
            }
            .sheet(item: $model.relationsSearchData) { PropertyCreationView(data: $0) }
            .torahEditorHost(session: legacyTorahProperties?.session, presentationHost: .properties)
            .anytypeSheet(isPresented: $model.showConflictingInfo) {
                ObjectPropertiesBottomAlert()
            }
    }
    
    private var content: some View {
        VStack(spacing: 0) {
            DragIndicator()
            navigationBar
            relationsList
        }
    }
    
    private var navigationBar: some View {
        HStack {            
            Spacer()
            AnytypeText(Loc.fields, style: .uxTitle1Semibold)
                .foregroundStyle(Color.Text.primary)
            Spacer()
        }
        .frame(height: 48)
        .overlay(alignment: .trailing) {
            if model.typeId.isNotNil {
                editButton
            }
        }
        .padding(.horizontal, 16)
    }
    
    private var editButton: some View {
        Button {
            withAnimation(.fastSpring) {
                model.onEditTap()
            }
        } label: {
            IconView(asset: .X24.settings).frame(width: 24, height: 24)
        }
    }
    
    private var relationsList: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                if let legacyTorahProperties, legacyTorahProperties.isResolvingManifest {
                    PinkhaTorahPropertiesLoadingState(model: legacyTorahProperties)
                } else if model.shouldShowEmptyState {
                    emptyStateView
                        .padding(.top, 24)
                }
                
                ForEach(visibleSections) { section in
                    Section {
                        if !section.isExpandable || model.isSectionExpanded(section.id) {
                            ForEach(section.relations) {
                                row(with: $0, section: section)
                            }
                        }
                    } header: {
                        sectionHeader(section: section)
                    }
                }

                if let legacyTorahProperties {
                    PinkhaTorahPropertiesSection(model: legacyTorahProperties)
                }
                if model.canAddProperty {
                    Button {
                        model.onAddPropertyTap()
                    } label: {
                        Text(verbatim: Loc.addProperty)
                            .anytypeStyle(.uxBodyRegular)
                    }
                    .accessibilityIdentifier("torah-object-add-property")
                    .padding(.vertical, 12)
                }
            }
            .padding(.horizontal, 20)
        }
    }
    
    private var emptyStateView: some View {
        AnytypeText(Loc.noPropertiesYet, style: .uxCalloutMedium)
            .foregroundStyle(Color.Text.secondary)
            .multilineTextAlignment(.center)
    }
    
    private func sectionHeader(section: PropertiesSection) -> some View {
        Group {
            if section.isExpandable {
                Button {
                    model.toggleSectionExpansion(section.id)
                } label: {
                    HStack(spacing: 0) {
                        Image(asset: .X18.Disclosure.right)
                            .foregroundStyle(Color.Control.secondary)
                            .rotationEffect(.degrees(model.isSectionExpanded(section.id) ? 90 : 0))
                        
                        AnytypeText(section.title, style: .uxCalloutMedium)
                            .foregroundStyle(Color.Text.secondary)
                            .padding(.leading, 10)
                        
                        if section.isMissingFields {
                            Spacer()
                            Button {
                                model.onConflictingInfoTap()
                            } label: {
                                Image(systemName: "questionmark.circle.fill")
                                    .foregroundStyle(Color.Control.secondary)
                                    .frame(width: 18, height: 18)
                            }
                        } else {
                            Spacer()
                        }
                    }
                    .padding(.vertical, 12)
                }
                .padding(.top, 16)
            } else {
                EmptyView()
            }
        }
    }
    
    private func row(with relation: Property, section: PropertiesSection) -> some View {
        HStack {
            rowWithoutActions(with: relation, addedToObject: section.addedToObject)
            if model.isObjectAttachedNative(relation) {
                Menu {
                    Button(Loc.Fields.removeFromObject, role: .destructive) { model.removeRelation(relation) }
                } label: {
                    MoreIndicator()
                }
            } else if section.isMissingFields {
                Menu {
                    Button(Loc.Fields.addToType) { model.addRelationToType(relation) }
                    if relation.canBeRemovedFromObject {
                        Button(Loc.Fields.removeFromObject, role: .destructive) { model.removeRelation(relation) }
                    }
                } label: {
                    MoreIndicator()
                }
            } else if section.id == PropertiesSection.Constants.hiddenPropertiesSectionId {
                Menu {
                    Button(Loc.show) { model.revealHiddenRelation(relation) }
                } label: {
                    MoreIndicator()
                }
                .accessibilityIdentifier("torah-object-property-show-\(relation.key)")
            }
        }
        .divider()
    }
    
    private func rowWithoutActions(with relation: Property, addedToObject: Bool) -> some View {
        // Deprecated design
        // TODO: Support new rows without stars and deletion
        // https://www.figma.com/design/16UsBI2PLwydmAC4wJfyu8/%5BM%5D-All-content-%26-Type?node-id=19264-38639&t=fgXeqZbpBgUNrB2C-4
        PropertiesListRowView(
            editingMode: .constant(false),
            starButtonAvailable: false,
            showLocks: false,
            addedToObject: addedToObject,
            relation: relation
        ) { _ in
            anytypeAssertionFailure("Deprecated row delete call")
        } onStarTap: { _ in
            anytypeAssertionFailure("Deprecated onStarTap call")
        } onEditTap: { tappedRelation in
            if model.hasOutput {
                model.handleTapOnRelation(tappedRelation)
            } else if let legacyTorahProperties,
                      let definition = TorahNativePropertyDefinition.definition(for: tappedRelation.key),
                      legacyTorahProperties.isEligible,
                      legacyTorahProperties.canEdit,
                      legacyTorahProperties.session != nil {
                legacyTorahProperties.edit(definition.kind)
            } else {
                model.handleTapOnRelation(tappedRelation)
            }
        }
    }
}
