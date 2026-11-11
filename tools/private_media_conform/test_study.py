"""Pure SOURCE tests with synthetic arrays/transport guards, not media or privacy passes."""
import ast
import contextlib
import copy
import io
import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
import study_worker as worker
import study_media as study
import private_github as pg
import cloud_worker as original


def fixture():
    c=json.loads((original.ROOT/"config.template.json").read_text())
    c.update(repository_id=1,draft_release_id=2,draft_tag="private-test",draft_target="a"*40,allowed_actors=["test-owner"],allowed_reviewers=["test-owner"])
    c["canary"].update(run_id=3,run_attempt=1,source_sha="a"*40,proof_asset_id=4,proof_size=None,proof_sha256="b"*64)
    for n,item in enumerate(c["inputs"].values(),10):
        item.update(asset_id=n,size=10,sha256="c"*64)
    c["study_schema"]="northstar.promo.native-source-study-config.v1"
    c["study_inputs"]={role:{"name":name,"asset_id":n,"size":10,"sha256":"d"*64} for n,(role,name) in enumerate(study.STUDY_NAMES.items(),100)}
    return c


def samples():
    return [bytes(range(256))*4 if i%2==0 else bytes(reversed(range(256)))*4 for i in range(20)]


class SourceStudyTests(unittest.TestCase):
    def test_new_sources_parse(self):
        for name in ("study_worker.py","study_media.py","private_github.py"):
            ast.parse((Path(__file__).parent/name).read_text(),filename=name)

    def test_default_is_offline_and_no_conform(self):
        with patch.object(sys,"argv",["study_worker.py"]),patch.object(pg.Transport,"request",side_effect=AssertionError("network forbidden")),patch("subprocess.run",side_effect=AssertionError("media forbidden")),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(worker.main(),0)
        result=json.loads(out.getvalue())
        self.assertFalse(result["network_started"]);self.assertFalse(result["media_started"]);self.assertFalse(result["conform_authorized"])

    def test_all_exact_names_with_actual_pins_required(self):
        c=fixture();self.assertIs(worker.study_configured(c),c)
        for role in study.STUDY_NAMES:
            for key in ("asset_id","name","size","sha256"):
                changed=copy.deepcopy(c);changed["study_inputs"][role][key]=None
                with self.subTest(role=role,key=key),self.assertRaises(pg.GuardError):
                    worker.study_configured(changed)

    def test_unknown_missing_duplicate_and_overbudget_block(self):
        for change in ("unknown","missing","duplicate","overbudget"):
            c=fixture()
            if change=="unknown":c["study_inputs"]["c6"]=c["study_inputs"]["c1"]
            if change=="missing":c["study_inputs"].pop("c1")
            if change=="duplicate":c["study_inputs"]["c1"]["asset_id"]=c["inputs"]["p1"]["asset_id"]
            if change=="overbudget":
                for item in c["study_inputs"].values():item["size"]=pg.MAX_ASSET
            with self.subTest(change=change),self.assertRaises(pg.GuardError):worker.study_configured(c)

    def test_all_study_pins_and_originals_bind_digest(self):
        c=fixture();before=worker.study_digest(c)
        for group,role in [("study_inputs","c1"),("inputs","p2")]:
            changed=copy.deepcopy(c);changed[group][role]["sha256"]="e"*64
            self.assertNotEqual(worker.study_digest(changed),before)

    def test_study_never_satisfies_existing_conform_approval(self):
        c=fixture();worker.study_configured(c)
        self.assertIsNone(c["approval"]["decision"])
        with self.assertRaises(pg.GuardError):original.prior_source_pin(c)

    def test_five_cfr_frames_across_real_duration(self):
        self.assertEqual(study.five_frame_ids(8),[0,60,119,178,238])
        self.assertEqual(len(set(study.five_frame_ids(1))),5)
        for value in (0,float("nan"),float("inf"),91):
            with self.subTest(value=value),self.assertRaises(pg.GuardError):study.five_frame_ids(value)

    def test_probe_real_video_bounds(self):
        probe={"streams":[{"codec_type":"video","width":1920,"height":1080,"duration":"8"}]}
        self.assertEqual(study.probe_duration(probe),8)
        for key,value in [("width",8),("height",5000),("duration","nan")]:
            c=copy.deepcopy(probe);c["streams"][0][key]=value
            with self.subTest(key=key),self.assertRaises(pg.GuardError):study.probe_duration(c)

    def test_motion_uses_actual_array_differences(self):
        movement=study.motion(samples())
        self.assertGreater(movement["mean_abs_luma_step"],1)
        self.assertEqual(movement["sampled_frames"],20)
        self.assertEqual(study.motion([bytes(1024)]*4)["mean_abs_luma_step"],0)
        with self.assertRaises(pg.GuardError):study.motion([bytes(4)]*4)

    def test_reused_or_flat_windows_cannot_be_candidates(self):
        frames=samples();movement=study.motion(frames)
        report={"p1":{"sample_times":[{"time":i/4} for i in range(len(frames))]}}
        self.assertEqual(study.candidate_windows(frames,movement,report),[])
        flat=[bytes(1024)]*20
        self.assertEqual(study.candidate_windows(flat,study.motion(flat),{}),[])

    def test_candidate_windows_are_estimates_nonoverlapping_and_not_approval(self):
        frames=samples();windows=study.candidate_windows(frames,study.motion(frames),{})
        self.assertTrue(windows)
        for i,item in enumerate(windows):
            self.assertTrue(item["estimate_only"])
            self.assertEqual(item["estimated_seconds"][1]-item["estimated_seconds"][0],2)
            for other in windows[i+1:]:
                self.assertTrue(item["sample_indices"][1]<=other["sample_indices"][0] or other["sample_indices"][1]<=item["sample_indices"][0])

    def test_new_output_name_only_narrow_phase_extension(self):
        api=pg.GitHub(fixture(),"synthetic-test-token")
        api.draft=lambda:(_ for _ in ()).throw(pg.GuardError("DRAFT_CHECK_REACHED"))
        for name in ("promo-v16-source-study-123-1.zip","promo-v16-source-qc-123-1.zip","promo-v16-conform-123-1.zip"):
            with self.subTest(name=name),self.assertRaisesRegex(pg.GuardError,"DRAFT_CHECK_REACHED"):api.upload_zip(name,b"synthetic")
        for name in ("source-study.zip","promo-v16-other-123-1.zip","promo-v16-source-study-123-1.mp4","../promo-v16-source-study-123-1.zip"):
            with self.subTest(name=name),self.assertRaisesRegex(pg.GuardError,"OUTPUT_NAME_OR_SIZE"):api.upload_zip(name,b"synthetic")

    def test_canary_failure_blocks_before_private_download_or_media(self):
        calls=[]
        class FailCanary:
            def __init__(self,*args):pass
            def repo_info(self):calls.append("repository")
            def draft(self):calls.append("draft")
            def run_identity(self,*args):calls.append("run")
            def verify_canary(self):calls.append("canary");raise pg.GuardError("ACTUAL_CANARY_GATE_NOT_MET")
            def binary(self,*args):raise AssertionError("private input forbidden")
        with patch.object(worker,"hosted",return_value=None),patch.object(worker,"GitHub",FailCanary),patch.dict(worker.os.environ,{"GITHUB_RUN_ID":"123","GITHUB_TOKEN":"synthetic-test-token"}):
            with self.assertRaisesRegex(pg.GuardError,"ACTUAL_CANARY_GATE_NOT_MET"):worker.perform_study(fixture(),"f"*40)
        self.assertEqual(calls,["repository","draft","run","canary"])

    def test_ffmpeg_frame_selector_uses_cfr30_without_input_seek(self):
        with patch.object(study.Study,"ff") as ff,patch.object(Path,"glob",return_value=[Path("out/c1_review_%02d.png"%i) for i in range(1,6)]):
            media=object.__new__(study.Study);media.out=Path("out")
            rows=media.study_images(Path("inputs/C1_best.mp4"),8,"c1")
            args=ff.call_args.args[0]
            self.assertNotIn("-ss",args)
            self.assertTrue(args[args.index("-vf")+1].startswith("fps=30,"))
            self.assertEqual(len(rows),5)


if __name__=="__main__":unittest.main(verbosity=2)
