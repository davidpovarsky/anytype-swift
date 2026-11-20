
function pythonTestMembership(text, module) {
 const lines=text.split("\n"), stack=[], methods=[],classes=[];let quote=null, triple=false,escaped=false,depth=0;
 for(let lineno=0;lineno<lines.length;lineno++){
  const raw=lines[lineno];if(raw.includes("\t"))throw new Error("Tabs require manual inspection at "+module+":"+(lineno+1));
  const logicalStart=quote===null&&depth===0;let clean="";
  for(let i=0;i<raw.length;i++){
   const ch=raw[i];
   if(quote!==null){if(escaped){escaped=false;continue;}if(ch==="\\"){escaped=true;continue;}if(triple){if(raw.slice(i,i+3)===quote.repeat(3)){quote=null;triple=false;i+=2;}}else if(ch===quote){quote=null;}continue;}
   if(ch==="#")break;
   if(ch==="'"||ch==='"'){quote=ch;triple=raw.slice(i,i+3)===ch.repeat(3);if(triple)i+=2;clean+=" ";continue;}
   if("([{".includes(ch))depth++;else if(")]}".includes(ch))depth--;
   if(depth<0)throw new Error("Unbalanced bracket at "+module+":"+(lineno+1));
   clean+=ch;
  }
  if(!triple)escaped=false;
  if(!logicalStart||clean.trim()==="")continue;
  const indent=raw.length-raw.trimStart().length;
  while(stack.length&&indent<=stack[stack.length-1].indent)stack.pop();
  const c=clean.trim(), cls=c.match(/^class\s+(\w+)\s*(?:\((.*)\))?:\s*$/),fn=c.match(/^(?:async\s+)?def\s+(\w+)\s*\(/);
  if(cls){const row={name:cls[1],base:cls[2]||"",line:lineno+1,indent,top_level:stack.length===0};classes.push(row);stack.push({kind:"class",...row});}
  else if(fn){const parent=stack[stack.length-1];if(fn[1].startsWith("test_")){const valid=parent?.kind==="class"&&parent.top_level&&parent.base.trim()==="unittest.TestCase"&&indent===parent.indent+4;if(!valid)throw new Error("Test declaration outside direct top-level TestCase membership: "+module+":"+fn[1]+":"+ (lineno+1));methods.push({id:module+"."+parent.name+"."+fn[1],class:parent.name,name:fn[1],line:lineno+1,indent,direct_testcase_member:true});}stack.push({kind:"function",name:fn[1],indent});}
  else if(c.endsWith(":"))stack.push({kind:"block",name:c.split(":")[0],indent});
 }
 if(quote!==null||depth!==0)throw new Error("Incomplete lexical source in "+module);
 return {classes,methods,declared:methods.length,method_ids:methods.map(x=>x.id)};
}

