import Foundation
// Source-only protocol predicate control. This is the exact three new product
// expressions with identifiers rebound to primitive values. It invokes no
// native schema, original RPC, facade construction, or Apple framework.
func accepts(wholeDisposition: String, hasTypeLayout: Bool, layoutDisposition: String) -> Bool {
    return wholeDisposition.utf8.elementsEqual("MATCHING_SCHEMA_OBSERVED".utf8) &&
        hasTypeLayout &&
        layoutDisposition.utf8.elementsEqual("MATCHING_SCHEMA_OBSERVED".utf8)
}
let complete = "MATCHING_SCHEMA_OBSERVED"
let statuses = [complete, "INCOMPLETE_OR_UNRESOLVED", "CONFLICT", "CHANGED_WHILE_READING", "UNAVAILABLE", ""]
var count = 0
for whole in statuses {
    for layout in statuses {
        for present in [false, true] {
            let actual = accepts(wholeDisposition: whole, hasTypeLayout: present, layoutDisposition: layout)
            let expected = whole == complete && present && layout == complete
            precondition(actual == expected, "source predicate changed native disposition contract")
            count += 1
        }
    }
}
for malformed in ["matching_schema_observed", complete + " ", complete + "\0"] {
    precondition(!accepts(wholeDisposition: malformed, hasTypeLayout: true, layoutDisposition: complete))
    precondition(!accepts(wholeDisposition: complete, hasTypeLayout: true, layoutDisposition: malformed))
    count += 2
}
print("PASS: \(count) primitive protocol predicate cases; native/framework qualification NOT_RUN")
