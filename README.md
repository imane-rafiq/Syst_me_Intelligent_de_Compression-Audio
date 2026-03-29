# Système Intelligent de Compression Audio

An academic implementation of an **Intelligent Audio Compression System** using
block-DCT, psychoacoustic masking, and Huffman entropy coding — in pure Python.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Quick Start](#quick-start)
7. [Usage](#usage)
8. [How It Works](#how-it-works)
9. [Results](#results)
10. [Running the Tests](#running-the-tests)

---

## Overview

This project implements a perceptual audio compression pipeline inspired by
industry standards such as MP3 and AAC.  The system exploits properties of
human auditory perception to discard information that is inaudible, while
preserving the perceptually relevant content.

Key capabilities:

| Feature | Description |
|---------|-------------|
| **Block-DCT compression** | Audio is segmented into frames; each frame is transformed with the Type-II DCT, quantised, and entropy-coded. |
| **Psychoacoustic masking** | A Bark-scale spreading model determines the masking threshold for each frequency bin, enabling perceptually-guided quantisation. |
| **Huffman entropy coding** | Quantised DCT coefficients are compressed with an optimal prefix-free Huffman code. |
| **Adjustable quality** | 16 quality levels trade compression ratio against signal-to-noise ratio (SNR). |
| **WAV I/O** | Load and save standard 16-bit PCM WAV files without external libraries. |

---

## Architecture

```
Audio input (WAV)
      │
      ▼
┌─────────────────────┐
│   Frame segmentation│  (overlapping blocks, sine window)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Block DCT (Type II)│
└────────┬────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│  Psychoacoustic model                │
│  • FFT power spectrum                │
│  • Bark-scale spreading function     │
│  • Masking threshold per bin         │
│  → Perceptual weights ∈ (0, 1)      │
└────────┬─────────────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Scalar quantisation│  (step size guided by perceptual weights)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Huffman encoding   │  (entropy coding of quantised integers)
└────────┬────────────┘
         │
         ▼
  Compressed bitstream (.sica)


Decompression reverses each stage:
  Huffman decode → Dequantise → IDCT → Overlap-add → WAV output
```

---

## Project Structure

```
.
├── main.py                       # CLI entry point
├── requirements.txt              # Python dependencies
├── src/
│   ├── __init__.py
│   ├── audio_compression.py      # High-level AudioCompressor API
│   ├── dct_compression.py        # Block-DCT encoder / decoder
│   ├── huffman.py                # Huffman encoder / decoder
│   ├── psychoacoustic_model.py   # Bark-scale masking model
│   └── utils.py                  # Audio I/O and quality metrics
├── tests/
│   ├── test_audio_compression.py
│   ├── test_compression.py
│   ├── test_huffman.py
│   └── test_utils.py
└── results/
    └── README.md                 # How to reproduce results
```

---

## Requirements

- Python ≥ 3.8
- [NumPy](https://numpy.org/) ≥ 1.22
- [SciPy](https://scipy.org/) ≥ 1.8
- [pytest](https://pytest.org/) ≥ 7.0 *(for tests only)*

---

## Installation

```bash
# Clone the repository
git clone https://github.com/imane-rafiq/Syst-me-Intelligent-de-Compression-Audio.git
cd Syst-me-Intelligent-de-Compression-Audio

# Install dependencies
pip install -r requirements.txt
```

---

## Quick Start

### Run the built-in demo

```bash
python main.py demo
```

Expected output:

```
============================================================
  Système Intelligent de Compression Audio — Demo
============================================================

Test signal : 440 Hz + 1 kHz + 4 kHz sine mix
Duration    : 2 seconds  |  Sample rate: 44100 Hz
Samples     : 88,200

 Quality     Ratio    Saving%     SNR(dB)    PSNR(dB)
-------------------------------------------------------
       2      7.67      87.0%       12.44       19.70
       4      7.51      86.7%       17.91       25.16
       6      7.32      86.3%       18.15       25.41
       8      7.10      85.9%       18.42       25.68
      10      6.57      84.8%       18.85       26.10
      12      5.87      83.0%       18.86       26.12
      14      5.06      80.2%       18.93       26.19
```

### Compress a WAV file

```bash
python main.py compress my_audio.wav --quality 8 --output my_audio.sica
```

### Decompress back to WAV

```bash
python main.py decompress my_audio.sica --output reconstructed.wav
```

---

## Usage

```
usage: main.py {compress,decompress,demo,benchmark} ...

Sub-commands:

  compress      Compress a WAV file to .sica format
  decompress    Decompress a .sica file back to WAV
  demo          Run a demonstration with synthetic signals
  benchmark     Benchmark all 16 quality levels
```

### `compress`

```
python main.py compress INPUT_WAV [options]

Options:
  --quality, -q [1-16]   Compression quality (1=highest compression,
                         16=near-lossless). Default: 8
  --frame-size, -f INT   DCT frame size in samples. Default: 1024
  --output, -o PATH      Output .sica file. Default: <input>.sica
  --no-psycho            Disable psychoacoustic masking
```

### `decompress`

```
python main.py decompress INPUT_SICA [options]

Options:
  --output, -o PATH      Output WAV file. Default: <input>_reconstructed.wav
```

### `demo`

```
python main.py demo [options]

Options:
  --output-dir, -o DIR   Save demo WAV files to DIR
```

### `benchmark`

```
python main.py benchmark
```

Prints a full table of compression ratio, space saving, SNR, and
encode/decode times for all 16 quality levels on two test signals.

---

## How It Works

### 1. Frame Segmentation

The audio signal is split into overlapping frames of `frame_size` samples
with a 50 % hop (overlap).  A **sine window** `w[n] = sin(π(n+0.5)/N)` is
applied before the DCT.  The sine window satisfies:

```
w[n]² + w[n + N/2]² = 1  for all n
```

which guarantees **perfect reconstruction** from the overlap-add synthesis
step (in the absence of quantisation error).

### 2. DCT Transform

The Type-II DCT with orthonormal normalisation converts the windowed time-
domain frame into frequency-domain coefficients.  Low-frequency coefficients
carry most of the signal energy.

### 3. Psychoacoustic Masking (optional)

For each frame, the model:
1. Computes the short-time power spectrum via FFT.
2. Maps each frequency bin to the **Bark scale** (Zwicker formula).
3. Applies a **spreading function** that models simultaneous masking:
   - Lower slope: 27 dB/Bark (masker masks lower frequencies weakly).
   - Upper slope: 6 dB/Bark (masker masks higher frequencies strongly).
4. Combines the spread power with the **absolute threshold of hearing** (ATH).
5. Produces a **perceptual weight** ∈ (0, 1) per DCT bin.

Coefficients with low perceptual weight are quantised more coarsely,
exploiting *just-noticeable differences*.

### 4. Scalar Quantisation

A uniform scalar quantiser maps each DCT coefficient to an integer index.
The global quantisation step is derived from the coefficient range and the
number of quantisation bits determined by the quality level.

When psychoacoustic weighting is enabled, the effective step per coefficient
is modulated by the perceptual weight — audible coefficients get finer steps.

### 5. Huffman Entropy Coding

The quantised integer indices are entropy-coded using an optimal Huffman code
built from the symbol frequency histogram of each compressed signal.  The
resulting bit savings depend on the distribution of quantised values.

### 6. Reconstruction

Decoding reverses the pipeline:
1. **Huffman decode** → quantised integers.
2. **Dequantise** (multiply by step size) → DCT coefficients.
3. **IDCT** → windowed time-domain frames.
4. **Weighted overlap-add** → full-length audio signal.

---

## Results

See [`results/README.md`](results/README.md) for instructions on reproducing
the benchmark results and a description of the output files.

### Typical performance (440 Hz sine, 44 100 Hz, 1 s)

| Quality | Ratio | Space Saving | SNR (dB) |
|---------|-------|-------------|---------|
| 2       | 7.88× | 87.3 %      | 8.2 dB  |
| 6       | 7.72× | 87.0 %      | 17.2 dB |
| 10      | 7.38× | 86.5 %      | 19.4 dB |
| 14      | 6.46× | 84.5 %      | 19.1 dB |
| 16      | 5.26× | 81.0 %      | 19.1 dB |

---

## Running the Tests

```bash
# Run all tests
pytest tests/ -v

# Run a specific test module
pytest tests/test_huffman.py -v

# Run with coverage (requires pytest-cov)
pytest tests/ --cov=src
```

The test suite covers:
- Huffman encoder/decoder correctness and prefix-free property
- DCT compressor roundtrip and SNR quality
- Psychoacoustic model outputs and Bark-scale conversion
- Audio I/O roundtrip (WAV save/load)
- Quality metric formulas (SNR, PSNR, compression ratio, space saving)
