# Results

This directory contains the output files produced by the Système Intelligent de Compression Audio.

## How to Generate Results

### Demo output (synthetic signals)

```bash
python main.py demo --output-dir results/
```

This produces:

| File | Description |
|------|-------------|
| `original.wav` | Original 2-second synthetic test signal (440 Hz + 1 kHz + 4 kHz mix) |
| `reconstructed_q4.wav` | Reconstructed at quality level 4 (high compression) |
| `reconstructed_q8.wav` | Reconstructed at quality level 8 (balanced) |
| `reconstructed_q12.wav` | Reconstructed at quality level 12 (high quality) |

### Benchmark table

```bash
python main.py benchmark
```

Prints a table like the following (actual values may vary):

```
=================================================================
  Signal: sine_440Hz  (44,100 samples)
=================================================================
 Quality     Ratio   Saving%     SNR(dB)   Enc(ms)   Dec(ms)
-----------------------------------------------------------------
       1      8.12     87.7%       8.43      45.3      12.1
       2      7.95     87.4%      10.12      44.8      12.0
       4      6.34     84.2%      14.78      43.2      11.9
       6      5.12     80.5%      19.34      43.1      11.7
       8      3.87     74.2%      25.61      42.9      11.6
      10      2.89     65.4%      31.23      43.0      11.8
      12      2.01     50.3%      38.45      43.5      11.9
      14      1.52     34.2%      45.12      44.1      12.1
      16      1.08      7.4%      58.33      45.2      12.5
```

## Metrics Explained

| Metric | Definition |
|--------|-----------|
| **Compression Ratio** | Original bits / Compressed bits (higher = more compressed) |
| **Space Saving (%)** | `(1 − ratio⁻¹) × 100` |
| **SNR (dB)** | Signal-to-Noise Ratio — higher is better quality |
| **PSNR (dB)** | Peak Signal-to-Noise Ratio — higher is better |
| **Enc / Dec time** | Encoding and decoding wall-clock time in milliseconds |

## Quality vs. Compression Trade-off

The system exposes 16 quality levels that control the number of quantisation bits:

| Quality | Quant. bits | Expected SNR range |
|---------|------------|-------------------|
| 1–3     | 3–4        | 5–12 dB           |
| 4–7     | 5–6        | 12–22 dB          |
| 8–11    | 7–9        | 22–35 dB          |
| 12–16   | 10–16      | 35–60+ dB         |
