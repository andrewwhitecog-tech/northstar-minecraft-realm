"""Manual private source-study only. Imports the existing reviewed pipeline guards."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from cloud_worker import configured,hosted,ROOT,REPO,WORKFLOW,input_digest,zip_outputs
from private_github import GitHub,GuardError,require,integer,sha,digest,MAX_ASSET
from study_media import STUDY_NAMES


def study_configured(config):
    configured(config)
    require(config.get("study_schema")=="northstar.promo.native-source-study-config.v1","STUDY_CONFIG_SCHEMA")
    require(set(config.get("study_inputs",{}))==set(STUDY_NAMES),"STUDY_INPUT_ALLOWLIST")
    ids=[]
    selected=list(config["study_inputs"].values())+[config["inputs"][role] for role in ("p1","p2","p3")]
    for role,name in STUDY_NAMES.items():
        item=config["study_inputs"][role]
        require(isinstance(item,dict) and item.get("name")==name and integer(item.get("asset_id"))
                and integer(item.get("size")) and item["size"]<=MAX_ASSET and sha(item.get("sha256")),"STUDY_INPUT_IDENTITY_PIN")
    for item in selected:
        ids.append(item["asset_id"])
    require(len(set(ids))==len(ids) and sum(item["size"] for item in selected)<=1024*1024*1024,"STUDY_DUPLICATE_OR_TOTAL_LIMIT")
    return config


def study_digest(config):
    selected={"study_inputs":config["study_inputs"],"original_inputs":{role:config["inputs"][role] for role in ("p1","p2","p3")}}
    return digest(json.dumps(selected,sort_keys=True,separators=(",",":")).encode())


def perform_study(config,reviewed_sha):
    study_configured(config)
    hosted(config,os.environ,reviewed_sha)
    token=os.environ.pop("GITHUB_TOKEN",None)
    api=GitHub(config,token)
    run_id=int(os.environ["GITHUB_RUN_ID"])
    api.repo_info();api.draft();api.run_identity(run_id,1,reviewed_sha,WORKFLOW,False);api.verify_canary()
    from study_media import Study
    with tempfile.TemporaryDirectory(prefix="nsp-private-native-study-",dir=os.environ["RUNNER_TEMP"]) as temp:
        work=Path(temp);(work/"inputs").mkdir();inputs={}
        selected={**{role:config["inputs"][role] for role in ("p1","p2","p3")},**config["study_inputs"]}
        for role,item in selected.items():
            payload=api.binary(item["asset_id"],item)
            path=work/"inputs"/item["name"];path.write_bytes(payload);inputs[role]=Path("inputs")/item["name"]
        media=Study(work);failed=False
        try:
            result=media.source_study(inputs)
        except GuardError as error:
            result={"schema":"northstar.promo.native-source-study.v1","phase":"source-study","status":"TECHNICAL_STUDY_FAILURE_NOT_ACCEPTED","reason_code":error.code};failed=True
        except Exception:
            result={"schema":"northstar.promo.native-source-study.v1","phase":"source-study","status":"TECHNICAL_STUDY_FAILURE_NOT_ACCEPTED","reason_code":"INTERNAL_STUDY_FAILURE"};failed=True
        result.update({"repository":REPO,"repository_id":config["repository_id"],"draft_release_id":config["draft_release_id"],
                       "workflow_run_id":run_id,"workflow_run_attempt":1,"source_sha":reviewed_sha,
                       "input_manifest_sha256":input_digest(config),"study_input_manifest_sha256":study_digest(config),
                       "commands":media.commands,"native_world_written":False,"public_media_output":False,
                       "creative_approval":False,"conform_authorized":False,"root_personal_qc_required":True})
        (media.out/"SOURCE_STUDY.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
        blob=zip_outputs(media.out)
        uploaded=api.upload_zip("promo-v16-source-study-"+str(run_id)+"-1.zip",blob)
        uploaded.update({"status":"PRIVATE_STUDY_FAILURE_BUNDLE" if failed else "PRIVATE_STUDY_BUNDLE_UPLOADED",
                         "phase":"source-study","repository_id":config["repository_id"],"draft_release_id":config["draft_release_id"],
                         "workflow_run_id":run_id,"source_sha":reviewed_sha,"creative_acceptance":False,"conform_authorized":False})
        print(json.dumps(uploaded,separators=(",",":")))
        return 1 if failed else 0


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--phase",choices=("validate","source-study"),default="validate")
    parser.add_argument("--config",default="media-config.json")
    parser.add_argument("--reviewed-sha")
    args=parser.parse_args()
    try:
        if args.phase=="validate":
            print(json.dumps({"status":"SOURCE_STUDY_PAYLOAD_ONLY_NOT_AUTHORIZED","media_started":False,"network_started":False,"conform_authorized":False}));return 0
        config_path=(ROOT/args.config).resolve()
        require(config_path.parent==ROOT and config_path.name=="media-config.json","CONFIG_LOCATION")
        config=json.loads(config_path.read_text(encoding="utf-8"))
        return perform_study(config,args.reviewed_sha)
    except GuardError as error:
        print(json.dumps({"status":"BLOCKED_NO_ACCEPTANCE","reason_code":error.code}));return 2
    except Exception:
        print(json.dumps({"status":"BLOCKED_NO_ACCEPTANCE","reason_code":"UNEXPECTED_STUDY_FAILURE"}));return 2


if __name__=="__main__":
    sys.exit(main())
