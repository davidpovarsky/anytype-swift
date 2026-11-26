import Foundation
import Lib
func checkGeneratedEntries() throws {
  let version: String = Lib.MobileVersion()
  let result = Lib.MobileStartWithResult("", "", "", "", "", "", "")
  if let result { let _: Int32 = result.code; let _: String = result.address; let _: String = result.message }
  var nativeError: NSError?
  let _: Bool = Lib.MobileStop(&nativeError)
  Lib.MobileStopNow()
  let capture: Data? = Lib.ServicePinkhaCaptureLoadedAccountSource("", "", "", "", "", &nativeError)
  let _: Bool = Lib.ServicePinkhaCancelLoadedAccountSourceCapture("", "")
  let _: Bool = Lib.ServicePinkhaValidateLoadedAccountSourceCapture("", "", "", &nativeError)
  let _: Bool = Lib.ServicePinkhaReleaseLoadedAccountSourceCapture("", "")
  let _ = Lib.ServicePinkhaTorahAuthorizedOperationRead
  let _ = Lib.ServicePinkhaSemanticAnchorCapture
  _ = version; _ = capture
}
