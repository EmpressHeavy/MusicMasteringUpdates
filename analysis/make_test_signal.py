#!/usr/bin/env python3
"""Generate a 20 s stereo test file: 100 Hz + 1 kHz tones, pink-ish noise, a loud section, 2 clipped bursts."""
import numpy as np, soundfile as sf, sys
sr = 48000; t = np.arange(20 * sr) / sr; rng = np.random.default_rng(1)
tone = 0.2 * np.sin(2 * np.pi * 100 * t) + 0.1 * np.sin(2 * np.pi * 1000 * t)
noise = np.cumsum(rng.standard_normal(len(t))); noise -= np.convolve(noise, np.ones(200) / 200, "same"); noise *= 0.05 / noise.std()
env = np.where((t > 8) & (t < 14), 2.0, 0.6)
L = env * (tone + noise); R = env * (tone + 0.8 * noise + 0.02 * rng.standard_normal(len(t)))
x = np.clip(np.stack([L, R], 1), -1, 1)
sf.write(sys.argv[1] if len(sys.argv) > 1 else "test_signal.wav", x, sr, subtype="PCM_24")
