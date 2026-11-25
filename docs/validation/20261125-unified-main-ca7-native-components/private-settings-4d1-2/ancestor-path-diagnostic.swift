import Foundation
let root = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
print("TEMP",FileManager.default.temporaryDirectory.path,"RESOLVED",root.path)
var cursor = root.appendingPathComponent("NotCreated-Pinkha-Diagnostic/Library/Application Support/Pinkha/Network/Servers", isDirectory: true)
for _ in 0..<24 {
 do {
  let attrs = try FileManager.default.attributesOfItem(atPath: cursor.path)
  print(cursor.path, String(describing: attrs[.type]))
 } catch let err as NSError { print(cursor.path, err.domain, err.code) }
 if cursor.path == "/" { break }
 cursor.deleteLastPathComponent()
}
