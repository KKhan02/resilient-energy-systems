#!/usr/bin/env python3
"""Read-only inventory of tracked SEEDExchange archives and their duplicate bytes."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def run_git(repo, *args):
    r=subprocess.run(['git','-C',str(repo),*args],capture_output=True,check=True)
    return r.stdout


def audit(repo):
    repo=repo.resolve()
    files=[x.decode('utf-8','surrogateescape') for x in run_git(repo,'ls-files','-z').split(b'\0') if x]
    archive_rows=[]
    by_sha=defaultdict(list)
    missing=[]
    for relative in files:
        if not relative.lower().endswith('.zip'):
            continue
        path=repo/relative
        if not path.is_file():
            missing.append(relative)
            continue
        digest=hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):
                digest.update(chunk)
        value=digest.hexdigest()
        try:
            with zipfile.ZipFile(path) as z:
                members=z.namelist()
                zip_ok=z.testzip() is None
        except (zipfile.BadZipFile,OSError):
            members=[];zip_ok=False
        by_sha[value].append(relative)
        archive_rows.append({'path':relative,'bytes':path.stat().st_size,'sha256':value,'valid_zip':zip_ok,'member_count':len(members),'sample_members':members[:25]})
    duplicate_groups=[]
    for digest, paths in by_sha.items():
        if len(paths)>1:
            one_size=(repo/paths[0]).stat().st_size
            duplicate_groups.append({'sha256':digest,'paths':sorted(paths),'extra_copies':len(paths)-1,'repeated_bytes':one_size*(len(paths)-1)})
    return {'tracked_files':len(files),'tracked_zip_files':len(archive_rows),'available_zip_bytes':sum(x['bytes'] for x in archive_rows),'duplicate_groups':len(duplicate_groups),'extra_identical_archives':sum(x['extra_copies'] for x in duplicate_groups),'extra_identical_bytes':sum(x['repeated_bytes'] for x in duplicate_groups),'missing_zip_paths':missing,'archives':archive_rows,'verified_identical_groups':sorted(duplicate_groups,key=lambda x:x['paths'][0])}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path.cwd())
    ap.add_argument('--out',type=Path,required=True,help='New output folder; never overwrite')
    args=ap.parse_args()
    if args.out.exists():
        raise FileExistsError(f'Existing audit folder: {args.out}')
    result=audit(args.repo_root)
    args.out.mkdir(parents=True)
    (args.out/'ARCHIVE_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    lines=['# Local repository archive verification','',f"Tracked files: {result['tracked_files']}",f"Tracked ZIPs: {result['tracked_zip_files']}",f"Verified duplicate archive groups: {result['duplicate_groups']}",f"Extra identical copies: {result['extra_identical_archives']}",f"Potential redundant bytes: {result['extra_identical_bytes']}",'','No files were moved or deleted. Duplicates are provenance evidence until reviewed.','']
    for g in result['verified_identical_groups']:
        lines.append(f"## SHA-256 {g['sha256']}")
        lines.extend('- \x60'+name+'\x60' for name in g['paths'])
        lines.append('')
    (args.out/'ARCHIVE_AUDIT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('archives','verified_identical_groups')},indent=2))


if __name__=='__main__':main()
