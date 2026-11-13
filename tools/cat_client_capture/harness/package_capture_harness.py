"""Package an ALREADY compiled capture-only recorder. No compiler/game/network launch."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import stat
import zipfile

BASE_SHA = 'b19fefcfee9980099dbf3ebd8426fe8da1f13346c37c347723b6ebc4cc99b532'
SOURCE_SHA = 'cc490d8f3f97703b7fd580c3664c7394d22b0b939fc2cab8024ccdb58b3793e6'
OLD = {'nsp/walk/FrameRecorder.class', 'nsp/walk/FrameRecorder$Frame.class'}
NEW = OLD | {'nsp/walk/FrameRecorder$UniqueWriter.class'}
NAME = 'nsp-route-walk-capture-unique-v01.jar'

def need(value, message):
    if not value:
        raise RuntimeError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--classes', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Fresh capture-unique-build-* directory')
    args = parser.parse_args()
    need(args.baseline.is_file() and not args.baseline.is_symlink(), 'Regular baseline JAR required')
    need(sha(args.baseline.read_bytes()) == BASE_SHA, 'Exact original heldproof-v02 JAR required')
    need(args.source.is_file() and not args.source.is_symlink() and sha(args.source.read_bytes()) == SOURCE_SHA,
         'Exact reviewed candidate source required')
    need(args.classes.is_dir() and not args.classes.is_symlink(), 'Fresh production classes directory required')
    paths = list(args.classes.rglob('*'))
    need(not any(p.is_symlink() for p in paths), 'Symlink class payload refused')
    compiled = {p.relative_to(args.classes).as_posix(): p.read_bytes() for p in paths if p.is_file()}
    need(set(compiled) == NEW, 'Exact three generated recorder classes required; no observer/test/other payload')
    need(all(data.startswith(bytes.fromhex('cafebabe')) for data in compiled.values()), 'Actual Java class bytes required')
    need(not args.output.exists() and args.output.name.startswith('capture-unique-build-'), 'Fresh bounded output directory required')
    with zipfile.ZipFile(args.baseline) as old:
        infos = old.infolist()
        names = [i.filename for i in infos]
        need(len(names) == len(set(names)), 'Duplicate baseline ZIP member refused')
        need({n for n in names if n.startswith('nsp/walk/FrameRecorder') and n.endswith('.class')} == OLD,
             'Baseline recorder class set changed')
        for i in infos:
            need(not i.filename.startswith('/') and '..' not in Path(i.filename).parts and chr(92) not in i.filename,
                 'Unsafe ZIP member')
            need(not stat.S_ISLNK(i.external_attr >> 16), 'Symlink ZIP member refused')
            need(not (i.filename.upper().startswith('META-INF/') and i.filename.upper().endswith(('.SF','.RSA','.DSA','.EC'))),
                 'Signed baseline cannot be repackaged')
        need('fabric.mod.json' in names, 'Original Fabric metadata missing')
        original = {i.filename: old.read(i) for i in infos}
        args.output.mkdir(parents=True)
        out = args.output / NAME
        with zipfile.ZipFile(out, 'x') as new:
            for i in infos:
                new.writestr(i, compiled.get(i.filename, original[i.filename]))
            added = zipfile.ZipInfo('nsp/walk/FrameRecorder$UniqueWriter.class', date_time=(2026,11,13,0,0,0))
            added.compress_type = zipfile.ZIP_DEFLATED
            added.external_attr = 0o100644 << 16
            new.writestr(added, compiled[added.filename])
    with zipfile.ZipFile(out) as new:
        actual = {i.filename: new.read(i) for i in new.infolist()}
    need(set(actual) == set(original) | NEW, 'Output member set mismatch')
    need(all(actual[n] == data for n,data in original.items() if n not in OLD), 'Non-recorder member changed')
    need(all(actual[n] == compiled[n] for n in NEW), 'Compiled class packaging mismatch')
    changes = [{'path':n, 'beforeSha256':sha(original[n]) if n in original else None,
                'afterSha256':sha(actual[n])} for n in sorted(NEW)]
    receipt = {'schema':'northstar.capture-unique-package.v1', 'baselineSha256':BASE_SHA,
               'reviewedSourceSha256':SOURCE_SHA, 'jar':{'name':NAME,'sha256':sha(out.read_bytes()),'bytes':out.stat().st_size},
               'changedOrAddedMembers':changes, 'unchangedMembers':len(original)-len(OLD),
               'allOtherMemberPayloadsByteIdentical':True,
               'fabricMetadataByteIdentical':actual['fabric.mod.json']==original['fabric.mod.json'],
               'compileVerifiedByThisPackager':False, 'unitTestsRunByThisPackager':False, 'nativeAccepted':False,
               'scope':'New capture-specific artifact only; never install alongside old same-modid recorder'}
    (args.output/'PACKAGE_ACTUAL.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
