# 📚 API Reference Documentation

Ce document liste l'exhaustivité des endpoints exposés par l'application FastAPI **Audio Compression Multi-Agent System** (`agents_main.py`).

L'URL de base standard en développement est : `http://localhost:8000`

---

## 🛠 Endpoints Système

### GET `/health`
Check-up global de l'état de l'API.

- **Réponse attendue (200 OK)** :
```json
{
  "status": "ok",
  "service": "Audio Compression Multi-Agent System",
  "agents": ["Input", "FeatureExtraction", "Decision", "Execution", "Report"]
}
```

### GET `/`
Documentation et listing des routes (racine de l'API).

---

## 🤖 1. Input Agent

### POST `/input/load`
Vérifie la présence du fichier audio, exécute `ffprobe` et génère les métadonnées basiques (Sample Rate, Channels, Durée).

**Request Body (`application/json`) :**
```json
{
  "filepath": "/chemin/absolu/vers/audio.wav"
}
```

**Response (`200 OK`) :**
```json
{
  "filepath": "/chemin/absolu/vers/audio.wav",
  "filename": "audio.wav",
  "duration": 12.5,
  "sample_rate": 44100,
  "channels": 2,
  "codec": "pcm_s16le",
  "filesize_bytes": 1500000,
  "filesize_mb": 1.43
}
```

---

## 🤖 2. Feature Extraction Agent

### POST `/features/extract`
Analyse le fichier audio avec `librosa` et extrait les Features temporelles et spectrales.

**Request Body (`application/json`) :**
```json
{
  "filepath": "/chemin/absolu/vers/audio.wav"
}
```

**Response (`200 OK`) :**
```json
{
  "filepath": "/chemin/absolu/vers/audio.wav",
  "centroid": 1850.3,
  "entropy": 4.1,
  "zero_crossing_rate": 0.08,
  "rms_energy": 0.2,
  "spectral_bandwidth": 2100.0,
  "content_type": "voice", 
  "peak_amplitude": 0.95
}
```
*Note: `content_type` peut être: "voice", "music", "ambient" ou "mixed".*

---

## 🤖 3. Decision Agent

### POST `/decision/decide`
Transmet les métadonnées et features à l'IA Claude (Anthropic) pour déterminer la meilleure stratégie de compression. Si les paramètres `metadata` et `features` ne sont pas envoyés, l'API cherchera par défaut dans le dossier `data/manifests/`.

**Request Body (`application/json`) :**
```json
{
  "filepath": "/chemin/absolu/vers/audio.wav",
  "metadata": { /* Optionnel si ffprobe tourne via /input/load */ },
  "features": { /* Optionnel si librosa a tourné via /features/extract */ }
}
```

**Response (`200 OK`) :**
```json
{
  "codec": "opus",
  "bitrate": 64,
  "sample_rate": 24000,
  "channels": 1,
  "reasoning": "Voice detected. Opus codec with mono compression maintains intelligibility while saving space."
}
```

---

## 🤖 4. Execution Agent

### POST `/execution/compress`
Créé une instance `FFmpeg` et applique concrètement la compression selon les paramètres définis à l'étape précédente.

**Request Body (`application/json`) :**
```json
{
  "filepath": "/chemin/absolu/vers/audio.wav",
  "codec": "opus",
  "bitrate": 64,
  "sample_rate": 24000,
  "channels": 1
}
```

**Response (`200 OK`) :**
```json
{
  "output_filepath": "data/outputs/audio_compressed.opus",
  "output_filename": "audio_compressed.opus",
  "compressed_size": 250000,
  "original_size": 1500000,
  "compression_ratio": 0.833
}
```

---

## 🤖 5. Report Agent

### POST `/report/generate`
Compare algébriquement le fichier source et génère un rapport final (calcul du SNR en dB).

**Request Body (`application/json`) :**
```json
{
  "original_filepath": "/chemin/absolu/vers/audio.wav",
  "compressed_filepath": "data/outputs/audio_compressed.opus"
}
```

**Response (`200 OK`) :**
```json
{
  "filename": "audio.wav",
  "duration": 12.5,
  "compression_ratio": 0.833,
  "original_size_mb": 1.43,
  "compressed_size_mb": 0.24,
  "snr_db": 34.2,
  "bitrate_kbps": 64,
  "codec": "opus",
  "report_file": "data/outputs/audio_report.json"
}
```
