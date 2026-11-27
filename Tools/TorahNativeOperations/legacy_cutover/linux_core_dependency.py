"""Admit the exact native-only ELF derivative without disabling the Go guard."""
import hashlib,importlib.util,json
from pathlib import Path
TRANSFORM=Path("/var/tmp/pinkha-e-cutover-llvm-native-20261126/attempt3")
RECEIPT_SHA="adc8941d001d81a01fdac2f407741d356594978703255fe860d9a66be2647e18"
HELPER_SHA="24c46be0bb9ae022b605919e4e1a9d1901217bce4847643cdec026870f8a7d29"
ORIGINAL_SHA="efee68b0fdf23fd8c1c630f10f4cad497bbbcb7372b6b985933324ebe730a601"
NATIVE_SHA="eb659a16cf763a47b41c837eeeb10d8743ed5bb96eb4b675582b6ca7c5ebb5f7"
SEMANTICS_SHA="490d812ac60b44137daccfb1b5a0757c2b934b91d6111753a6cb1deb1a1f57f9"
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def require(value,message):
 if not value:raise ValueError(message)
def admit(original):
 helper=Path(__file__).parent/"strip_linux_embedded_llvm.py"
 require(helper.resolve()==helper and digest(helper)==HELPER_SHA,"exact ELF semantic parser")
 receipt=TRANSFORM/"receipt.json"
 require(receipt.resolve()==receipt and digest(receipt)==RECEIPT_SHA,"actual transform receipt")
 result=json.loads(receipt.read_bytes())
 require(result["status"]=="PASS_ELF_NATIVE_EQUIVALENCE_NOT_RUNTIME" and result["exitCode"]==0
  and result["controllerSHA256"]==HELPER_SHA and result["sourceSHA256"]==ORIGINAL_SHA
  and result["nativeSHA256"]==NATIVE_SHA and result["nativeSemanticInventorySHA256"]==SEMANTICS_SHA
  and result["nativeTests"]==result["accounts"]==0 and result["goLTOGuardDisabled"] is False
  and result["onlyExcludedLLVMMetadataRemoved"] is True,"closed actual transform")
 native=TRANSFORM/"libtantivy_go.a"
 require(original.resolve()==original and digest(original)==ORIGINAL_SHA and original.stat().st_size==59821546,"original ELF archive")
 require(native.resolve()==native and digest(native)==NATIVE_SHA and native.stat().st_size==51291066,"actual native-only ELF archive")
 spec=importlib.util.spec_from_file_location("core_elf_native_equivalence",helper)
 parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
 before=parser.inventory(original);after=parser.inventory(native)
 require(before["native"]==after["native"] and not after["llvmMetadata"],"independent full ELF native equality")
 require(len(after["native"])==836 and len(before["llvmMetadata"])==550
  and parser.sha(parser.canonical(after["native"]))==SEMANTICS_SHA,"complete native/metadata census")
 require(digest(original)==ORIGINAL_SHA and digest(native)==NATIVE_SHA and digest(helper)==HELPER_SHA,"dependency drift during admission")
 return native,{"status":"PASS_EXACT_NATIVE_ONLY_DEPENDENCY_NOT_RUNTIME","originalSHA256":ORIGINAL_SHA,
  "nativeSHA256":NATIVE_SHA,"transformReceiptSHA256":RECEIPT_SHA,"parserSHA256":HELPER_SHA,
  "nativeSemanticInventorySHA256":SEMANTICS_SHA,"nativeMembers":836,"nativeTests":0,"accounts":0,"goLTOGuardDisabled":False}
