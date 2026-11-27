'use strict';
const fs=require('node:fs'),cp=require('node:child_process'),crypto=require('node:crypto');
const {setTimeout:delay}=require('node:timers/promises');
const original='/Users/m1/builds/actions-anytype/anytype-swift/anytype-swift/control-native8ac-stream-canonical-20261127/Tools/PinkhaDualEngineRuntime/hosted_shared_build/native_stream_action/upload_stream.cjs';
const expected='3e9e40a1cf09cca6a79e3b5b4f677884f6619ef8b2aaed34f9fd2ef8665abde3';
function info(e){return Object.fromEntries(['name','message','code','errno','syscall','status','signal','killed','pid','stdout','stderr'].filter(k=>e[k]!==undefined).map(k=>[k,Buffer.isBuffer(e[k])?e[k].toString('utf8'):e[k]]));}
async function main(){
 const bytes=fs.readFileSync(original),sha=crypto.createHash('sha256').update(bytes).digest('hex');
 if(sha!==expected)throw new Error('Exact original action bytes required');
 const {OwnedGroup}=require(original);
 const result={status:'BOUNDED_ORIGINAL_NODE24_OWNED_LIFECYCLE_DIAGNOSTIC_ONLY',observedAt:new Date().toISOString(),node:{execPath:process.execPath,version:process.version,pid:process.pid,platform:process.platform,arch:process.arch},originalAction:{path:original,sha256:sha},observations:[],actualKillCalls:[],historicalPIDReprobed:false};
 const child=cp.spawn('/bin/sleep',['5'],{env:{PATH:'/usr/bin:/bin'},stdio:'ignore',detached:true});
 const terminal=new Promise(resolve=>{child.once('error',e=>resolve({error:info(e)}));child.once('close',(code,signal)=>resolve({code,signal}));});
 await new Promise((resolve,reject)=>{child.once('spawn',resolve);child.once('error',reject);});
 const owner=new OwnedGroup(child.pid);result.ownedPID=child.pid;
 const originalKill=process.kill;
 process.kill=function(pid,signal){try{const value=originalKill.call(process,pid,signal);result.actualKillCalls.push({time:Date.now(),pid,signal,status:'RETURNED'});return value;}catch(e){result.actualKillCalls.push({time:Date.now(),pid,signal,error:info(e)});throw e;}};
 try{
   result.initialGroupProbe=owner.probe();
   for(let i=0;i<3;i++){
     const argv=['-o','rss=','-p',`${process.pid},${child.pid}`],started=Date.now();
     try{const stdout=cp.execFileSync('/bin/ps',argv,{encoding:'utf8',timeout:3000});result.observations.push({argv,timeoutMilliseconds:3000,elapsedMilliseconds:Date.now()-started,stdout,stderr:'',status:0});}
     catch(e){result.observations.push({argv,timeoutMilliseconds:3000,elapsedMilliseconds:Date.now()-started,error:info(e)});throw e;}
     await delay(50);
   }
   result.originalStopAndDrain=await owner.stopAndDrain();
 }catch(e){result.failure=info(e);}
 finally{
   if(!owner.absent){try{result.cleanupDrain=await owner.stopAndDrain();}catch(e){result.cleanupFailure=info(e);}}
   result.terminal=await terminal;result.group=owner.proof();process.kill=originalKill;
 }
 process.stdout.write(JSON.stringify(result)+'\n');
}
main().catch(e=>{process.stderr.write(JSON.stringify({error:info(e)})+'\n');process.exitCode=1;});
