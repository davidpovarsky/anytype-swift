#!/usr/bin/env python3
"""Own only a new loopback AnySync network; preserve the original T2 project."""
from pathlib import Path
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import time
import traceback
import yaml

BASE = Path('/mnt/development/projects/evidence/page154-final-validation-20261125/semantic-peer-network')
SOURCE = BASE / 'source'
COMMIT = '960805aab318d45854f4cbd735fb28059d835573'
PROJECT = 'pinkha-e-semantic-20261125'
TOOLS = 'sha256:ee6cf65958ee4e9b558c3973802b7fbd64b3a66c7cf78d64d1a08fb9de0af510'
IMAGE_IDS = {
    'any-sync-node-1': 'sha256:91ca6c1998bed3e4fb72b905dc56df3379a3ac2567e4880947497082f3484db4',
    'any-sync-node-2': 'sha256:91ca6c1998bed3e4fb72b905dc56df3379a3ac2567e4880947497082f3484db4',
    'any-sync-node-3': 'sha256:91ca6c1998bed3e4fb72b905dc56df3379a3ac2567e4880947497082f3484db4',
    'any-sync-coordinator': 'sha256:488c96b9c57935919ae33bc500c8497df5576f7b9d16e3905bfa6c6608433cc6',
    'any-sync-coordinator_bootstrap': 'sha256:488c96b9c57935919ae33bc500c8497df5576f7b9d16e3905bfa6c6608433cc6',
    'any-sync-filenode': 'sha256:229f1fc369bf0fa639eb88b199a316ec9940d0d2726db439a6d68c411e1dcc33',
    'any-sync-consensusnode': 'sha256:39e747c6c14ffe4eb94e1c96fbf9ffbe9aacf2289a6e02cc1fc78d7673b28f09',
    'mongo-1': 'sha256:4510cf3d7050003e958745adb25d2deb3fb907430716162d9cc1a92eda2a6047',
    'redis': 'sha256:92f0d6f0d2eb2582511f907f5bffbbedf10970e2427f4433ae2d3bec7e409c8b',
    'garage': 'sha256:866bd13ed2038ba7e7190e840482bc27234c4afaf77be8cfa439ae088c1e4690',
    'netcheck': TOOLS,
}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with p.open('x') as f:
        f.write(value)

def metadata(project):
    ids = subprocess.check_output(['sudo', '-n', 'docker', 'ps', '-aq', '--filter',
                                  'label=com.docker.compose.project=' + project], timeout=15).decode().split()
    if not ids:
        return []
    rows = json.loads(subprocess.check_output(['sudo', '-n', 'docker', 'inspect', *ids], timeout=15))
    return sorted([{
        'id': d['Id'], 'name': d['Name'], 'image': d['Image'], 'startedAt': d['State']['StartedAt'],
        'service': d['Config']['Labels']['com.docker.compose.service'],
        'state': d['State']['Status'], 'health': d['State'].get('Health', {}).get('Status'),
        'ports': d['HostConfig']['PortBindings'],
        'mounts': sorted([{k: m.get(k) for k in ['Type', 'Source', 'Destination']} for m in d['Mounts']],
                         key=lambda m: (m['Destination'], m['Source'], m['Type']))
    } for d in rows], key=lambda row: row['id'])

def main():
    os.umask(0o077)
    out = BASE / 'provision-attempt1'
    out.mkdir(mode=0o700)
    result = {'status': 'FAIL', 'project': PROJECT, 'sourceCommit': COMMIT,
              'oldT2ProjectMutations': 0, 'newPeerAccountsCreated': 0,
              'nativeAcceptance': False, 'startedAt': time.time(), 'commands': []}
    def run(argv, name, cwd=SOURCE, timeout=60):
        with (out / (name + '.log')).open('xb') as log:
            code = subprocess.run(argv, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, timeout=timeout).returncode
        row = {'name': name, 'exitCode': code, 'logSHA256': sha(out / (name + '.log'))}
        result['commands'].append(row)
        if code:
            raise RuntimeError('actual infrastructure command failed: ' + name)
        return out / (name + '.log')
    try:
        assert subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD']).decode().strip() == COMMIT
        assert not subprocess.check_output(['git', '-C', str(SOURCE), 'diff', '--name-only']).strip()
        assert shutil.disk_usage(BASE).free >= 3 * 1024**3, '1GiB infrastructure growth plus2GiB emergency floor'
        assert not metadata(PROJECT), 'new E project must be absent'
        old = metadata('pinkha-t2-20261125')
        write(out / 'original-t2-containers-before.json', json.dumps(old, indent=2, sort_keys=True) + '\n')
        for port in list(range(24001,24007)) + list(range(24101,24107)) + list(range(24801,24804)) + list(range(24901,24907)) + [27401,26479]:
            for kind in [socket.SOCK_STREAM, socket.SOCK_DGRAM]:
                with socket.socket(socket.AF_INET, kind) as sock:
                    sock.bind(('127.0.0.1', port))
        for image in sorted(set(IMAGE_IDS.values())):
            d = json.loads(subprocess.check_output(['sudo','-n','docker','image','inspect',image], timeout=15))[0]
            assert d['Id'] == image
        env = {}
        for line in (SOURCE / '.env.example').read_text().splitlines():
            if line and not line.startswith('#'):
                key, value = line.split('=',1)
                env[key] = value.strip('"')
        roles = ['NODE_1','NODE_2','NODE_3','COORDINATOR','FILENODE','CONSENSUSNODE']
        for n, role in enumerate(roles,1):
            env['ANY_SYNC_' + role + '_PORT'] = str(24000+n)
            env['ANY_SYNC_' + role + '_QUIC_PORT'] = str(24100+n)
            env['ANY_SYNC_' + role + '_METRIC_ADDR'] = '127.0.0.1:' + str(24900+n)
        for n in range(1,4):
            env[f'ANY_SYNC_NODE_{n}_API_SERVER_ADDR'] = '127.0.0.1:' + str(24800+n)
        env.update(MONGO_1_PORT='27401', MONGO_REPLICA_SET='pinkha_e_semantic', REDIS_PORT='26479',
                   STORAGE_DIR=str(SOURCE / 'storage'), EXTERNAL_LISTEN_HOSTS='127.0.0.1',
                   AWS_ACCESS_KEY_ID='pinkha_e_' + secrets.token_hex(8), AWS_SECRET_ACCESS_KEY=secrets.token_hex(32),
                   GARAGE_RPC_SECRET=secrets.token_hex(32))
        for _ in range(10):
            env = {k: re.sub(r'\$\{([A-Z0-9_]+)\}', lambda m: env[m[1]], v) for k,v in env.items()}
        assert not any('${' in v for v in env.values())
        write(SOURCE / '.env', ''.join(k+'="'+v+'"\n' for k,v in env.items()))
        work = SOURCE / 'storage/docker-generateconfig'
        work.mkdir(parents=True,mode=0o700)
        assert not (SOURCE/'storage/minio').exists(), 'new isolated network must have no legacy storage'
        docker = ['sudo','-n','docker','run','--rm','--network','none','--user',f'{os.getuid()}:{os.getgid()}',
                  '--mount','type=bind,src='+str(work)+',dst=/conf','-w','/conf','--entrypoint','/usr/bin/anyconf',TOOLS]
        run(docker + ['create-network'], 'original-anyconf-create-network')
        first = yaml.safe_load((work / 'nodes.yml').read_text())
        root_account = yaml.safe_load((work / 'account.yml').read_text())
        arguments = ['generate-nodes']
        for role in ['tree','tree','tree','coordinator','file','consensus']:
            arguments += ['--t',role]
        for role in roles:
            arguments += ['--addresses', env['ANY_SYNC_'+role+'_ADDRESSES']]
        run(docker + arguments, 'original-anyconf-generate-nodes')
        nodes = yaml.safe_load((work / 'nodes.yml').read_text())
        nodes.pop('creationTime',None)
        nodes['networkId'] = first['networkId']
        (work / 'nodes.yml').write_text(yaml.safe_dump(nodes,sort_keys=False))
        for n in [3,5]:
            p=work/f'account{n}.yml';a=yaml.safe_load(p.read_text())
            a['account']['signingKey']=root_account['account']['signingKey']
            p.write_text(yaml.safe_dump(a,sort_keys=False))
        run(['python3','./docker-generateconfig/setListenIp.py',str(work/'nodes.yml'),str(work/'nodesProcessed.yml')], 'original-client-address-generation')
        client=yaml.safe_load((work/'nodesProcessed.yml').read_text())
        assert len(client['nodes'])==6 and client['networkId']==first['networkId']
        common=(SOURCE/'docker-generateconfig/etc/common.yml').read_text()
        network=yaml.safe_dump({'network':client},sort_keys=False)
        names=['node-1','node-2','node-3','coordinator','filenode','consensusnode']
        for n,name in enumerate(names):
            raw=network+common+(work/f'account{n}.yml').read_text()+(SOURCE/f'docker-generateconfig/etc/{name}.yml').read_text()
            raw=re.sub(r'%([A-Z0-9_]+)%',lambda m:env[m[1]],raw)
            assert not re.search(r'%[A-Z0-9_]+%',raw)
            d=yaml.safe_load(raw)
            assert d['network']==client and d['account']==yaml.safe_load((work/f'account{n}.yml').read_text())['account']
            write(SOURCE/f'etc/any-sync-{name}/config.yml',yaml.safe_dump(d,sort_keys=False))
        write(SOURCE/'etc/client.yml',yaml.safe_dump(client,sort_keys=False))
        write(SOURCE/'etc/any-sync-coordinator/network.yml',yaml.safe_dump(client,sort_keys=False))
        aws=(SOURCE/'docker-generateconfig/etc/aws-credentials').read_text()
        write(SOURCE/'etc/.aws/credentials',re.sub(r'%([A-Z0-9_]+)%',lambda m:env[m[1]],aws))
        # Original generated native identities, with only the six actual
        # loopback TCP endpoints reachable through the dedicated SSH forwards.
        mac_client=json.loads(json.dumps(client))
        assert not re.search(r'(?i)"(?:account|privatekey|signingkey|peerkey)"\s*:', json.dumps(mac_client)), 'public nodeconf must not contain private account keys'
        for n,node in enumerate(mac_client['nodes'],1):
            address='127.0.0.1:'+str(24000+n)
            assert address in node['addresses']
            node['addresses']=[address]
        write(BASE/'mac-public-nodeconf.yml',yaml.safe_dump(mac_client,sort_keys=False))
        log=run(['sudo','-n','docker','compose','-p',PROJECT,'-f','docker-compose.yml','config','--format','json'],'original-compose-render')
        composed=json.loads(log.read_bytes())
        for name in list(composed['services']):
            if name not in IMAGE_IDS:
                del composed['services'][name]
                continue
            service=composed['services'][name]
            service['image']=IMAGE_IDS[name]
            service['pull_policy']='never'
            service.pop('build',None)
            deps=service.get('depends_on',{})
            for dep in list(deps):
                if dep not in IMAGE_IDS:del deps[dep]
            for port in service.get('ports',[]):
                port['host_ip']='127.0.0.1'
            for mount in service.get('volumes',[]):
                if mount['type']=='bind':assert Path(mount['source']).is_relative_to(SOURCE)
        composed['services']['mongo-1']['command'] += ['--wiredTigerCacheSizeGB','0.25']
        composed['services']['mongo-1']['mem_limit']='512m'
        write(BASE/'runtime.compose.json',json.dumps(composed,indent=2,sort_keys=True)+'\n')
        result['generatedPublicNodeconfSHA256']=sha(SOURCE/'etc/client.yml')
        result['macPublicNodeconfSHA256']=sha(BASE/'mac-public-nodeconf.yml')
        result['runtimeComposeSHA256']=sha(BASE/'runtime.compose.json')
        result['images']=IMAGE_IDS
        result['configGeneration']='original anyconf create-network/generate-nodes and setListenIp; YAML operations reproduce original init.sh without downloading a builder'
        result['nativeServiceChanges']='loopback bindings, pinned cached images, isolated persistent paths/ports, bounded Mongo cache; native protocols unchanged'
        run(['sudo','-n','docker','compose','-p',PROJECT,'-f',str(BASE/'runtime.compose.json'),'up','-d','--no-build','--pull','never'],'start-new-owned-network',timeout=240)
        deadline=time.monotonic()+120
        while True:
            current=metadata(PROJECT)
            if any(r['service']=='netcheck' and r['health']=='healthy' for r in current):break
            if time.monotonic()>deadline:raise RuntimeError('real native netcheck did not become healthy')
            if shutil.disk_usage(BASE).free<2*1024**3:raise RuntimeError('2GiB infrastructure emergency floor reached')
            time.sleep(2)
        after=metadata('pinkha-t2-20261125')
        assert after==old, 'old T2 identity/state changed externally during new-network setup'
        result['ownedContainers']=current
        result['oldT2ContainerIdentitiesUnchanged']=True
        result['status']='PASS_REAL_ISOLATED_NETWORK_HEALTH_NOT_PEER_ACCEPTANCE'
    except Exception as error:
        result['error']={'type':type(error).__name__,'message':str(error)}
        write(out/'traceback.txt',traceback.format_exc())
    finally:
        result['finishedAt']=time.time()
        result['freeBytesAfter']=shutil.disk_usage(BASE).free
        write(out/'receipt.json',json.dumps(result,indent=2,sort_keys=True)+'\n')
        print(json.dumps({k:result.get(k) for k in ['status','error','macPublicNodeconfSHA256','freeBytesAfter']}),flush=True)
    return 0 if result['status']=='PASS_REAL_ISOLATED_NETWORK_HEALTH_NOT_PEER_ACCEPTANCE' else 1

if __name__=='__main__':
    raise SystemExit(main())
