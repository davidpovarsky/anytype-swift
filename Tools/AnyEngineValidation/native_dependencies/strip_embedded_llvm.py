#!/usr/bin/env python3
"""Remove embedded legacy LLVM IR, preserving native code and link semantics.

Native symbol table indices/section ordinals may change after deleting LLVM
sections. Every symbol identity and every relocation target is therefore
compared through the actual Mach-O symbol/section tables, not raw indices.
Raw LLVM-only members are refused. The original library remains untouched.
"""
from pathlib import Path
import argparse, hashlib, json, struct, subprocess

def digest(data):return hashlib.sha256(data).hexdigest()
def inventory(path):
 data=path.read_bytes()
 if data[:8]!=b'!<arch>\n':raise ValueError('Not an archive')
 position=8;native=[];metadata=[]
 while position<len(data):
  head=data[position:position+60]
  if len(head)!=60 or head[58:60]!=b'\x60\n':raise ValueError('Invalid archive member header')
  length=int(head[48:58]);name=head[:16].rstrip();body=data[position+60:position+60+length]
  if len(body)!=length:raise ValueError('Truncated archive member')
  if name.startswith(b'#1/'):
   n=int(name[3:]);name=body[:n].rstrip(b'\0');body=body[n:]
  else:name=name.rstrip(b'/')
  position+=60+length+(length%2);name=name.decode()
  if name.startswith('__.SYMDEF') or name in ['', '/', '//']:continue
  if len(body)<32 or struct.unpack_from('<I',body)[0]!=0xfeedfacf:raise ValueError('Non-native Mach-O member '+name)
  magic,cpu,subtype,kind,ncmd,sizecmd,flags,reserved=struct.unpack_from('<8I',body)
  if cpu!=0x100000c or kind!=1:raise ValueError('Not ARM64 relocatable native code')
  sections=[];symtab=None;pos=32;platform=[]
  for i in range(ncmd):
   cmd,cmdsize=struct.unpack_from('<2I',body,pos)
   if cmdsize<8 or pos+cmdsize>len(body):raise ValueError('Invalid native load command')
   if cmd==0x19:
    count=struct.unpack_from('<I',body,pos+64)[0]
    if cmdsize!=72+80*count:raise ValueError('Invalid section table')
    for j in range(count):
     q=pos+72+80*j
     sn=body[q:q+16].split(b'\0')[0].decode();sg=body[q+16:q+32].split(b'\0')[0].decode()
     addr,sz,off,align,rel,nrel,fl,res1,res2,res3=struct.unpack_from('<QQ8I',body,q+32)
     zero=(fl&255) in (1,12,18)
     if (not zero and off+sz>len(body)) or rel+nrel*8>len(body):raise ValueError('Native section bounds')
     sections.append({'segment':sg,'section':sn,'addr':addr,'size':sz,'alignment':align,'flags':fl,
      'sha256':None if zero else digest(body[off:off+sz]),'rel':rel,'nrel':nrel})
   elif cmd==2:
    if symtab is not None:raise ValueError('Duplicate symbol table')
    symtab=struct.unpack_from('<4I',body,pos+8)
   elif cmd in [0x24,0x25,0x2f,0x30,0x32]:
    platform.append(body[pos:pos+cmdsize].hex())
   pos+=cmdsize
  symbols=[];discarded=[]
  if symtab:
   symoff,count,stroff,strsize=symtab
   if symoff+16*count>len(body) or stroff+strsize>len(body):raise ValueError('Symbol table bounds')
   strings=body[stroff:stroff+strsize]
   def symbolstring(index):
    if index>=len(strings):raise ValueError('String table index')
    end=strings.find(b'\0',index)
    if end<0:raise ValueError('Unterminated native symbol')
    return strings[index:end].decode()
   for i in range(count):
    strx,typ,sect,desc,value=struct.unpack_from('<IBBHQ',body,symoff+16*i)
    if sect>len(sections):raise ValueError('Native symbol section')
    section=sections[sect-1] if sect else None
    alias=symbolstring(value) if typ&0xe==0xa else None
    normalized=value
    if section and typ&0xe==0xe:
     normalized=value-section['addr']
    if alias is not None:normalized=alias
    item={'name':symbolstring(strx),'type':typ,'section':None if section is None else [section['segment'],section['section']],
      'desc':desc,'value':normalized}
    symbols.append(item)
    if section and section['segment']=='__LLVM':
     if typ&1 and not typ&0xe0:raise ValueError('Runtime external symbol belongs to removed LLVM data')
     discarded.append(item)
  normalized_sections=[]
  for section in sections:
   if section['segment']=='__LLVM':
    if section['section'] not in ['__bitcode','__cmdline']:raise ValueError('Unknown LLVM section')
    metadata.append({'member':name,'section':section['section'],'size':section['size'],'sha256':section['sha256']});continue
   relocations=[]
   for i in range(section['nrel']):
    addr,word=struct.unpack_from('<2I',body,section['rel']+i*8)
    if addr&0x80000000:raise ValueError('Unqualified ARM64 scattered relocation')
    index=word&0xffffff;pc=(word>>24)&1;length=(word>>25)&3;ext=(word>>27)&1;typ=word>>28
    if typ==10:
     target={'addend24':index}
    elif ext:
     if index>=len(symbols):raise ValueError('Relocation symbol bound')
     target=symbols[index]
     if target['section'] and target['section'][0]=='__LLVM':raise ValueError('Native relocation targets removed LLVM section')
    elif index==0:target={'absolute':True}
    else:
     if index>len(sections):raise ValueError('Relocation section bound')
     s=sections[index-1];target={'section':[s['segment'],s['section']]}
     if s['segment']=='__LLVM':raise ValueError('Native relocation targets removed LLVM section')
    relocations.append({'address':addr,'pcRelative':pc,'length':length,'external':ext,'type':typ,'target':target})
   entry={k:v for k,v in section.items() if k not in ['addr','rel','nrel']}
   entry['relocations']=len(relocations)
   entry['relocationTargetsSHA256']=digest(json.dumps(relocations,sort_keys=True,separators=(',',':')).encode())
   normalized_sections.append(entry)
  runtime_symbols=[s for s in symbols if not (s['section'] and s['section'][0]=='__LLVM')]
  symstrings=sorted(json.dumps(s,sort_keys=True,separators=(',',':')) for s in runtime_symbols)
  externalstrings=sorted(json.dumps(s,sort_keys=True,separators=(',',':')) for s in runtime_symbols if s['type']&1 and not s['type']&0xe0)
  native.append({'member':name,'cpu':cpu,'subtype':subtype,'kind':kind,'flags':flags,'platformCommands':platform,
   'sections':normalized_sections,'nativeSymbolCount':len(runtime_symbols),'nativeSymbolsSHA256':digest(('\n'.join(symstrings)+'\n').encode()),
   'nativeExternalSymbolCount':len(externalstrings),'nativeExternalSymbolsSHA256':digest(('\n'.join(externalstrings)+'\n').encode())})
 return {'native':native,'llvmSections':metadata}


def file_digest(path):return digest(path.read_bytes())

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--llvm-objcopy',required=True,type=Path)
 parser.add_argument('--input',required=True,type=Path)
 parser.add_argument('--output',required=True,type=Path)
 parser.add_argument('--expected-input-sha256',required=True)
 parser.add_argument('--expected-tool-sha256',default='76638bb89898a6d51c7c2c6ca2ac89bc23c38f74a4124f51e56805204de1d604')
 parser.add_argument('--receipt',required=True,type=Path)
 args=parser.parse_args()
 source=args.input.resolve(strict=True);target=args.output.absolute();tool=args.llvm_objcopy.resolve(strict=True)
 if target.exists() or args.receipt.exists():raise ValueError('Refuse to replace an existing output or receipt')
 if file_digest(source)!=args.expected_input_sha256:raise ValueError('Original native library hash mismatch')
 if file_digest(tool)!=args.expected_tool_sha256:raise ValueError('LLVM objcopy executable hash mismatch')
 before=inventory(source)
 if not before['llvmSections']:raise ValueError('Source has no embedded legacy LLVM sections to remove')
 command=[str(tool),'--remove-section=__LLVM,__bitcode','--remove-section=__LLVM,__cmdline',str(source),str(target)]
 result=subprocess.run(command,capture_output=True,text=True,timeout=120)
 if result.returncode:raise RuntimeError(result.stderr)
 after=inventory(target)
 if before['native']!=after['native']:raise ValueError('Native member, code, data, symbol or relocation target changed')
 if after['llvmSections']:raise ValueError('Legacy LLVM sections remain')
 if file_digest(source)!=args.expected_input_sha256:raise ValueError('Original input changed during transform')
 encoded=json.dumps(before['native'],sort_keys=True,separators=(',',':')).encode()
 receipt={'contract':'pinkha-native-embedded-llvm-removal-v2','verified':True,
  'tool':'Ubuntu LLVM objcopy18.1.3','toolSHA256':file_digest(tool),'command':command,
  'sourceSHA256':file_digest(source),'nativeSHA256':file_digest(target),
  'sourceBytes':source.stat().st_size,'nativeBytes':target.stat().st_size,
  'memberCount':len(before['native']),'nativeCodeDataSymbolsRelocationTargetsUnchanged':True,
  'nativeSemanticInventorySHA256':digest(encoded),'nativeExternalSymbolCount':sum(x['nativeExternalSymbolCount'] for x in before['native']),
  'removedLegacyLLVMSections':len(before['llvmSections']),'goLTOGuardDisabled':False,
  'symbolRecheckOnMacRequired':True,'nativeRuntimeTestsRequired':True,'originalPinnedReleaseRetained':True,
  'normalization':'Native symbol identities and relocation targets resolved through actual Mach-O tables; no IR symbols used'}
 args.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt))

if __name__=='__main__':main()
