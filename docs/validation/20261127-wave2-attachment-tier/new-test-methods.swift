    @Test
    func validStorageTiersRetainRawRootAndAllowAvailabilityProgress() throws {
        let inlineWithoutRoot = try AnyNativeAttachment(row([
            "inline": .bool(true), "cached": .bool(true), "durable": .bool(true)
        ], omitting: ["rootCid", "name", "mime"]), objectID: "doc-1")
        let inlineWithEmptyRoot = try AnyNativeAttachment(row([
            "inline": .bool(true), "cached": .bool(true), "durable": .bool(true),
            "rootCid": .string("")
        ], omitting: ["name", "mime"]), objectID: "doc-1")
        #expect(inlineWithoutRoot.inline && inlineWithoutRoot.cached && inlineWithoutRoot.durable)
        #expect(inlineWithoutRoot.rootCID == nil)
        #expect(inlineWithEmptyRoot.inline && inlineWithEmptyRoot.rootCID == "")
        #expect(inlineWithoutRoot.name.isEmpty && inlineWithEmptyRoot.name.isEmpty)
        #expect(inlineWithoutRoot.mime == "application/octet-stream")
        #expect(inlineWithEmptyRoot.mime == "application/octet-stream")

        let full = try AnyNativeAttachment(row(), objectID: "doc-1")
        #expect(!full.inline && full.rootCID == "root-one")
        #expect(!full.sameContent(as: inlineWithoutRoot))
        for (cached, durable) in [(false, false), (true, false), (false, true), (true, true)] {
            let progressed = try AnyNativeAttachment(row([
                "cached": .bool(cached), "durable": .bool(durable)
            ]), objectID: "doc-1")
            #expect(!progressed.inline)
            #expect(progressed.cached == cached && progressed.durable == durable)
            #expect(full.sameContent(as: progressed), "Availability and backup progress must not change content identity")
        }
        let rawRoot = "root-Original-Case"
        let preserved = try AnyNativeAttachment(row(["rootCid": .string(rawRoot)]), objectID: "doc-1")
        #expect(preserved.rootCID?.utf8.elementsEqual(rawRoot.utf8) == true)
    }

    @Test(arguments: ["missing-inline", "null-inline", "wrong-inline", "inline-with-root", "inline-not-cached", "inline-not-durable", "full-missing-root", "full-empty-root", "null-root", "wrong-root"])
    func missingMalformedOrContradictoryTierMetadataIsRejected(invalidCase: String) throws {
        var fields = try #require(row().object)
        switch invalidCase {
        case "missing-inline": fields.removeValue(forKey: "inline")
        case "null-inline": fields["inline"] = .null
        case "wrong-inline": fields["inline"] = .string("false")
        case "inline-with-root":
            fields["inline"] = .bool(true); fields["durable"] = .bool(true)
        case "inline-not-cached":
            fields["inline"] = .bool(true); fields["cached"] = .bool(false)
            fields["durable"] = .bool(true); fields.removeValue(forKey: "rootCid")
        case "inline-not-durable":
            fields["inline"] = .bool(true); fields.removeValue(forKey: "rootCid")
        case "full-missing-root": fields.removeValue(forKey: "rootCid")
        case "full-empty-root": fields["rootCid"] = .string("")
        case "null-root": fields["rootCid"] = .null
        case "wrong-root": fields["rootCid"] = .integer(3)
        default: Issue.record("Unknown finite attachment tier fixture"); return
        }
        #expect(throws: AnyHostError.invalidDocument("native attachment metadata")) {
            try AnyNativeAttachment(.object(fields), objectID: "doc-1")
        }
    }

