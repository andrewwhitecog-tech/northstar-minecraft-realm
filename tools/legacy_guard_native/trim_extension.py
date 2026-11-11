"""Native-only case dispatch/observations; source tests do not execute Minecraft."""
import re

def assert_same_observation(original,guarded):
    for key in ('items','storage','result','success'):
        if original[key] != guarded[key]:
            raise RuntimeError('Original/guarded native observation differs: '+key)

def rejection_kind(response,guard_zero,guard_sentinel):
    if guard_zero:return 'GUARD_REJECTION'
    if guard_sentinel:
        if re.search(r'(?i)(failed to instantiate|cannot instantiate|missing.*(?:argument|parameter)|macro.*(?:missing|fail))',response):return 'NATIVE_INSTANTIATION_REFUSAL'
        if re.search(r'(?i)(expected|invalid|unclosed|incorrect argument|unknown.*(?:argument|function)|unrecognized)',response):return 'NATIVE_PARSER_REFUSAL'
    raise RuntimeError('Native rejection classification lacks affirmative evidence: '+response)

def run_trim_cases(cases,sites,cmd,score,condition,reset,check,start_case,report,write):
    def observe(site,prefix):
        return {'items':cmd('data get block {x} {y} {z} Items'.format(**site)),
                'storage':cmd('data get storage nsp_crafter_refill:t first'),
                'result':score(prefix+'result',allow_unset=True),'success':score(prefix+'success',allow_unset=True)}
    for label in report['dispatch_labels']:
        case=cases[label];site=sites[case['fixture_site_index']];start_case(label)
        if case['native_mode']=='DIFFERENTIAL_LITERAL':
            reset(site);cmd('function nsp_mg_proof:original_'+label)
            original=observe(site,'#original_')
            check(label+': original parent continues',score('#original_after')==1)
            check(label+': original removes one stack',condition('if data block {x} {y} {z} Items[15]'.format(**site)) and not condition('if data block {x} {y} {z} Items[16]'.format(**site)))
            reset(site);cmd('function nsp_mg_proof:'+label)
            guarded=observe(site,'#')
            assert_same_observation(original,guarded)
            check(label+': exact native body/result/storage equality',all(original[k]==guarded[k] for k in ('items','storage','result','success')),{'original':original,'guarded':guarded})
            check(label+': guard valid',condition('if data storage nsp_legacy_macro_guard:trim flags{valid:1b}'))
            check(label+': parent continues',score('#after')==1)
            result={'label':label,'status':'PASS','classification':'NATIVE_DIFFERENTIAL_EQUIVALENCE','original':original,'guarded':guarded}
        elif case['native_mode']=='REJECTION_REQUIRED':
            reset(site)
            cmd('data modify storage nsp_legacy_macro_guard:trim flags set value {valid:2b}')
            before_items=cmd('data get block {x} {y} {z} Items'.format(**site));before_storage=cmd('data get storage nsp_crafter_refill:t first')
            response=cmd('function nsp_crafter_refill:trim '+case['arguments_snbt'])
            direct_items=cmd('data get block {x} {y} {z} Items'.format(**site));direct_storage=cmd('data get storage nsp_crafter_refill:t first')
            check(label+': direct refusal no operative writes',(before_items,before_storage)==(direct_items,direct_storage))
            kind=rejection_kind(response,condition('if data storage nsp_legacy_macro_guard:trim flags{valid:0b}'),condition('if data storage nsp_legacy_macro_guard:trim flags{valid:2b}'))
            # Reset OUTSIDE wrapper too: missing/unloaded wrapper cannot inherit a stale continuation pass.
            cmd('scoreboard players set #after nspmg 0');cmd('scoreboard players reset #result nspmg');cmd('scoreboard players reset #success nspmg')
            cmd('data modify storage nsp_legacy_macro_guard:trim flags set value {valid:2b}')
            wrapper_response=cmd('function nsp_mg_proof:'+label)
            after=observe(site,'#')
            check(label+': wrapper refusal no operative writes',(before_items,before_storage)==(after['items'],after['storage']))
            check(label+': parent continues after rejected child',score('#after')==1,{'wrapper_response':wrapper_response})
            if kind=='GUARD_REJECTION':
                check(label+': rejected child result0 success1',(after['result'],after['success'])==(0,1))
                check(label+': wrapper guard rejects',condition('if data storage nsp_legacy_macro_guard:trim flags{valid:0b}'))
            else:
                check(label+': native refusal stays before guard',condition('if data storage nsp_legacy_macro_guard:trim flags{valid:2b}'))
                check(label+': native refusal success is not affirmative',after['success'] in (None,0),after)
            result={'label':label,'status':'PASS','classification':kind,'direct_response':response,'wrapper_response':wrapper_response,'after':after}
        else:raise RuntimeError('Unsupported case dispatch mode: '+case['native_mode'])
        report['case_results'].append(result);write()
