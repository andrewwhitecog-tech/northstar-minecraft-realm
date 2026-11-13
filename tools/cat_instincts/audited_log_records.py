"""Pure event-local native server log classification; never native proof by itself."""
import re

ERRORS=tuple(re.compile(p,re.I)for p in(
 r'/(?:ERROR|FATAL)\]',r'Failed to (?:load|parse) (?:function|tag|registry|data)',
 r'Exception in (?:thread|server tick)',r'Encountered an unexpected exception',r'Mixin apply failed'))
HEADER=re.compile(r'^\[\d\d:\d\d:\d\d\] \[')
PROFILE=re.compile(r'^\[\d\d:\d\d:\d\d\] \[Download-\d+/ERROR\]: Got an error with a html body connecting to https://sessionserver\.mojang\.com/session/minecraft/profile/([0-9a-f]{32})\?unsigned=false:')
STACK=re.compile(r'(?:^|\n)\s*(?:at\s+[\w.$]+\(|Caused by:|Suppressed:)|\b(?:[\w$]+\.)+[\w$]*(?:Exception|Error)\b')

def audit_log_records(logs,*,expected_ids,actors_ok=False,owner_ok=False,closure_ok=False):
    """Classify each actual indexed event within its own file/boot boundary.

    Only the exact synthetic-profile HTTP429 event can be nonfatal, and only when
    every independent identity/owner/normal-closure prerequisite is literally True.
    Unknown status, mixed status, Java stacks, other errors and foreign UUIDs fail.
    No repeated header is looked up by text and no event spans another log file.
    """
    records=[];all_errors=[];warnings=[];fatal=[];total=0
    expected=set(expected_ids)
    if not all(isinstance(i,str) and re.fullmatch('[0-9a-f]{32}',i)for i in expected):raise ValueError('Exact synthetic profile UUID hex set required')
    for source in logs:
        if not isinstance(source,dict) or not all(isinstance(source.get(k),str)for k in ('file','boot','text')):raise ValueError('Named actual boot log text required')
        lines=source['text'].splitlines();total+=len(lines)
        for index,line in enumerate(lines):
            if not any(p.search(line)for p in ERRORS):continue
            end=next((j for j in range(index+1,len(lines))if HEADER.match(lines[j])),len(lines))
            event='\n'.join(lines[index:end]);match=PROFILE.match(line)
            statuses=re.findall(r'\bstatus\s*=\s*(\d{3})\b',event)
            cosmetic=bool(match and match.group(1)in expected and statuses and set(statuses)=={'429'} and not STACK.search(event) and actors_ok is True and owner_ok is True and closure_ok is True)
            record={'file':source['file'],'boot':source['boot'],'line1':index+1,'endLine1':end,
                    'rawErrorLine':line,'rawEvent':event,'statusCodes':statuses,'fatal':not cosmetic,
                    'classification':('Optional synthetic-player cosmetic profile HTTP429; actual actor identity/readiness/ownership and normal closure verified; transport not repaired'if cosmetic else'Fatal/unclassified actual server error')}
            records.append(record);all_errors.append(line)
            if cosmetic:warnings.append(record)
            else:fatal.append(line)
    return {'lineCount':total,'allErrorLines':all_errors,'records':records,'fatalErrors':fatal,
            'nonfatalTransportWarnings':warnings,'actorReadinessIdentityProven':actors_ok is True,
            'ownerRelationProven':owner_ok is True,'normalClosureProven':closure_ok is True}
