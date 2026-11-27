#!/usr/bin/env python3
"""Prepare a finite public-evidence packet locally; never run the publisher."""
import ast
import base64
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
N = WORKSPACE/'network_files'
CODE = 'Tools/AnyEngineValidation/native_file_positive_offload/'
DOC = 'docs/validation/20261127-native-file-positive-offload/'
BASE = '972f6c2eaed18fdcfa4e5f885d519b3fb18a9aa7'
TREE = 'de8a7074500d28918af62dcbbb2f5c70b82b0580'
BRANCH = 'codex/chatgpt-wave15-network-final-authority-20261127'
WT = '/mnt/development/projects/worktrees/anytype-network-final-authority-publish-20261127'
OLD = N/'final_authority_publication/publish_final_files_authority.py'
OLD_SHA = 'd4615e0cbbace5597d0842900449fc6dde68241a76e4ee50f46ccda4ce072a3f'
PRIOR_RECEIPT = '/mnt/development/projects/evidence/pinkha-w1-final-authority-publication-20261127/attempt2/result.json'
PRIOR_SHA = 'f70e4ea6c21c28b0242471e183c4345cc4babe0fcf172bc43f6b17dda5f0c208'


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()


def main():
    original = OLD.read_bytes()
    assert identity(original)['sha256'] == OLD_SHA
    text = original.decode()

    def replace(before, after):
        nonlocal text
        assert text.count(before) == 1, before
        text = text.replace(before, after)

    replace('"""Publish fixed final metadata/cache sources and actual evidence only.\n\nCreates one new isolated branch from the pinned network parent. No native,\ncompiler, account, prior test replay, existing worktree edit or force push.\n"""',
            '"""Publish only exact positive-Offload controls and actual public evidence.\n\nExtends the same already owned, clean network branch at exact972f. No native,\ncompiler, account, prior test replay, existing-file replacement or force push.\n"""')
    for name in ['PLAN_SHA', 'LOCAL_SHA', 'VALIDATOR_SHA']:
        line = next(row for row in text.splitlines() if row.startswith(name+' = '))
        replace(line, name+" = '__"+name+"__'")
    replace("ADMISSION_SHA = 'cc6e5b4163712bfccae98bb1e586c24723ade0c8862c3656a6e657522996714f'\n", '')
    replace('REMOTE_COUNT = 43', 'REMOTE_COUNT = 11')
    replace('LOCAL_COUNT = 6', 'LOCAL_COUNT = 6')
    replace("BASE = 'e330c0230f352cadff76b4fa0feafd1032fa142e'", "BASE = '"+BASE+"'\nBASE_TREE = '"+TREE+"'\nPRIOR_PUBLICATION = Path('"+PRIOR_RECEIPT+"')\nPRIOR_PUBLICATION_SHA = '"+PRIOR_SHA+"'")
    replace("OUT = Path('/mnt/development/projects/evidence/pinkha-w1-final-authority-publication-20261127/attempt1')",
            "OUT = Path('/mnt/development/projects/evidence/pinkha-w1-positive-offload-publication-20261127/attempt1')")
    replace("CODE = 'Tools/AnyEngineValidation/native_file_metadata_authority/'", "CODE = '"+CODE+"'")
    replace("DOC = 'docs/validation/20261127-native-file-metadata-authority/'", "DOC = '"+DOC+"'")
    replace("    require(not os.path.lexists(WORKTREE) and not os.path.lexists(OUT), 'exclusive new source worktree and receipt')",
            "    require(WORKTREE.is_dir() and not os.path.lexists(OUT), 'existing owned source worktree and exclusive new receipt')\n    require(not os.path.lexists(WORKTREE/CODE.rstrip('/')) and\n            not os.path.lexists(WORKTREE/DOC.rstrip('/')), 'both declared evidence prefixes are absent')")
    replace('    owned_worktree = False', '    owned_worktree = True')
    replace("'protocol': 'pinkha-final-files-authority-source-publication-v1'", "'protocol': 'pinkha-positive-offload-evidence-publication-v1'")
    replace("'privateAccountInputs': 0, 'existingWorktreeWrites': 0, 'forcePushes': 0,",
            "'privateAccountInputs': 0, 'existingOwnedWorktreeUsed': True, 'existingFilesReplaced': 0, 'forcePushes': 0,")
    replace("        require(plan['protocol']=='pinkha-final-files-authority-publication-plan-v1' and",
            "        require(plan['protocol']=='pinkha-positive-offload-publication-plan-v1' and")
    replace("        for module_name, module_sha in [('validate_public_evidence',VALIDATOR_SHA),\n                                        ('final_product_admission',ADMISSION_SHA)]:\n            module_path = HERE/(module_name+'.py'); pin(module_path,module_sha)\n            module_spec = importlib.util.spec_from_file_location('final_publication_'+module_name,module_path)\n            loaded_module = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(loaded_module)\n            if module_name=='validate_public_evidence': evidence_validator=loaded_module\n            else: admission=loaded_module",
            "        prior = json.loads(pin(PRIOR_PUBLICATION, PRIOR_PUBLICATION_SHA))\n        require(prior['status']=='PASS_NORMAL_PUBLICATION_OF_FINAL_FILES_AUTHORITY_WITH_LOSSLESS_HISTORICAL_ARTIFACTS' and\n                prior['commit']==BASE and prior['tree']==BASE_TREE and prior['branch']==BRANCH and\n                prior['publicFileCount']==52 and prior['publishedFilesUnchanged'] is True and\n                prior['publicInputsUnchanged'] is True and prior['fullUndeclaredGitTreePreserved'] is True and\n                prior['allStartedOwnedGroupsPositivelyAbsent'] is True and prior['errors']==prior['completionErrors']==[] and\n                len(prior['commands'])==29 and all(row['exitCode']==0 and row['processGroupAbsent'] is True and\n                    not row['forcedCleanup'] and not row['cleanupErrors'] for row in prior['commands']),\n                'exact prior accepted publication owns this branch/worktree; no historical PID actions')\n        report['priorPublication'] = {'path':str(PRIOR_PUBLICATION),'sha256':PRIOR_PUBLICATION_SHA,\n            'commit':BASE,'tree':BASE_TREE,'historicalProcessIDsProbed':False,'historicalCommandsReexecuted':0}\n        module_path = HERE/'validate_public_evidence.py'; pin(module_path,VALIDATOR_SHA)\n        module_spec = importlib.util.spec_from_file_location('positive_offload_public_evidence',module_path)\n        evidence_validator = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(evidence_validator)")
    replace("report['qualifiedPacket'] = evidence_validator.validate(content,CODE,DOC,admission)",
            "report['qualifiedPacket'] = evidence_validator.validate(content,CODE,DOC)")
    replace("'protocol':'pinkha-final-files-authority-public-file-set-v1'", "'protocol':'pinkha-positive-offload-public-file-set-v1'")
    replace("        require(not textgit('local-branch-absent',['for-each-ref','--format=%(refname)','refs/heads/'+BRANCH]), 'new owned local branch')",
            "        require(textgit('existing-owned-branch',['symbolic-ref','--short','HEAD'],WORKTREE)==BRANCH and\n                textgit('existing-owned-head',['rev-parse','HEAD'],WORKTREE)==BASE and\n                textgit('existing-owned-common',['rev-parse','--git-common-dir'],WORKTREE)==str(COMMON),\n                'same previously owned exact branch, HEAD and common repository')\n        require(textgit('existing-owned-index',['write-tree'],WORKTREE)==BASE_TREE and\n                textgit('exact-base-tree',['rev-parse',BASE+'^{tree}'])==BASE_TREE,\n                'existing complete index matches exact972f; no initialization/reset')\n        require(not git('existing-clean-status',['status','--porcelain=v1','--untracked-files=all'],WORKTREE),\n                'existing owned source/index must already be clean')")
    replace("        require(not textgit('remote-branch-absent',auth+['ls-remote','--heads','origin','refs/heads/'+BRANCH],seconds=60), 'new owned remote branch')",
            "        require(textgit('existing-remote-branch',auth+['ls-remote','--heads','origin','refs/heads/'+BRANCH],seconds=60).split()==\n                [BASE,'refs/heads/'+BRANCH], 'same exact published parent; no changed remote branch')")
    start="        mutate('create-isolated-worktree',['worktree','add','--no-checkout','-b',BRANCH,str(WORKTREE),BASE],seconds=60)"
    end="        require(not git('new-clean-status',['status','--porcelain=v1','--untracked-files=all'],WORKTREE), 'new sparse base is clean')"
    i=text.index(start);j=text.index(end,i)+len(end)
    text=text[:i]+"        # Existing exact owned index and sparse rules remain unchanged.\n        # Only new fixed paths are added with the original --sparse admission."+text[j:]
    replace("            'Enforce current FilesV2 metadata and cache authority'],WORKTREE,60)",
            "            'Qualify backed full-tier Offload and cloud cache recovery'],WORKTREE,60)")
    replace("report['status']='PASS_NORMAL_PUBLICATION_OF_FINAL_FILES_AUTHORITY'",
            "report['status']='PASS_NORMAL_PUBLICATION_OF_POSITIVE_FULL_TIER_OFFLOAD_EVIDENCE'")
    ast.parse(text)
    template = text.encode()
    save(HERE/'publish_positive_offload.template.py', template)
    patch = ''.join(difflib.unified_diff(original.decode().splitlines(True),text.splitlines(True),
                    'qualified-d461/publish_final_files_authority.py','positive-offload/publish_positive_offload.template.py'))
    save(HERE/'publisher.review.patch',patch.encode())

    roots = {
        'source2': '/mnt/development/projects/evidence/pinkha-positive-full-tier-offload-source-20261127-attempt2',
        'source1': '/mnt/development/projects/evidence/pinkha-positive-full-tier-offload-source-20261127-attempt1',
        'runtime': '/var/lib/pinkha-c-filesv2-20261126/positive-full-tier-offload-20261127',
    }
    remote_rows = [
        (CODE+'run_positive_full_tier_offload.py', roots['source2']+'/run_positive_full_tier_offload.py', N/'positive_full_tier_offload/variant_successor/run_positive_full_tier_offload_variant.py'),
        (CODE+'original/run_positive_full_tier_offload.py', roots['source1']+'/run_positive_full_tier_offload.py', N/'positive_full_tier_offload/run_positive_full_tier_offload.py'),
        (CODE+'final_product_admission.py', roots['source2']+'/final_product_admission.py', N/'final_files_authority_product/completion2/final_product_admission.py'),
        (CODE+'owned_swift_commands.py', roots['source2']+'/owned_swift_commands.py', N/'final_authority_publication/owned_swift_commands.py'),
        (DOC+'receipts/attempt2-pass.json', roots['runtime']+'/attempt2/result.json', N/'positive_full_tier_offload/variant_successor/actual_attempt2_result.json'),
        (DOC+'receipts/original-attempt1-fail.json', roots['runtime']+'/attempt1/result.json', N/'positive_full_tier_offload/actual_attempt1_result.json'),
        (DOC+'receipts/attempt2-source-install.json', '/mnt/development/projects/evidence/pinkha-positive-full-tier-offload-source-install-20261127-attempt2/result.json', N/'positive_full_tier_offload/variant_successor/installation/actual-installation-result.json'),
        (DOC+'receipts/original-two-file-cloud.json', '/var/lib/pinkha-w1-cloud-filesv2-20261127/attempt6-small-cloud/result.json', N/'final_authority_publication/offload_feasibility/actual_small_cloud_result.json'),
        (DOC+'receipts/original-protected-variant.json', '/var/lib/pinkha-c-filesv2-20261126/production-lan-files2/result.json', N/'production-lan-files2-result.json'),
        (DOC+'receipts/native1616-producer.json', '/var/lib/pinkha-c-filesv2-20261126/final-authority-native1/result.json', N/'final_files_authority_product/completion2/actual_native1_result.json'),
        (DOC+'receipts/historical-account-limits-read1.json', '/var/lib/pinkha-w1-cloud-filesv2-20261127/account-limits-read1/result.json', N/'quota_consumer_assessment/actual-account-limits-read1-result.json'),
    ]
    local_rows = [
        (CODE+'variant-source-manifest.json', N/'positive_full_tier_offload/variant_successor/variant-source-manifest.json'),
        (CODE+'variant-identity.review.patch', N/'positive_full_tier_offload/variant_successor/variant-identity.review.patch'),
        (DOC+'README.md', HERE/'README.md'),
        (CODE+'publication/validate_public_evidence.py', HERE/'validate_public_evidence.py'),
        (CODE+'publication/publish_positive_offload.template.py', HERE/'publish_positive_offload.template.py'),
        (CODE+'publication/prepare_publication.py', Path(__file__)),
    ]
    assert len(remote_rows)==11 and len(local_rows)==6
    content = {}
    remote = []
    local = []
    local_payload = {}
    for name,source,path in remote_rows:
        data=path.read_bytes(); assert name not in content; content[name]=data
        remote.append(dict(destination=name,source=source,maximumBytes=2*1024**2,**identity(data)))
    for name,path in local_rows:
        data=path.read_bytes(); assert name not in content; content[name]=data
        local.append(dict(destination=name,**identity(data)))
        local_payload[name]=dict(base64=base64.b64encode(data).decode(),**identity(data))
    spec=importlib.util.spec_from_file_location('local_offload_evidence_validator',HERE/'validate_public_evidence.py')
    validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)
    checked=validator.validate(content,CODE,DOC)
    plan={'protocol':'pinkha-positive-offload-publication-plan-v1','expectedHead':BASE,'expectedTree':TREE,
          'branch':BRANCH,'worktree':WT,'remotePublicCopies':remote,'localPublicFiles':local,
          'priorPublicationReceipt':{'path':PRIOR_RECEIPT,'sha256':PRIOR_SHA},
          'existingSourceFilesReplaced':0,'newAccountOrRuntimeActions':0,'preparedStatus':'SOURCE_ONLY_NOT_PUBLISHED'}
    plan_bytes=encoded(plan);local_bytes=encoded(local_payload)
    save(HERE/'PUBLICATION_PLAN.json',plan_bytes);save(HERE/'LOCAL_PUBLIC_FILES.json',local_bytes)
    actual=template
    for before,after in [(b'__PLAN_SHA__',identity(plan_bytes)['sha256'].encode()),
                         (b'__LOCAL_SHA__',identity(local_bytes)['sha256'].encode()),
                         (b'__VALIDATOR_SHA__',identity((HERE/'validate_public_evidence.py').read_bytes())['sha256'].encode())]:
        assert actual.count(before)==1;actual=actual.replace(before,after)
    ast.parse(actual);save(HERE/'publish_positive_offload.py',actual)
    content[DOC+'publication-inputs.json']=plan_bytes
    descriptor={'protocol':'pinkha-positive-offload-public-file-set-v1','baseCommit':BASE,
        'inputPlanSHA256':identity(plan_bytes)['sha256'],'localPublicPayloadSHA256':identity(local_bytes)['sha256'],
        'nativeExecutableCopiedToGit':False,'privateAccountFiles':0,
        'files':{name:identity(data) for name,data in sorted(content.items())}}
    content[DOC+'FILES.json']=encoded(descriptor)
    for name,data in content.items():
        save(HERE/'candidate'/name,data)
        if name.endswith('.py'):ast.parse(data)
    prep={'status':'PREPARED_SOURCE_ONLY_NOT_PUBLISHED','sourceFiles':len(content),'bytes':sum(map(len,content.values())),
          'plan':identity(plan_bytes),'localPayload':identity(local_bytes),'publisher':identity(actual),
          'template':identity(template),'validator':identity((HERE/'validate_public_evidence.py').read_bytes()),
          'reviewPatch':identity(patch.encode()),'pureLocalEvidenceValidation':checked,
          'originalPublisher':{'path':str(OLD),'sha256':OLD_SHA},'newRuntimeOrTestActions':0}
    save(HERE/'PREPARATION.json',encoded(prep))
    print(json.dumps({key:value for key,value in prep.items() if key!='pureLocalEvidenceValidation'},sort_keys=True))


if __name__=='__main__':
    main()
