import math
import os
import random
import struct
import subprocess
import wave

ROOT = r"c:\laragon\www\TierSystem-Django\video"
SFX_DIR = os.path.join(ROOT, "assets", "sfx")
FFMPEG = r"C:\Users\Usuario\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
SR = 44100

os.makedirs(SFX_DIR, exist_ok=True)


def write_wav_and_mp3(name, samples, bitrate="160k"):
    wav_path = os.path.join(SFX_DIR, f"{name}.wav")
    mp3_path = os.path.join(SFX_DIR, f"{name}.mp3")
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        # Normalize safely
        peak = max((abs(x) for x in samples), default=1.0)
        scale = 0.88 / peak if peak > 0.88 else 1.0
        buf = bytearray()
        for i in range(0, len(samples), 2):
            l = max(-1.0, min(1.0, samples[i] * scale))
            r = max(-1.0, min(1.0, samples[i + 1] * scale))
            buf.extend(struct.pack("<hh", int(l * 32767), int(r * 32767)))
        wf.writeframes(buf)

    subprocess.run(
        [FFMPEG, "-y", "-i", wav_path, "-c:a", "libmp3lame", "-b:a", bitrate, mp3_path],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.remove(wav_path)
    print(f"[OK] {name}.mp3")


def gen_pop():
    # Crisp, friendly modern UI bubble pop (pitch sweep 280Hz -> 620Hz, 160ms)
    dur = 0.17
    n = int(SR * dur)
    out = [0.0] * (2 * n)
    phase = 0.0
    for i in range(n):
        t = i / SR
        env = math.sin(min(1.0, t / 0.012) * math.pi / 2) * math.exp(-t * 28.0)
        freq = 270.0 + 380.0 * (1.0 - math.exp(-t * 42.0))
        phase += 2.0 * math.pi * freq / SR
        s = (math.sin(phase) + 0.25 * math.sin(phase * 2.0)) * env * 0.65
        out[2 * i] = s
        out[2 * i + 1] = s
    write_wav_and_mp3("pop", out)


def gen_click():
    # Subtle tactile UI click (80ms)
    dur = 0.085
    n = int(SR * dur)
    out = [0.0] * (2 * n)
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 65.0)
        s = (
            0.55 * math.sin(2 * math.pi * 1150 * t)
            + 0.35 * math.sin(2 * math.pi * 2300 * t)
        ) * env * 0.55
        out[2 * i] = s
        out[2 * i + 1] = s
    write_wav_and_mp3("click", out)


def gen_chime():
    # Warm harmonic notification/success two-note chime (E5 -> B5, 580ms)
    dur = 0.62
    n = int(SR * dur)
    out = [0.0] * (2 * n)
    notes = [(0.0, 659.25, 0.50), (0.11, 987.77, 0.45), (0.11, 1318.51, 0.22)]
    for i in range(n):
        t = i / SR
        l = 0.0
        r = 0.0
        for start, f, amp in notes:
            if t >= start:
                dt = t - start
                env = (1.0 - math.exp(-dt * 90.0)) * math.exp(-dt * 6.5)
                val = (math.sin(2 * math.pi * f * dt) + 0.18 * math.sin(4 * math.pi * f * dt)) * env * amp
                l += val
                r += val * (0.95 if f > 900 else 1.0)
        out[2 * i] = l * 0.55
        out[2 * i + 1] = r * 0.55
    write_wav_and_mp3("chime", out)


def gen_whoosh():
    # Silky soft air whoosh (filtered pink-ish noise swell, 420ms)
    dur = 0.44
    n = int(SR * dur)
    out = [0.0] * (2 * n)
    random.seed(42)
    lp1 = lp2 = 0.0
    for i in range(n):
        t = i / SR
        p = t / dur
        env = math.sin(p * math.pi) ** 1.7
        # Sweep cutoff up then down
        alpha = 0.04 + 0.22 * math.sin(p * math.pi)
        noise = random.uniform(-1.0, 1.0)
        lp1 += alpha * (noise - lp1)
        lp2 += alpha * (lp1 - lp2)
        hp = lp1 - lp2 * 0.85
        # Soft sub-air tone
        air = math.sin(2 * math.pi * (140 + 180 * p) * t) * 0.12
        s = (hp * 1.4 + air) * env * 0.55
        pan = 0.35 + 0.3 * p
        out[2 * i] = s * (1.0 - pan * 0.25)
        out[2 * i + 1] = s * (0.75 + pan * 0.25)
    write_wav_and_mp3("whoosh", out)


def gen_bgm_loop():
    # Generate a clean, warm, uplifting corporate/tech 16-second seamless loop (Cadd9 - G - Am7 - Fmaj7 at 90 BPM)
    # Then tile cleanly to 278 seconds with ffmpeg so it's fast and super smooth!
    bpm = 90.0
    beat = 60.0 / bpm
    loop_beats = 16  # 4 chords x 4 beats = 10.6667s -> 32 beats = 21.3333s
    loop_dur = 32 * beat
    n = int(SR * loop_dur)
    out = [0.0] * (2 * n)

    # 8 bars (each 4 beats): Cmaj7, G6, Am7, Fmaj7, Cmaj7, Em7, Fmaj7, G6
    chords = [
        [261.63, 329.63, 392.00, 493.88],  # Cmaj7
        [196.00, 293.66, 392.00, 493.88],  # G
        [220.00, 261.63, 329.63, 392.00],  # Am7
        [174.61, 261.63, 329.63, 440.00],  # Fmaj7
        [261.63, 329.63, 392.00, 523.25],  # C
        [164.81, 246.94, 329.63, 392.00],  # Em7
        [174.61, 261.63, 349.23, 440.00],  # F
        [196.00, 293.66, 392.00, 440.00],  # Gsus2
    ]

    # Gentle arpeggio pattern per 4-beat bar (eighth notes)
    arp_idx = [0, 1, 2, 3, 2, 1, 2, 3]
    bar_dur = 4 * beat
    eighth = beat / 2.0

    for i in range(n):
        t = i / SR
        bar = min(7, int(t / bar_dur))
        bt = t - bar * bar_dur
        ch = chords[bar]

        # 1. Warm slow breathing pad
        pad_env = math.sin(min(1.0, bt / 0.35) * math.pi / 2) * (
            1.0 - 0.15 * max(0.0, (bt - (bar_dur - 0.35)) / 0.35)
        )
        pad_l = 0.0
        pad_r = 0.0
        for idx, f in enumerate(ch):
            # Subtle stereo detune for lushness
            pad_l += math.sin(2 * math.pi * (f * 0.5) * t + idx * 0.4) * 0.11
            pad_r += math.sin(2 * math.pi * (f * 0.5012) * t + idx * 0.7) * 0.11
        pad_l *= pad_env
        pad_r *= pad_env

        # 2. Soft muted electric-piano / marimba pluck on eighth notes
        step_i = int(bt / eighth)
        st_t = bt - step_i * eighth
        pf = ch[arp_idx[step_i % len(arp_idx)]]
        pluck_env = (1.0 - math.exp(-st_t * 110.0)) * math.exp(-st_t * 7.5)
        pluck = (math.sin(2 * math.pi * pf * st_t) + 0.15 * math.sin(4 * math.pi * pf * st_t)) * pluck_env * 0.17

        # 3. Very gentle soft pulse on beats 1 and 3
        beat_in_bar = int(bt / beat)
        b_t = bt - beat_in_bar * beat
        pulse = 0.0
        if beat_in_bar in (0, 2):
            p_env = math.exp(-b_t * 22.0)
            pulse = math.sin(2 * math.pi * (68.0 + 35.0 * math.exp(-b_t * 30.0)) * b_t) * p_env * 0.18

        out[2 * i] = pad_l + pluck * 0.9 + pulse
        out[2 * i + 1] = pad_r + pluck * 1.1 + pulse

    loop_wav = os.path.join(SFX_DIR, "bgm_loop.wav")
    with wave.open(loop_wav, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        peak = max((abs(x) for x in out), default=1.0)
        scale = 0.75 / peak
        buf = bytearray()
        for i in range(0, len(out), 2):
            l = max(-1.0, min(1.0, out[i] * scale))
            r = max(-1.0, min(1.0, out[i + 1] * scale))
            buf.extend(struct.pack("<hh", int(l * 32767), int(r * 32767)))
        wf.writeframes(buf)

    bgm_mp3 = os.path.join(SFX_DIR, "bgm_ambient.mp3")
    # Tile seamlessly to 276s with gentle fade-in (1.5s) and fade-out (3.0s)
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-stream_loop",
            "14",
            "-i",
            loop_wav,
            "-t",
            "275.5",
            "-af",
            "lowpass=f=3200,afade=t=in:st=0:d=1.5,afade=t=out:st=272.0:d=3.5",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "160k",
            bgm_mp3,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.remove(loop_wav)
    print("[OK] bgm_ambient.mp3 (275.5s)")


if __name__ == "__main__":
    gen_pop()
    gen_click()
    gen_chime()
    gen_whoosh()
    gen_bgm_loop()
