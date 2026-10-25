"""ffmpeg assembly: scenes (still images or video clips) + transitions + subtitles + narration + music (+ ambient) -> mp4 at -16 LUFS."""
import json, subprocess, textwrap
from pathlib import Path

FPS, XFADE, LEAD, W, H = 25, 0.35, 0.5, 1280, 720

def run(cmd): subprocess.run(cmd, check=True)

def duration(f): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], text=True))

def sub_style(style_id):
    base = "FontName=DejaVu Sans,FontSize=22,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H99000000,BorderStyle=3,Outline=6,Shadow=0,MarginV=30"
    return {"pixel": "FontName=DejaVu Sans Mono,FontSize=22,Bold=1,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BackColour=&HCC000000,BorderStyle=3,Outline=6,Shadow=0,MarginV=30",
            "cinematic": "FontName=DejaVu Sans,FontSize=20,Bold=0,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H66000000,BorderStyle=3,Outline=5,Shadow=0,MarginV=34"}.get(style_id, base)

def _ken_burns(i, frames):
    m = i % 3
    if m == 0: return "z='min(zoom+0.0009,1.14)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if m == 1: return f"z='1.12':x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)'"
    return "z='if(eq(on,1),1.14,max(zoom-0.0009,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"

def scenes_to_video(work, sources, timings, transition="fade", camera="drift", ambient=False):
    """Returns (silent_video, [ambient wavs], scene durations)."""
    work = Path(work); tmp = work / "tmp"; tmp.mkdir(exist_ok=True)
    voice_len = duration(work / "narration.wav"); starts = [t[0] for t in timings] + [voice_len + 0.8]
    durs = [starts[i + 1] - starts[i] for i in range(len(sources))]; durs[0] += LEAD; clips, amb = [], []
    for i, src in enumerate(sources):
        src = str(src); L = durs[i] + (XFADE if i < len(sources) - 1 else 0.0); fr = max(1, round(L * FPS)); out = tmp / f"c{i:02d}.mp4"
        enc = ["-c:v", "libx264", "-crf", "17", "-preset", "medium"]
        if src.endswith(".mp4"):
            cd = duration(src); f = min(max(L / cd, 1.0), 1.4)  # stretch up to 1.4x, then hold the last frame
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf", f"scale={W}:{H},setpts={f}*PTS,fps={FPS},tpad=stop_mode=clone:stop_duration=3,format=yuv420p", "-t", f"{L:.3f}", "-an", *enc, str(out)])
            if ambient:
                a = tmp / f"a{i:02d}.wav"
                run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vn", "-af", f"atempo={1/f:.4f},apad=whole_dur={L:.3f},atrim=0:{L:.3f},aresample=48000", "-ac", "2", str(a)]); amb.append(a)
        elif camera == "step":  # retro: pan in 4 px steps
            x = "x='min(64,floor(t*3.5)*4)'" if i % 2 == 0 else "x='max(0,64-floor(t*3.5)*4)'"
            run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", src, "-vf", f"scale=1344:756:flags=neighbor,crop={W}:{H}:{x}:y=18,fps={FPS},format=yuv420p", "-t", f"{L:.3f}", *enc, str(out)])
        else:
            run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", src, "-vf", f"scale=2560:1440,zoompan={_ken_burns(i, fr)}:d={fr}:s={W}x{H}:fps={FPS},format=yuv420p", "-frames:v", str(fr), *enc, str(out)])
        clips.append(out)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]; [cmd.extend(["-i", str(c)]) for c in clips]; fc, prev, off = [], "[0:v]", 0.0
    for k in range(1, len(clips)):
        off += durs[k - 1]; lab = f"[x{k}]" if k < len(clips) - 1 else "[vid]"
        fc.append(f"{prev}[{k}:v]xfade=transition={transition}:duration={XFADE}:offset={off:.3f}{lab}"); prev = lab
    silent = tmp / "silent.mp4"
    run(cmd + ["-filter_complex", ";".join(fc), "-map", "[vid]", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", str(silent)])
    return silent, amb

def write_srt(work, timings):
    def ts(s): return f"{int(s//3600):02d}:{int(s%3600//60):02d}:{s%60:06.3f}".replace(".", ",")
    p = Path(work) / "subtitles.srt"
    with open(p, "w", encoding="utf-8") as f:
        for i, (a, b, txt) in enumerate(timings, 1): f.write(f"{i}\n{ts(a+LEAD)} --> {ts(b+LEAD+0.2)}\n" + "\n".join(textwrap.wrap(txt, 46)) + "\n\n")
    return p

def mix(work, video, music, style_id, subs, ambient_wavs, dest, music_vol=0.14, ambient_vol=0.45):
    """Voice + music (+ ambient), two-pass loudnorm to -16 LUFS, burn subtitles unless the video already has them."""
    work = Path(work); d = duration(video); inputs = ["-i", str(video), "-i", str(work / "narration.wav")]
    fa = [f"[1:a]adelay={int(LEAD*1000)}|{int(LEAD*1000)},apad,atrim=0:{d:.2f}[v]"]; mixin, idx = ["[v]"], 2
    if music:
        inputs += ["-i", str(music)]
        fa.append(f"[{idx}:a]aloop=loop=-1:size=2e9,atrim=0:{d:.2f},volume={music_vol},afade=t=in:d=1.5,afade=t=out:st={max(d-3,0):.2f}:d=3[m]"); mixin.append("[m]"); idx += 1
    if ambient_wavs:
        for a in ambient_wavs: inputs += ["-i", str(a)]
        n, ch = len(ambient_wavs), f"[{idx}:a]"
        for k in range(1, n):
            lab = f"[ac{k}]" if k < n - 1 else "[amb0]"; fa.append(f"{ch}[{idx+k}:a]acrossfade=d={XFADE}{lab}"); ch = lab
        fa.append(f"{ch}volume={ambient_vol},atrim=0:{d:.2f},apad=whole_dur={d:.2f}[amb]"); mixin.append("[amb]")
    fa.append("".join(mixin) + f"amix=inputs={len(mixin)}:duration=first:normalize=0[pre]")
    p1 = subprocess.run(["ffmpeg", "-nostats", "-loglevel", "info", *inputs, "-filter_complex", ";".join(fa) + ";[pre]loudnorm=I=-16:TP=-2:LRA=11:print_format=json[o]", "-map", "[o]", "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(p1.stderr[p1.stderr.rindex("{"):p1.stderr.rindex("}") + 1])
    fa.append(f"[pre]loudnorm=I=-16:TP=-2:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000[a]")
    vf = ["-vf", f"subtitles={work}/subtitles.srt:force_style='{sub_style(style_id)}'"] if subs else []
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fa), "-map", "0:v", "-map", "[a]", *vf, "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ac", "1", "-shortest", str(dest)])
    return Path(dest)
