import ProtobufMessages
import Services
import Foundation

struct EventsBunch {
    let contextId: String
    let middlewareEvents: [MiddlewareEventMessage]
    let localEvents: [LocalEvent]
#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
    let pinkhaSemanticPublication: PinkhaHeartSemanticAnchorPublicationFence?
#endif

    func send() async {
        await EventBunchSubscribtion.default.sendEvent(events: self)
    }
}

extension EventsBunch {

    init(contextId: String, middlewareEvents: [MiddlewareEventMessage]) {
        self.contextId = contextId
        self.middlewareEvents = middlewareEvents
        self.localEvents = []
#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
        self.pinkhaSemanticPublication = nil
#endif
    }

    init(contextId: String, localEvents: [LocalEvent]) {
        self.contextId = contextId
        self.middlewareEvents = []
        self.localEvents = localEvents
#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
        self.pinkhaSemanticPublication = nil
#endif
    }

    init(event: Anytype_Event) {
        self.init(contextId: event.contextID, middlewareEvents: event.messages)
    }

    init(event: Anytype_ResponseEvent) {
        self.contextId = event.contextID
        self.middlewareEvents = event.messages
        self.localEvents = []
#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 && PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1
        let candidate = PinkhaHeartSemanticAnchorPublication.current
        self.pinkhaSemanticPublication = candidate?.matches(event: event) == true ? candidate : nil
#endif
    }
}
