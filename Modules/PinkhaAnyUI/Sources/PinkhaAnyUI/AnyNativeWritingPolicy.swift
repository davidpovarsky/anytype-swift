import Foundation
import PinkhaKit
import PinkhaAnyHost

/// The preserved application writing policy owns automatic alignment. Native
/// direction/alignment keys are storage bindings; rendering never writes them.
public enum AnyNativeWritingPolicy {
    public static func resolve(block: AnyEditorBlock, visibleText: String,
                               interfaceDirection: PinkhaLayoutDirection,
                               detectedTextDirection: PinkhaLayoutDirection?) -> PinkhaWritingDirectionDecision {
        let persisted: PinkhaParagraphAlignment? = block.alignment.map {
            switch $0 {
            case .natural: .natural
            case .left: .left
            case .center: .center
            case .right: .right
            case .justified: .justified
            }
        }
        let explicitDirection: PinkhaLayoutDirection? = switch block.direction {
        case .leftToRight: .leftToRight
        case .rightToLeft: .rightToLeft
        default: nil
        }
        let decision = PinkhaWritingDirectionPolicy.resolve(.init(
            isEmpty: visibleText.isEmpty, interfaceDirection: interfaceDirection,
            detectedTextDirection: explicitDirection ?? detectedTextDirection,
            persistedAlignment: persisted,
            alignmentWasExplicit: block.native["style"]?["pinkhaAlignmentWasExplicit"]?.bool == true))
        return .init(baseWritingDirection: explicitDirection ?? decision.baseWritingDirection,
                     alignment: decision.alignment)
    }
}
