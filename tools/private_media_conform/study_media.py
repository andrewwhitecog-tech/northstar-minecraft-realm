"""Read-only native clip study. Uses actual FFmpeg; never approves or conforms footage."""
import math
import statistics
from pathlib import Path
from private_github import require
from media_pipeline import Media, fingerprints, reuse
STUDY_NAMES={"c1":"C1_best.mp4","c3":"C3_best.mp4","c4":"C4_best.mp4","c5":"C5_best.mp4","c8":"C8_best.mp4","c9":"C9_best.mp4","c11":"C11_best.mp4","c12":"C12_best.mp4"}


def probe_duration(probe):
    videos=[s for s in probe.get("streams",[]) if s.get("codec_type")=="video"]
    require(len(videos)==1,"STUDY_SINGLE_VIDEO_REQUIRED")
    video=videos[0]
    try:
        duration=float(video.get("duration") or probe.get("format",{}).get("duration"))
        width=int(video.get("width",0));height=int(video.get("height",0))
    except Exception:
        require(False,"STUDY_PROBE_FIELDS")
    require(math.isfinite(duration) and 1<=duration<=90 and 16<=width<=4096 and 16<=height<=4096,"STUDY_VIDEO_BOUNDS")
    require(width>=int(height*9/16)//2*2,"STUDY_PORTRAIT_CROP_WIDTH")
    return duration


def five_frame_ids(duration):
    require(math.isfinite(duration) and 1<=duration<=90,"STUDY_VIDEO_BOUNDS")
    end=max(4,int(duration*30)-2)
    ids=[round(end*q/4) for q in range(5)]
    require(len(set(ids))==5,"STUDY_FIVE_DISTINCT_FRAMES")
    return ids


def motion(frames):
    require(len(frames)>=4 and len(frames)<=361 and all(len(f)==1024 for f in frames),"STUDY_SAMPLE_BOUNDS")
    steps=[sum(abs(a-b) for a,b in zip(x,y))/1024 for x,y in zip(frames,frames[1:])]
    return {"sample_rate_fps":4,"sampled_frames":len(frames),"mean_abs_luma_step":statistics.mean(steps),
            "steps":steps,"frame_luma_stddev":[statistics.pstdev(f) for f in frames],
            "method":"actual decoded center-9:16 crop,4fps32x32 grayscale; luma motion estimate, not proof of scene animation"}


def candidate_windows(frames,movement,reports):
    hit_samples={round(hit["time"]*4) for report in reports.values() for hit in report["sample_times"]}
    candidates=[]
    for start in range(max(0,len(frames)-8+1)):
        end=start+8
        if any(i in hit_samples for i in range(start,end)):
            continue
        step=statistics.mean(movement["steps"][start:end-1])
        contrast=min(movement["frame_luma_stddev"][start:end])
        if step<.75 or contrast<8:
            continue
        candidates.append({"estimated_seconds":[start/4,end/4],"sample_indices":[start,end],
                           "mean_abs_luma_step":step,"minimum_sample_luma_stddev":contrast,
                           "no_sampled_reuse_match":True,"estimate_only":True})
    selected=[]
    for item in sorted(candidates,key=lambda c:c["mean_abs_luma_step"],reverse=True):
        a,b=item["sample_indices"]
        if all(b<=other["sample_indices"][0] or a>=other["sample_indices"][1] for other in selected):
            selected.append(item)
        if len(selected)==3:
            break
    return selected


class Study(Media):
    def study_images(self,path,duration,role):
        frames=five_frame_ids(duration)
        selector="+".join("eq(n\\,"+str(n)+")" for n in frames)
        vf="fps=30,scale=640:640:force_original_aspect_ratio=decrease,select="+selector
        self.ff(["-v","error","-i",str(path),"-vf",vf,"-fps_mode","vfr","-threads","1","out/"+role+"_review_%02d.png"],role+"_images")
        files=sorted(self.out.glob(role+"_review_*.png"))
        require(len(files)==5,"STUDY_REVIEW_FRAME_COUNT")
        return [{"cfr30_frame":frame,"seconds":frame/30,"file":file.name,"source_aspect_preserved":True}
                for frame,file in zip(frames,files)]

    def source_study(self,inputs):
        originals={}
        original_probes={}
        for role in ("p1","p2","p3"):
            original_probes[role]=self.probe(inputs[role],role+"_study_probe")
            probe_duration(original_probes[role])
            originals[role]=fingerprints(self.raw(inputs[role],role+"_study_reference",crop=True))
            require(0<len(originals[role])<=361,"STUDY_REFERENCE_SAMPLE_BOUNDS")
        clips={}
        for role in STUDY_NAMES:
            probe=self.probe(inputs[role],role+"_study_probe")
            duration=probe_duration(probe)
            samples=self.raw(inputs[role],role+"_study_samples",crop=True)
            movement=motion(samples)
            hashes=fingerprints(samples)
            comparisons={old:reuse(hashes,reference) for old,reference in originals.items()}
            clips[role]={"basename":STUDY_NAMES[role],"probe":probe,"duration_seconds":duration,
                         "review_frames":self.study_images(inputs[role],duration,role),"motion":movement,
                         "reuse_estimates_vs_originals":comparisons,
                         "unused_window_candidates":candidate_windows(samples,movement,comparisons)}
        return {"schema":"northstar.promo.native-source-study.v1","phase":"source-study",
                "status":"STUDY_ONLY_REQUIRES_ROOT_PERSONAL_REVIEW","creative_approval":False,
                "conform_authorized":False,"original_comparison_probes":original_probes,"clips":clips,
                "limits":["4fps reuse estimates can miss sub-quarter-second reuse, changed crops or visual transforms.",
                          "Five CFR30 full-aspect decoded frames per source are sampling, not full visual review.",
                          "Candidate windows are estimated central portrait crops; no sampled match is not proof of unused footage.",
                          "No edit or audio render is produced; existing source-QC/conform approval gates remain unchanged."]}
