import Testing
import ProtobufMessages
import Services
import SwiftProtobuf

@Suite("BlockInformationConverter fields")
struct BlockInformationConverterFieldsTests {
    @Test("Existing known and unknown fields survive both conversion directions")
    func preservesExistingFields() throws {
        let fields: BlockFields = [
            BlockFieldBundledKey.isLocked.rawValue: Google_Protobuf_Value(boolValue: true),
            "lang": Google_Protobuf_Value(stringValue: "swift"),
            "pinkha.test.unknown": Google_Protobuf_Value(stringValue: "preserve-me")
        ]
        let information = BlockInformation(
            id: "block-id",
            content: .text(.empty(contentType: .text)),
            backgroundColor: nil,
            horizontalAlignment: .right,
            childrenIds: ["child-id"],
            configurationData: BlockInformationMetadata(backgroundColor: .default),
            fields: fields
        )

        let protobuf = try #require(BlockInformationConverter.convert(information: information))
        #expect(protobuf.fields.fields == fields)

        let roundTrip = try #require(BlockInformationConverter.convert(block: protobuf))
        #expect(roundTrip.fields == fields)
        #expect(roundTrip.isLocked)
        #expect(roundTrip.horizontalAlignment == .right)
        #expect(roundTrip.childrenIds == ["child-id"])
    }

    @Test("An empty fields dictionary stays empty")
    func preservesEmptyFields() throws {
        let protobuf = try #require(BlockInformationConverter.convert(information: .emptyText))
        #expect(protobuf.fields.fields.isEmpty)
    }
}
