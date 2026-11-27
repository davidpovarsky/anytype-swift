"""Finite SFTPv3 exclusive-file writer over the already pinned SSH alias.

Protocol framing: IETF draft-ietf-secsh-filexfer-02, sections 3, 4, 6.3,
6.4 and 7. No SSH credentials are read. No rename, removal, truncation,
attribute change, directory scan, or general SFTP operation is implemented.
"""
import hashlib,io,os,re,selectors,signal,struct,subprocess,time
from pathlib import Path


def sftp_upload(path, source, expected_size, expected_sha, label, save, guard, rows):
    """CREATE|WRITE|EXCL, <=8 outstanding 32KiB writes, correlated status."""
    allowed=r'C:\\Users\\DAVID\\AppData\\Local\\SentinelX\\anytapy-immutable-evidence\\(?:pinkha-frozen-e-20261127-|pinkha-root-closed-builds-20261127-)[0-9a-f]{32}\\[A-Za-z0-9][A-Za-z0-9._-]{0,127}'
    assert re.fullmatch(allowed,path) and '..' not in path and expected_size>=0
    command=['sudo','-n','-u','ubuntu','ssh','-T','-o','StrictHostKeyChecking=yes','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=2','-o','ControlMaster=no','-o','ControlPath=none','-o','ControlPersist=no','-s','david-win','sftp']
    row={'label':label,'transport':'sftp-v3','openFlags':42,'maximumWriteBytes':32768,'maximumOutstandingWrites':8,'status':'DISPATCH_INTENT','forcedCleanup':False,'sourceBytesRead':0,'writeBytesAcknowledged':0,'writeStatusesAcknowledged':0,'closeConfirmed':False}
    rows.append(row);save()
    p=None;reader=None;own_reader=False;selector=None;output=bytearray();stderr=bytearray();pending={};started=time.monotonic();input_hash=hashlib.sha256()
    stdout_eof=False;next_id=1
    def bounded():guard();assert time.monotonic()-started<260,'bounded SFTP operation deadline'
    def parse_string(data,at,maximum=65536):
        assert at+4<=len(data),'truncated SFTP string length'
        size=struct.unpack_from('>I',data,at)[0];at+=4
        assert size<=maximum and at+size<=len(data),'bounded SFTP string'
        return data[at:at+size],at+size
    def s(value):return struct.pack('>I',len(value))+value
    def read_event(key):
        nonlocal stdout_eof
        try:data=os.read(key.fd,65536)
        except BlockingIOError:return
        if not data:
            selector.unregister(key.fileobj);key.fileobj.close()
            if key.data=='out':stdout_eof=True
            return
        if key.data=='out':output.extend(data);assert len(output)<=2*1024**2,'bounded SFTP receive buffer'
        else:stderr.extend(data);assert len(stderr)<=131072,'bounded SFTP stderr'
    def send(kind,payload):
        bounded();frame=struct.pack('>IB',len(payload)+1,kind)+payload
        assert len(frame)<=65536,'bounded SFTP outgoing packet'
        view=memoryview(frame);done=0
        selector.register(p.stdin,selectors.EVENT_WRITE,'in')
        try:
            while done<len(view):
                bounded();assert not stdout_eof,'SFTP closed before complete request dispatch'
                for key,_ in selector.select(.1):
                    if key.data=='in':
                        try:wrote=os.write(key.fd,view[done:])
                        except BlockingIOError:continue
                        assert wrote>0;done+=wrote
                    else:read_event(key)
        finally:selector.unregister(p.stdin)
    def receive():
        while True:
            bounded()
            if len(output)>=4:
                size=struct.unpack_from('>I',output,0)[0]
                assert 1<=size<=1024**2,'bounded SFTP incoming packet'
                if len(output)>=4+size:
                    packet=bytes(output[4:4+size]);del output[:4+size];return packet
            assert not stdout_eof,'truncated SFTP response/early EOF'
            for key,_ in selector.select(.1):read_event(key)
    def status(packet):
        assert len(packet)>=9 and packet[0]==101,'expected typed SFTP STATUS'
        request_id,code=struct.unpack_from('>II',packet,1)
        message,at=parse_string(packet,9);language,at=parse_string(packet,at,1024)
        assert at==len(packet),'trailing SFTP STATUS data'
        if code:
            row['lastServerError']={'requestId':request_id,'code':code,'message':message.decode('utf-8','replace'),'language':language.decode('ascii','replace')}
        return request_id,code
    try:
        if isinstance(source,Path):
            reader=os.fdopen(os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME),'rb');own_reader=True;row['sourceKind']='ordinary-file'
        elif isinstance(source,(bytes,bytearray)):
            reader=io.BytesIO(source);own_reader=True;row['sourceKind']='in-memory-bytes'
        else:
            assert callable(getattr(source,'read',None)),'only a supplied bounded read stream is accepted'
            reader=source;row['sourceKind']='borrowed-bounded-read-stream';row['producerLifecycleOwnedByCaller']=True
        bounded();p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,bufsize=0)
        row['pid']=p.pid;save();selector=selectors.DefaultSelector()
        for stream,kind in ((p.stdout,'out'),(p.stderr,'err')):os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,kind)
        os.set_blocking(p.stdin.fileno(),False)
        send(1,struct.pack('>I',3));packet=receive()
        assert len(packet)>=5 and packet[0]==2 and struct.unpack_from('>I',packet,1)[0]==3,'SFTP version3 required'
        at=5;extensions=[]
        while at<len(packet):
            name,at=parse_string(packet,at,4096);_,at=parse_string(packet,at,65536)
            extensions.append(name.decode('ascii','replace'));assert len(extensions)<=64
        row['negotiatedVersion']=3;row['advertisedExtensionNames']=extensions
        # No READ, APPEND or TRUNC bit: existing destinations must fail.
        open_id=next_id;next_id+=1
        send(3,struct.pack('>I',open_id)+s(path.replace('\\','/').encode('utf-8'))+struct.pack('>II',42,0))
        packet=receive()
        if packet[0]==101:
            response_id,code=status(packet);assert response_id==open_id
            raise RuntimeError('SFTP exclusive OPEN refused with status '+str(code))
        assert packet[0]==102 and len(packet)>=9 and struct.unpack_from('>I',packet,1)[0]==open_id,'correlated SFTP HANDLE required'
        handle,at=parse_string(packet,5,256);assert handle and at==len(packet)
        row['exclusiveOpenConfirmed']=True;row['phase']='writing';save()
        offset=0;highest_outstanding=0
        while offset<expected_size or pending:
            while offset<expected_size and len(pending)<8:
                want=min(32768,expected_size-offset);assembled=bytearray()
                while len(assembled)<want:
                    bounded();piece=reader.read(want-len(assembled))
                    assert isinstance(piece,(bytes,bytearray)) and 0<len(piece)<=want-len(assembled),'source ended before pinned size or exceeded bounded read'
                    assembled.extend(piece)
                chunk=bytes(assembled)
                input_hash.update(chunk);request_id=next_id;next_id+=1
                pending[request_id]=(offset,len(chunk));row['sourceBytesRead']+=len(chunk)
                row.update(lastWriteRequestId=request_id,lastWriteOffset=offset)
                send(6,struct.pack('>I',request_id)+s(handle)+struct.pack('>Q',offset)+s(chunk))
                offset+=len(chunk);row['writeBytesDispatched']=offset
                highest_outstanding=max(highest_outstanding,len(pending))
            request_id,code=status(receive())
            assert request_id in pending,'unknown/duplicate SFTP write response id'
            assert code==0,'SFTP write rejected; existing partial retained'
            _,length=pending.pop(request_id);row['writeBytesAcknowledged']+=length;row['writeStatusesAcknowledged']+=1
        assert reader.read(1)==b'' and offset==expected_size and input_hash.hexdigest()==expected_sha,'complete pinned source hash/length required'
        row.update(inputBytes=offset,inputSHA256=input_hash.hexdigest(),actualMaximumOutstandingWrites=highest_outstanding)
        close_id=next_id
        send(4,struct.pack('>I',close_id)+s(handle));response_id,code=status(receive())
        assert response_id==close_id and code==0,'correlated successful SFTP CLOSE required'
        row['closeConfirmed']=True;row['phase']='closed';p.stdin.close()
        while selector.get_map():
            bounded()
            for key,_ in selector.select(.1):read_event(key)
        assert not output,'unexpected response after final CLOSE'
        p.wait(timeout=5)
        try:os.killpg(p.pid,0);absent=False
        except ProcessLookupError:absent=True
        row.update(exitCode=p.returncode,groupPositivelyAbsent=absent)
        assert p.returncode==0 and absent,'SFTP SSH group must exit cleanly'
        assert row['writeBytesAcknowledged']==expected_size
        row['status']='PASS'
    except BaseException as error:
        row.update(status='FAIL',errorType=type(error).__name__,error=str(error));raise
    finally:
        if reader is not None and own_reader:reader.close()
        if selector is not None:selector.close()
        if p is not None:
            try:
                if p.stdin is not None and not p.stdin.closed:p.stdin.close()
                if not row.get('groupPositivelyAbsent'):
                    try:p.wait(timeout=1)
                    except subprocess.TimeoutExpired:pass
                    try:os.killpg(p.pid,0);alive=True
                    except ProcessLookupError:alive=False
                    if alive:
                        row['forcedCleanup']=True
                        for sig in (signal.SIGTERM,signal.SIGKILL):
                            try:os.killpg(p.pid,sig)
                            except ProcessLookupError:alive=False;break
                            deadline=time.monotonic()+5
                            while time.monotonic()<deadline:
                                p.poll()
                                try:os.killpg(p.pid,0)
                                except ProcessLookupError:alive=False;break
                                time.sleep(.05)
                            if not alive:break
                    row['groupPositivelyAbsent']=not alive
                row['exitCode']=p.returncode
            except BaseException as error:row.update(status='FAIL',groupPositivelyAbsent=False,cleanupError=str(error))
            finally:
                for stream in (p.stdin,p.stdout,p.stderr):
                    if stream is not None and not stream.closed:
                        try:stream.close()
                        except OSError as error:row.update(status='FAIL',streamCloseError=str(error))
        else:row.update(processStarted=False,groupPositivelyAbsent=True)
        if row['forcedCleanup'] or not row.get('groupPositivelyAbsent'):row['status']='FAIL'
        row.update(seconds=round(time.monotonic()-started,3),sourceSHA256Observed=input_hash.hexdigest(),unacknowledgedWriteRequests=len(pending),stderr=stderr.decode('utf-8','replace'))
        save()
    assert row['status']=='PASS' and row['groupPositivelyAbsent'] and not row['forcedCleanup'] and row['exitCode']==0
    return row
