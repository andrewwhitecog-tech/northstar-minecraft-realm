"""Actual native-footage v17 review render; no text, stills, synthetic motion or approval."""
import json
import statistics
from fractions import Fraction
from pathlib import Path
from private_github import require
from media_pipeline import Media,CROP,fingerprints,reuse
from study_media import motion,probe_duration


def window_filter(start,length):
    return "fps=30,trim=start_frame="+str(start)+":end_frame="+str(start+length)+",setpts=PTS-STARTPTS,"+CROP


def segments(replacements):
    result=[];cursor=0
    for index,item in enumerate(replacements):
        start,end=item["base_frames"]
        if cursor<start:result.append({"kind":"base","start":cursor,"end":start})
        result.append({"kind":"replacement","index":index,"start":start,"end":end})
        cursor=end
    if cursor<1200:result.append({"kind":"base","start":cursor,"end":1200})
    return result


def graph(replacements):
    parts=segments(replacements);base=[p for p in parts if p["kind"]=="base"]
    commands=[]
    if base:
        commands.append("[0:v]split="+str(len(base))+"".join("[base"+str(i)+"]" for i in range(len(base))))
    labels=[];base_index=0
    for n,part in enumerate(parts):
        label="segment"+str(n);labels.append("["+label+"]")
        if part["kind"]=="base":
            chain="[base"+str(base_index)+"]trim=start_frame="+str(part["start"])+":end_frame="+str(part["end"])+",setpts=PTS-STARTPTS,setsar=1";base_index+=1
        else:
            item=replacements[part["index"]]
            chain="["+str(part["index"]+1)+":v]"+window_filter(item["source_start_frame"],part["end"]-part["start"])+",scale=1080:1920:flags=lanczos,setsar=1"
        commands.append(chain+"["+label+"]")
    commands.append("".join(labels)+"concat=n="+str(len(parts))+":v=1:a=0[out]")
    return ";".join(commands)


class ReviewRender(Media):
    def counted_source(self,path,role):
        args=["-v","error","-threads","1","-select_streams","v:0","-count_frames","-show_streams","-show_format","-of","json",str(path)]
        value=json.loads(self.run("ffprobe",args,role+"_counted_probe"))
        duration=probe_duration(value)
        video=value["streams"][0]
        try:
            read=int(video["nb_read_frames"]);rate=float(Fraction(video["avg_frame_rate"]))
        except Exception:require(False,"V17_COUNTED_PROBE_REQUIRED")
        require(read>0 and rate>0,"V17_COUNTED_PROBE_REQUIRED")
        return value,duration,read,rate

    def review_render(self,inputs,replacements):
        base=self.base_contract(inputs["base"])
        originals={role:fingerprints(self.raw(inputs[role],"v17_"+role+"_reference",crop=True)) for role in ("p1","p2","p3")}
        windows=[];probes={}
        for index,item in enumerate(replacements):
            role=item["role"];length=item["base_frames"][1]-item["base_frames"][0]
            if role not in probes:probes[role]=self.counted_source(inputs[role],role)
            probe,duration,read,rate=probes[role]
            end=item["source_start_frame"]+length
            require(end<=int(duration*30) and end/30<=read/rate+1/rate,"V17_SOURCE_PROBE_INSUFFICIENT_FRAMES")
            vf=window_filter(item["source_start_frame"],length)+",fps=4,scale=32:32:flags=area,format=gray"
            raw=self.ff(["-v","error","-i",str(inputs[role]),"-vf",vf,"-an","-f","rawvideo","pipe:1"],"v17_window_"+str(index),True)
            require(len(raw)%1024==0,"V17_WINDOW_SAMPLE_LENGTH")
            frames=[raw[n:n+1024] for n in range(0,len(raw),1024)]
            movement=motion(frames)
            comparisons={old:reuse(fingerprints(frames),reference) for old,reference in originals.items()}
            windows.append({"replacement":item,"source_probe":probe,"motion":movement,"reuse_estimates":comparisons,
                            "motion_eligible":movement["mean_abs_luma_step"]>=.75 and min(movement["frame_luma_stddev"])>=8})
        output=Path("out/P4_V17_NATIVE_RECUT_REVIEW.mp4")
        args=["-v","warning","-i",str(inputs["base"])]
        for item in replacements:args += ["-i",str(inputs[item["role"]])]
        args += ["-filter_complex",graph(replacements),"-map","[out]","-map","0:a:0","-c:v","libx264","-threads","1","-crf","16","-preset","veryfast","-pix_fmt","yuv420p","-fps_mode","cfr","-r","30","-c:a","copy","-movflags","+faststart",str(output)]
        self.ff(args,"v17_review_render")
        probe=self.probe(output,"v17_final_probe")
        video=next(s for s in probe["streams"] if s["codec_type"]=="video");audio=next(s for s in probe["streams"] if s["codec_type"]=="audio")
        require((video.get("width"),video.get("height"),video.get("r_frame_rate"),int(video.get("nb_frames",0)))==(1080,1920,"30/1",1200),"V17_FINAL_VIDEO_CONTRACT")
        require(abs(float(video.get("duration",0))-40)<.002 and abs(float(audio.get("duration",0))-40)<.03,"V17_FINAL_DURATION")
        final_audio=self.audio(output,"v17_candidate")
        original_hash=self.ff(["-v","error","-i",str(inputs["base"]),"-map","0:a:0","-c","copy","-f","hash","-hash","sha256","-"],"v17_original_audio_packet_hash").strip()
        require(original_hash==final_audio["packet_sha256_muxer"],"V17_ORIGINAL_AUDIO_PACKET_MISMATCH")
        final_samples=fingerprints(self.raw(output,"v17_final_reuse",crop=True))
        comparisons={role:reuse(final_samples,reference) for role,reference in originals.items()}
        reuse_ok=all(report["estimated_seconds"]<=1 for report in comparisons.values())
        motion_ok=all(window["motion_eligible"] for window in windows)
        frame_ids={0,300,600,900,1199}
        for item in replacements:
            start,end=item["base_frames"]
            frame_ids.update(n for n in (start-1,start,(start+end-1)//2,end-1,end) if 0<=n<1200)
        images=self.images(output,sorted(frame_ids),"v17_final")
        self.ff(["-v","error","-i",str(output),"-map","0:v:0","-map","0:a:0","-f","null","-"],"v17_full_decode")
        binary=(self.work/output).read_bytes()
        from private_github import digest
        return {"schema":"northstar.promo.v17-review-render.v1","phase":"v17-review-render",
                "status":"TECHNICAL_V17_REVIEW_REQUIRES_ROOT_QC" if reuse_ok and motion_ok else "TECHNICAL_V17_NOT_FOR_RELEASE",
                "creative_approval":False,"root_final_qc_required":True,"technical_release_bar_met":reuse_ok and motion_ok,
                "technical_reuse_within_limit":reuse_ok,"technical_selected_window_motion_eligible":motion_ok,
                "final_reuse_estimates_vs_originals":comparisons,"selected_windows":windows,"base_probe":base,"final_probe":probe,
                "audio":final_audio,"base_audio_packet_sha256_muxer":original_hash,"review_frames":images,
                "timeline_five_frames":[row for row in images if row["frame"] in (0,300,600,900,1199)],
                "candidate":{"file":output.name,"size":len(binary),"sha256":digest(binary)},
                "limits":["4fps reuse and luma-motion are technical estimates, not creative acceptance.","Root must personally view and listen before any release."]}
