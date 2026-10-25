# Measured timings

One 53-second-ish reel per style from `examples/volcanoes.md`. App/LLM box: ARM mini-PC (121 GB unified memory). GPU box: RTX 3090 24 GB
(thermally throttled during these runs, see README). Seconds, wall-clock, single job at a time.

| Style | Video | Total | Script+fact-check | Voice | Visuals | Vision QA + redo | Music | Assemble+mix | Verify | LUFS | Check |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chalkboard | 50 s | **146 s** | 55 | 30 | 12 | 0 | 7 | 4 | 38 | -16.3 | OK |
| cinematic | 51 s | **2108 s** | 87 | 29 | 1477 | 64 | 26 | 27 | 38 | -16.1 | OK |
| clay | 56 s | **344 s** | 51 | 31 | 88 | 91 | 20 | 26 | 38 | -16.2 | OK |
| flat | 49 s | **163 s** | 55 | 31 | 11 | 0 | 21 | 4 | 42 | -16.2 | OK |
| kinetic | 50 s | **131 s** | 49 | 29 | 10 | 0 | 7 | 4 | 33 | -16.2 | OK |
| papercut | 54 s | **274 s** | 54 | 31 | 81 | 35 | 16 | 25 | 34 | -16.3 | OK |
| pixel | 50 s | **308 s** | 58 | 29 | 100 | 45 | 20 | 16 | 40 | -16.4 | OK |
| watercolor | 54 s | **336 s** | 67 | 30 | 122 | 32 | 20 | 26 | 38 | -16.0 | OK |
