"""SOURCE ONLY synthetic contract/graph tests; no actual media, provider or acceptance."""
import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile
import v17_worker as worker
import v17_media as media
import private_github as pg
import cloud_worker as original
from study_worker import study_digest
from study_media import STUDY_NAMES
from test_study import fixture as study_fixture


def edl():
    return [{"base_frames":[60,180],"role":"c1","source_start_frame":30},
            {"base_frames":[600,900],"role":"c8","source_start_frame":0}]


def fixture():
    c=study_fixture()
    r={"schema":"northstar.promo.native-source-study.v1","phase":"source-study","status":"STUDY_ONLY_REQUIRES_ROOT_PERSONAL_REVIEW",
       "creative_approval":False,"conform_authorized":False,"repository":original.REPO,"repository_id":c["repository_id"],
       "draft_release_id":c["draft_release_id"],"workflow_run_id":500,"workflow_run_attempt":1,"source_sha":"f"*40,
       "study_input_manifest_sha256":study_digest(c),"input_manifest_sha256":original.input_digest(c),"clips":{role:{"basename":name} for role,name in STUDY_NAMES.items()}}
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:z.writestr("SOURCE_STUDY.json",json.dumps(r))
    blob=b.getvalue()
    source={"asset_id":501,"size":len(blob),"sha256":pg.digest(blob),"run_id":500,"run_attempt":1,"source_sha":"f"*40,"study_input_manifest_sha256":study_digest(c),"input_manifest_sha256":original.input_digest(c)}
    approval={"decision":"APPROVE_V17_REVIEW_RENDER","reviewer":"test-owner","reviewed_utc":"2026-11-11T00:00:00Z",
              "study_asset_id":501,"study_zip_sha256":pg.digest(blob),"study_run_id":500,"study_input_manifest_sha256":study_digest(c),"input_manifest_sha256":original.input_digest(c),
              "replacement_manifest_sha256":worker.replacement_digest(edl()),"reviewed_roles":["c1","c8"],
              "source_samples_personally_viewed":True,"motion_and_reuse_reviewed":True}
    c["v17_review_render"]={"source_study":source,"replacements":edl(),"approval":approval}
    return c,blob


class V17SourceTests(unittest.TestCase):
    def test_sources_compile(self):
        for name in ("v17_worker.py","v17_media.py","private_github.py"):
            ast.parse((Path(__file__).parent/name).read_text(),filename=name)

    def test_default_offline(self):
        with patch.object(sys,"argv",["v17_worker.py"]),patch.object(pg.Transport,"request",side_effect=AssertionError("no network")),patch("subprocess.run",side_effect=AssertionError("no media")),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(worker.main(),0)
        self.assertFalse(json.loads(out.getvalue())["media_started"])

    def test_missing_edl_refuses(self):
        for value in (None,[],{},"invented"):
            with self.subTest(value=value),self.assertRaises(pg.GuardError):worker.validate_replacements(value)

    def test_unsafe_interval_and_source_forms_refuse(self):
        for bounds in ([True,90],[-1,60],[0,1201],[50,50],[20,0],[0.0,40],[0,29]):
            value=edl();value[0]["base_frames"]=bounds
            with self.subTest(bounds=bounds),self.assertRaises(pg.GuardError):worker.validate_replacements(value)
        for role,start in (("c6",0),("p1",0),("c1",True),("c1",-1),("c1",2700)):
            value=edl();value[0].update(role=role,source_start_frame=start)
            with self.subTest(role=role,start=start),self.assertRaises(pg.GuardError):worker.validate_replacements(value)

    def test_overlap_and_unordered_refuse(self):
        for value in (list(reversed(edl())),[edl()[0],{**edl()[1],"base_frames":[170,400]}]):
            with self.assertRaises(pg.GuardError):worker.validate_replacements(value)

    def test_unedited_base_coverage_and_total_timing(self):
        parts=media.segments(edl())
        self.assertEqual([(p["start"],p["end"]) for p in parts if p["kind"]=="base"],[(0,60),(180,600),(900,1200)])
        self.assertEqual(sum(p["end"]-p["start"] for p in parts),1200)
        for a,b in zip(parts,parts[1:]):self.assertEqual(a["end"],b["start"])

    def test_graph_native_fps_trim_and_no_still_or_text(self):
        graph=media.graph(edl())
        self.assertIn("[1:v]fps=30,trim=start_frame=30:end_frame=150,setpts=PTS-STARTPTS,crop=",graph)
        self.assertIn("concat=n=5:v=1:a=0[out]",graph)
        self.assertNotIn("drawtext",graph);self.assertNotIn("zoompan",graph)

    def test_actual_pin_and_separate_approval_contract(self):
        c,blob=fixture();self.assertIs(worker.configured_v17(c),c["v17_review_render"])
        self.assertEqual(worker.inspect_study_zip(blob,c)["workflow_run_id"],500)
        self.assertIsNone(c["approval"]["decision"])
        with self.assertRaises(pg.GuardError):original.prior_source_pin(c)

    def test_root_review_flags_and_decision_cannot_be_absent(self):
        for key in ("decision","reviewer","source_samples_personally_viewed","motion_and_reuse_reviewed","reviewed_roles","reviewed_utc"):
            c,_=fixture();c["v17_review_render"]["approval"][key]=None
            with self.subTest(key=key),self.assertRaises(pg.GuardError):worker.configured_v17(c)

    def test_changed_edl_or_input_pins_invalidates_approval(self):
        c,_=fixture();c["v17_review_render"]["replacements"][0]["source_start_frame"]=31
        with self.assertRaises(pg.GuardError):worker.configured_v17(c)
        c,_=fixture();c["study_inputs"]["c1"]["sha256"]="e"*64
        with self.assertRaises(pg.GuardError):worker.configured_v17(c)

    def test_changed_base_pin_cannot_reuse_old_study_or_approval(self):
        c,blob=fixture()
        c["inputs"]["base"]["sha256"]="e"*64
        with self.assertRaisesRegex(pg.GuardError,"V17_SOURCE_STUDY_PIN_REQUIRED"):
            worker.configured_v17(c)
        # Updating the source declaration alone cannot revive the old approval.
        c["v17_review_render"]["source_study"]["input_manifest_sha256"]=original.input_digest(c)
        with self.assertRaisesRegex(pg.GuardError,"V17_APPROVAL_BINDING"):
            worker.configured_v17(c)
        # Updating both declarations still cannot change the actual prior ZIP receipt.
        c["v17_review_render"]["approval"]["input_manifest_sha256"]=original.input_digest(c)
        worker.configured_v17(c)
        with self.assertRaisesRegex(pg.GuardError,"V17_STUDY_IDENTITY"):
            worker.inspect_study_zip(blob,c)

    def test_corrupt_study_zip_refuses(self):
        c,blob=fixture()
        with self.assertRaises(pg.GuardError):worker.inspect_study_zip(blob+b"x",c)

    def test_failed_or_foreign_study_receipt_refuses(self):
        for key,value in (("status","TECHNICAL_STUDY_FAILURE_NOT_ACCEPTED"),("workflow_run_id",999),("source_sha","b"*40),("creative_approval",True)):
            c,blob=fixture()
            with zipfile.ZipFile(io.BytesIO(blob)) as z:r=json.loads(z.read("SOURCE_STUDY.json"))
            r[key]=value;out=io.BytesIO()
            with zipfile.ZipFile(out,"w") as z:z.writestr("SOURCE_STUDY.json",json.dumps(r))
            altered=out.getvalue();s=c["v17_review_render"]["source_study"];s.update(size=len(altered),sha256=pg.digest(altered));c["v17_review_render"]["approval"]["study_zip_sha256"]=pg.digest(altered)
            with self.subTest(key=key),self.assertRaises(pg.GuardError):worker.inspect_study_zip(altered,c)

    def test_upload_only_adds_exact_v17_phase(self):
        c,_=fixture();api=pg.GitHub(c,"synthetic-test-token");api.draft=lambda:(_ for _ in ()).throw(pg.GuardError("DRAFT_REACHED"))
        for name in ("promo-v17-review-render-100-1.zip","promo-v16-source-study-100-1.zip","promo-v16-conform-100-1.zip"):
            with self.assertRaisesRegex(pg.GuardError,"DRAFT_REACHED"):api.upload_zip(name,b"synthetic")
        for name in ("promo-v17-conform-100-1.zip","promo-v17-review-render-100-1.mp4","../promo-v17-review-render-100-1.zip"):
            with self.assertRaisesRegex(pg.GuardError,"OUTPUT_NAME_OR_SIZE"):api.upload_zip(name,b"synthetic")

    def test_failed_canary_stops_before_study_or_private_inputs(self):
        calls=[]
        class FailCanary:
            def __init__(self,*args):pass
            def repo_info(self):calls.append("repository")
            def draft(self):calls.append("draft")
            def run_identity(self,*args):calls.append("current_run")
            def verify_canary(self):calls.append("canary");raise pg.GuardError("CANARY_NOT_PROVEN")
            def binary(self,*args):raise AssertionError("private download forbidden")
        c,_=fixture()
        with patch.object(worker,"hosted",return_value=None),patch.object(worker,"GitHub",FailCanary),patch.dict(worker.os.environ,{"GITHUB_RUN_ID":"100","GITHUB_TOKEN":"synthetic-test-token"}):
            with self.assertRaisesRegex(pg.GuardError,"CANARY_NOT_PROVEN"):worker.perform_v17(c,"a"*40)
        self.assertEqual(calls,["repository","draft","current_run","canary"])


if __name__=="__main__":unittest.main(verbosity=2)
