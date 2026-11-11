"""Separate v17 review-render authorization; never overrides v16 conform approval."""
import argparse
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import zipfile
from private_github import GitHub,GuardError,require,integer,sha,digest,MAX_ASSET
from cloud_worker import hosted,ROOT,REPO,WORKFLOW,zip_outputs,input_digest
from study_worker import study_configured,study_digest
from study_media import STUDY_NAMES


def replacement_digest(replacements):
    return digest(json.dumps(replacements,sort_keys=True,separators=(",",":")).encode())


def validate_replacements(value):
    require(isinstance(value,list) and 1<=len(value)<=8,"V17_REPLACEMENTS_REQUIRED")
    previous=0
    for item in value:
        require(isinstance(item,dict) and set(item)=={"base_frames","role","source_start_frame"},"V17_REPLACEMENT_SCHEMA")
        bounds=item["base_frames"]
        require(isinstance(bounds,list) and len(bounds)==2 and all(type(n) is int for n in bounds),"V17_FRAME_INTEGER_BOUNDS")
        start,end=bounds
        require(0<=start<end<=1200 and start>=previous and end-start>=30,"V17_ORDER_OVERLAP_OR_RANGE")
        require(item["role"] in STUDY_NAMES and type(item["source_start_frame"]) is int and 0<=item["source_start_frame"]<2700,"V17_SOURCE_ROLE_OR_FRAME")
        previous=end
    return value


def configured_v17(config):
    study_configured(config)
    section=config.get("v17_review_render",{})
    require(isinstance(section,dict),"V17_CONFIG_REQUIRED")
    replacements=validate_replacements(section.get("replacements"))
    source=section.get("source_study",{})
    require(isinstance(source,dict) and all(integer(source.get(key)) for key in ("asset_id","size","run_id","run_attempt"))
            and source["size"]<=MAX_ASSET and source["run_attempt"]==1 and sha(source.get("sha256"))
            and re.fullmatch("[0-9a-f]{40}",source.get("source_sha","")) is not None
            and source.get("study_input_manifest_sha256")==study_digest(config)
            and source.get("input_manifest_sha256")==input_digest(config),"V17_SOURCE_STUDY_PIN_REQUIRED")
    approval=section.get("approval",{})
    require(isinstance(approval,dict) and approval.get("decision")=="APPROVE_V17_REVIEW_RENDER"
            and approval.get("reviewer") in config["allowed_reviewers"],"V17_SEPARATE_REVIEW_APPROVAL_REQUIRED")
    for key,value in {"study_asset_id":source["asset_id"],"study_zip_sha256":source["sha256"],"study_run_id":source["run_id"],
                      "study_input_manifest_sha256":study_digest(config),"input_manifest_sha256":input_digest(config),
                      "replacement_manifest_sha256":replacement_digest(replacements)}.items():
        require(approval.get(key)==value,"V17_APPROVAL_BINDING")
    roles={item["role"] for item in replacements}
    require(isinstance(approval.get("reviewed_roles"),list) and len(set(approval["reviewed_roles"]))==len(approval["reviewed_roles"])
            and roles.issubset(set(approval["reviewed_roles"])) and set(approval["reviewed_roles"]).issubset(STUDY_NAMES)
            and approval.get("source_samples_personally_viewed") is True and approval.get("motion_and_reuse_reviewed") is True,"V17_PERSONAL_SAMPLE_REVIEW_REQUIRED")
    require(isinstance(approval.get("reviewed_utc"),str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ",approval["reviewed_utc"]) is not None,"V17_REVIEW_TIME")
    selected={role:config["inputs"][role] for role in ("base","p1","p2","p3")}
    selected.update({item["role"]:config["study_inputs"][item["role"]] for item in replacements})
    require(sum(item["size"] for item in selected.values())<=1024*1024*1024,"V17_SELECTED_INPUT_TOTAL_LIMIT")
    return section


def inspect_study_zip(blob,config):
    section=configured_v17(config);source=section["source_study"]
    require(len(blob)==source["size"] and digest(blob)==source["sha256"],"V17_STUDY_ZIP_INTEGRITY")
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            require(archive.namelist().count("SOURCE_STUDY.json")==1,"V17_STUDY_RECEIPT_DUPLICATE_OR_MISSING")
            info=archive.getinfo("SOURCE_STUDY.json");require(info.file_size<=4_000_000,"V17_STUDY_RECEIPT_SIZE")
            receipt=json.loads(archive.read(info))
    except GuardError:raise
    except Exception:raise GuardError("V17_STUDY_ZIP_RECEIPT") from None
    require(receipt.get("schema")=="northstar.promo.native-source-study.v1" and receipt.get("phase")=="source-study"
            and receipt.get("status")=="STUDY_ONLY_REQUIRES_ROOT_PERSONAL_REVIEW"
            and receipt.get("creative_approval") is False and receipt.get("conform_authorized") is False,"V17_STUDY_STATUS")
    for key,value in {"repository":REPO,"repository_id":config["repository_id"],"draft_release_id":config["draft_release_id"],
                      "workflow_run_id":source["run_id"],"workflow_run_attempt":source["run_attempt"],"source_sha":source["source_sha"],
                      "study_input_manifest_sha256":study_digest(config),"input_manifest_sha256":input_digest(config)}.items():
        require(receipt.get(key)==value,"V17_STUDY_IDENTITY")
    require(set(receipt.get("clips",{}))==set(STUDY_NAMES),"V17_STUDY_CLIP_SET")
    for role,name in STUDY_NAMES.items():
        require(receipt["clips"][role].get("basename")==name,"V17_STUDY_CLIP_NAME")
    return receipt


def perform_v17(config,reviewed_sha):
    section=configured_v17(config);hosted(config,os.environ,reviewed_sha)
    token=os.environ.pop("GITHUB_TOKEN",None);api=GitHub(config,token);run_id=int(os.environ["GITHUB_RUN_ID"])
    api.repo_info();api.draft();api.run_identity(run_id,1,reviewed_sha,WORKFLOW,False);api.verify_canary()
    source=section["source_study"]
    api.run_identity(source["run_id"],source["run_attempt"],source["source_sha"],WORKFLOW,True)
    expected={"name":"promo-v16-source-study-"+str(source["run_id"])+"-1.zip","size":source["size"],"sha256":source["sha256"]}
    inspect_study_zip(api.binary(source["asset_id"],expected),config)
    from v17_media import ReviewRender
    with tempfile.TemporaryDirectory(prefix="nsp-private-v17-review-",dir=os.environ["RUNNER_TEMP"]) as temp:
        work=Path(temp);(work/"inputs").mkdir();inputs={}
        selected={role:config["inputs"][role] for role in ("base","p1","p2","p3")}
        selected.update({item["role"]:config["study_inputs"][item["role"]] for item in section["replacements"]})
        for role,item in selected.items():
            blob=api.binary(item["asset_id"],item);path=work/"inputs"/item["name"];path.write_bytes(blob);inputs[role]=Path("inputs")/item["name"]
        media=ReviewRender(work);failed=False
        try:
            result=media.review_render(inputs,section["replacements"])
            failed=result.get("technical_release_bar_met") is not True
        except GuardError as error:
            result={"schema":"northstar.promo.v17-review-render.v1","phase":"v17-review-render","status":"TECHNICAL_V17_FAILURE_NOT_ACCEPTED","reason_code":error.code};failed=True
        except Exception:
            result={"schema":"northstar.promo.v17-review-render.v1","phase":"v17-review-render","status":"TECHNICAL_V17_FAILURE_NOT_ACCEPTED","reason_code":"INTERNAL_V17_RENDER_FAILURE"};failed=True
        result.update({"repository":REPO,"repository_id":config["repository_id"],"draft_release_id":config["draft_release_id"],
                       "workflow_run_id":run_id,"workflow_run_attempt":1,"source_sha":reviewed_sha,"study_input_manifest_sha256":study_digest(config),
                       "input_manifest_sha256":input_digest(config),
                       "replacement_manifest_sha256":replacement_digest(section["replacements"]),"source_study":source,
                       "commands":media.commands,"native_world_written":False,"public_media_output":False,
                       "creative_approval":False,"root_final_qc_required":True,"review_render_only":True})
        (media.out/"V17_REVIEW_QC.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
        uploaded=api.upload_zip("promo-v17-review-render-"+str(run_id)+"-1.zip",zip_outputs(media.out))
        uploaded.update({"status":"PRIVATE_V17_FAILURE_BUNDLE" if failed else "PRIVATE_V17_REVIEW_BUNDLE_UPLOADED",
                         "phase":"v17-review-render","repository_id":config["repository_id"],"draft_release_id":config["draft_release_id"],
                         "workflow_run_id":run_id,"source_sha":reviewed_sha,"creative_acceptance":False,"review_render_only":True})
        print(json.dumps(uploaded,separators=(",",":")));return 1 if failed else 0


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--phase",choices=("validate","v17-review-render"),default="validate")
    parser.add_argument("--config",default="media-config.json");parser.add_argument("--reviewed-sha");args=parser.parse_args()
    try:
        if args.phase=="validate":
            print(json.dumps({"status":"V17_SOURCE_ONLY_NOT_AUTHORIZED","network_started":False,"media_started":False}));return 0
        path=(ROOT/args.config).resolve();require(path.parent==ROOT and path.name=="media-config.json","CONFIG_LOCATION")
        return perform_v17(json.loads(path.read_text(encoding="utf-8")),args.reviewed_sha)
    except GuardError as error:print(json.dumps({"status":"BLOCKED_NO_ACCEPTANCE","reason_code":error.code}));return 2
    except Exception:print(json.dumps({"status":"BLOCKED_NO_ACCEPTANCE","reason_code":"UNEXPECTED_V17_FAILURE"}));return 2


if __name__=="__main__":sys.exit(main())
