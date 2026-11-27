#!/usr/bin/env python3
"""Strip only embedded excluded LLVM metadata; prove ELF native link semantics unchanged."""
import argparse,hashlib,json,struct,subprocess
from pathlib import Path
DROP={".llvmbc",".llvmcmd"}
INPUT_SHA="efee68b0fdf23fd8c1c630f10f4cad497bbbcb7372b6b985933324ebe730a601"
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(",",":")).encode()
def require(v,message):
 if not v:raise ValueError(message)
def bounded(data,off,size):
 require(off>=0 and size>=0 and off+size<=len(data),"ELF bounds")
 return data[off:off+size]
def cstring(data,off):
 require(off<len(data),"ELF string offset");end=data.find(b"\0",off)
 require(end>=0,"ELF string terminator");return data[off:end]
def ar_members(data):
 require(data[:8]==b"!<arch>\n","regular archive");pos=8;longs=b"";seen=set()
 while pos<len(data):
  h=bounded(data,pos,60);require(h[58:60]==b"\x60\n","archive header")
  length=int(h[48:58]);name=h[:16].rstrip();body=bounded(data,pos+60,length);pos+=60+length+(length%2)
  if name==b"//":longs=body;continue
  if name in (b"/",b"/SYM64/"):continue
  if name.startswith(b"#1/"):
   n=int(name[3:]);name=body[:n].rstrip(b"\0");body=body[n:]
  elif name.startswith(b"/") and name[1:].isdigit():
   i=int(name[1:]);end=longs.find(b"/\n",i);require(end>=i,"long archive name");name=longs[i:end]
  else:name=name.rstrip(b"/")
  require(name and name not in seen,"unique native archive member");seen.add(name)
  yield name.decode("utf8"),body
 require(pos==len(data),"archive tail")
def elf_native(name,data):
 require(data[:7]==b"\x7fELF\x02\x01\x01","ELF64 little endian native object")
 h=struct.unpack_from("<16sHHIQQQIHHHHHH",data)
 ident,kind,machine,version,entry,phoff,shoff,flags,ehsize,phsize,phnum,shsize,shnum,shstr=h
 require(kind==1 and machine==183 and version==1 and entry==0 and phoff==0 and phnum==0 and ehsize==64 and shsize==64 and 0<shnum<65535 and shstr<shnum,"aarch64 relocatable header")
 sections=[struct.unpack("<IIQQQQIIQQ",bounded(data,shoff+i*64,64)) for i in range(shnum)]
 require(sections[0]==(0,)*10,"empty ELF null section")
 st=sections[shstr];require(st[1]==3,"section name table")
 strings=bounded(data,st[4],st[5]);names=[cstring(strings,s[0]).decode("utf8") for s in sections]
 occurrence={};ids=[]
 for n,s in zip(names,sections):
  k=(n,s[1]);number=occurrence.get(k,0);occurrence[k]=number+1;ids.append([n,s[1],number])
 def section_id(index):
  require(0<=index<len(sections),"native section index");require(names[index] not in DROP,"native reference to LLVM metadata");return ids[index]
 removed=[]
 for i,s in enumerate(sections):
  if names[i] in DROP:
   require(s[1]==1 and s[2]&0x80000000 and not(s[2]&2) and s[6]==0 and s[7]==0,"only excluded LLVM metadata")
   removed.append({"section":names[i],"bytes":s[5],"sha256":sha(bounded(data,s[4],s[5]))})
 symtabs=[i for i,s in enumerate(sections) if s[1]==2]
 require(len(symtabs)==1,"one original native symbol table")
 si=symtabs[0];s=sections[si];require(s[9]==24 and s[5]%24==0 and sections[s[6]][1]==3,"native symbol table")
 symstrings=bounded(data,sections[s[6]][4],sections[s[6]][5]);symbols=[];native_symbols=[]
 for off in range(s[4],s[4]+s[5],24):
  sn,info,other,sect,value,size=struct.unpack("<IBBHQQ",bounded(data,off,24))
  require(sect!=0xffff,"unsupported extended symbol section")
  target=["reserved",sect] if sect>=0xff00 else ids[sect] if sect else None
  item={"nameHex":cstring(symstrings,sn).hex(),"info":info,"other":other,"section":target,"value":value,"bytes":size}
  symbols.append(item)
  if sect and sect<0xff00 and names[sect] in DROP:
   local_mapping=(info==0 and cstring(symstrings,sn)==b"$d")
   require((info==3 or local_mapping) and other==0 and value==0 and size==0,"only exact local metadata section/mapping symbol may disappear")
   row=next(x for x in removed if x["section"]==names[sect])
   row.setdefault("localMetadataSymbols",[]).append(item)
  else:native_symbols.append(item)
 def symbol(index):
  require(index<len(symbols),"relocation/group symbol index");x=symbols[index]
  require(not x["section"] or x["section"][0] not in DROP,"native symbol references removed metadata");return x
 require({i for i,x in enumerate(sections) if x[1]==3}=={shstr,s[6]},"all string tables accounted")
 native=[];relocation_count=0
 for i,s in enumerate(sections):
  n=names[i];typ=s[1]
  if i==0 or n in DROP or typ in (2,3):continue
  require(typ in (1,4,7,8,9,14,17),"closed ELF section kinds")
  item={"id":ids[i],"type":typ,"flags":s[2],"address":s[3],"bytes":s[5],"alignment":s[8],"entryBytes":s[9]}
  if typ in (4,9):
   width=24 if typ==4 else 16
   require(s[6]==si and s[9]==width and s[5]%width==0,"native relocations")
   item["targetSection"]=section_id(s[7]);records=[]
   for off in range(s[4],s[4]+s[5],width):
    fields=struct.unpack("<QQq" if typ==4 else "<QQ",bounded(data,off,width))
    offset,info=fields[:2];records.append({"offset":offset,"type":info&0xffffffff,"symbol":symbol(info>>32),"addend":fields[2] if typ==4 else None})
   item["relocations"]=len(records);item["relocationIdentitySHA256"]=sha(canonical(records));relocation_count+=len(records)
  elif typ==17:
   require(s[6]==si and s[9]==4 and s[5]%4==0,"native COMDAT group")
   values=struct.unpack("<"+"I"*(s[5]//4),bounded(data,s[4],s[5]))
   require(values,"nonempty native group");item["groupFlag"]=values[0];item["signature"]=symbol(s[7]);item["members"]=[section_id(x) for x in values[1:]]
  else:
   require(s[6]==0 and s[7]==0,"unexpected native section references")
   item["contentSHA256"]=None if typ==8 else sha(bounded(data,s[4],s[5]))
  native.append(item)
 normalized_symbols=sorted(canonical(x).decode() for x in native_symbols)
 out={"member":name,"ELFIdentity":ident.hex(),"kind":kind,"machine":machine,"flags":flags,"nativeSections":native,
      "nativeSymbolCount":len(native_symbols),"nativeSymbolsSHA256":sha(("\n".join(normalized_symbols)+"\n").encode()),
      "nativeRelocationCount":relocation_count}
 return out,removed
def inventory(path):
 native=[];metadata=[]
 for name,body in ar_members(path.read_bytes()):
  row,removed=elf_native(name,body);native.append(row)
  metadata += [dict(member=name,**x) for x in removed]
 return {"native":native,"llvmMetadata":metadata}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--source",type=Path,required=True);ap.add_argument("--root",type=Path,required=True);a=ap.parse_args()
 a.root.mkdir(mode=0o700,parents=True,exist_ok=False)
 result={"status":"FAIL","nativeTests":0,"accounts":0,"goLTOGuardDisabled":False}
 def digest(p):return sha(p.read_bytes())
 try:
  source=a.source;tool=Path('/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-core/llvm-tool-recovery1/llvm-objcopy')
  require(source.resolve()==source and source.is_file() and digest(source)==INPUT_SHA,"exact original Linux archive")
  toolSHA=digest(tool)
  require(tool.resolve()==tool and toolSHA=='76638bb89898a6d51c7c2c6ca2ac89bc23c38f74a4124f51e56805204de1d604',"exact recovered LLVM tool")
  before=inventory(source)
  require(len(before["native"])==836 and len(before["llvmMetadata"])==550,"original native/archive metadata census")
  target=a.root/"libtantivy_go.a"
  command=[str(tool),"--remove-section=.llvmbc","--remove-section=.llvmcmd",str(source),str(target)]
  completed=subprocess.run(command,capture_output=True,timeout=120)
  (a.root/"original-stdout.log").write_bytes(completed.stdout);(a.root/"original-stderr.log").write_bytes(completed.stderr)
  result.update(command=command,exitCode=completed.returncode,toolSHA256=toolSHA)
  require(completed.returncode==0,"actual objcopy")
  after=inventory(target)
  (a.root/"native-before.json").write_bytes(canonical(before["native"])+b"\n")
  (a.root/"native-after.json").write_bytes(canonical(after["native"])+b"\n")
  (a.root/"removed-metadata.json").write_bytes(canonical(before["llvmMetadata"])+b"\n")
  require(before["native"]==after["native"],"native sections/symbols/relocation targets changed")
  require(not after["llvmMetadata"],"LLVM metadata remains")
  require(digest(source)==INPUT_SHA and digest(tool)==toolSHA,"original input/tool drift")
  result.update(status="PASS_ELF_NATIVE_EQUIVALENCE_NOT_RUNTIME",sourceSHA256=INPUT_SHA,sourceBytes=source.stat().st_size,
   nativeSHA256=digest(target),nativeBytes=target.stat().st_size,nativeMembers=len(after["native"]),
   nativeSymbolCount=sum(x["nativeSymbolCount"] for x in after["native"]),
   nativeRelocationCount=sum(x["nativeRelocationCount"] for x in after["native"]),
   nativeSemanticInventorySHA256=sha(canonical(after["native"])),removedSections=len(before["llvmMetadata"]),
   removedBytes=sum(x["bytes"] for x in before["llvmMetadata"]),onlyExcludedLLVMMetadataRemoved=True,
   controllerSHA256=digest(Path(__file__)))
 except Exception as e:result["error"]=type(e).__name__+": "+str(e)
 (a.root/"receipt.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print(json.dumps(result));return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
