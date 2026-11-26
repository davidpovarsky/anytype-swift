import Foundation

struct EditorPageViewModelConfiguration {
    let blockId: String?
    let usecase: ObjectHeaderEmptyUsecase
    var quickCapture: Bool = false
    var suppressesAutomaticCursorFocus = false
    var headerHint: ObjectHeaderExpectedLayout? = nil
}
