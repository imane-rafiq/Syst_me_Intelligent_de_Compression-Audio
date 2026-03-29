# 🎵 Système Intelligent de Compression Audio Multi-Agents

Bienvenue dans la documentation du **Système Intelligent de Compression Audio Multi-Agents**. Ce projet universitaire (Université Hassan II de Casablanca - FSTM, Licence IRM) implémente une architecture multi-agents pilotée par l'Intelligence Artificielle (Claude d'Anthropic / Deepgram) pour analyser, décider, compresser et évaluer des fichiers audio de manière autonome.

---

## 🚀 Fonctionnalités Principales

- **Analyse Audio Avancée** : Extraction de caractéristiques spectrales et temporelles (Centroid, Entropy, ZCR) et détection intelligente du type de contenu (Voix, Musique, Ambiance, Mixte).
- **Décision via IA Générative** : Utilisation d'un LLM (Claude-3.5-Sonnet) pour choisir le meilleur codec (Opus, AAC, MP3, OGG, FLAC) et bitrate en fonction du profil audio.
- **Compression Automatique** : Exécution optimisée via `FFmpeg`.
- **Évaluation de la Qualité** : Calcul du Taux de Compression (τ) et du Signal-to-Noise Ratio (SNR).
- **Architecture Multi-Agents via FastAPI** : Chaque agent est exposé comme un micro-service RESTful indépendant.

---

## 🛠 Prérequis et Installation

### 1. Prérequis Système
- **Python 3.8+**
- **FFmpeg** (Doit être installé et accessible dans les variables d'environnement `PATH`).

### 2. Installation de l'environnement

```bash
# 1. Cloner le projet (si hébergé) ou se rendre dans le dossier
cd AUDIO_V_FINAL

# 2. Créer un environnement virtuel
python -m venv venv

# 3. Activer l'environnement virtuel
# Sur Windows :
venv\Scripts\activate
# Sur Linux/macOS :
source venv/bin/activate

# 4. Installer les dépendances
pip install -r requirements.txt
```

### 3. Configuration des Variables d'Environnement

Créez un fichier `.env` à la racine du projet (copiez `.env.example` s'il existe) :

```env
# Clé API pour le Decision Agent
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=votre_cle_gemini_si_besoin
GOOGLE_API_KEY=votre_cle_google_si_besoin

# Port de l'API
AGENTS_PORT=8000
```

---

## 🏃 Utilisation

### Démarrage des Agents (Mode API REST)

L'ensemble des agents est orchestré au sein d'une seule application FastAPI.

```bash
uvicorn agents_main:app --reload --port 8000
# ou simplement
python agents_main.py
```

L'API est maintenant accessible sur `http://localhost:8000/`.
Vous pouvez consulter la documentation Swagger interactive sur `http://localhost:8000/docs`.

### Démarrage en ligne de commande (Mode Pipeline Complet)

Vous pouvez lancer un flux complet de compression de l'analyse jusqu'au rapport :

```bash
python orchestrator.py
```
*(Assurez-vous de modifier le chemin du fichier d'entrée dans la méthode `__main__` du fichier avant de l'exécuter).*

---

## 🏗 Structure du Projet

```text
AUDIO_V_FINAL/
├── agents_main.py            # Entry point FastAPI exposant tous les agents
├── orchestrator.py           # Script pour l'exécution locale du pipeline complet
├── api.py                    # Définition potentielle d'anciennes routes ou websockets
├── requirements.txt          # Liste des dépendances pip
├── .env                      # Variables d'environnement (API Keys)
├── agents/                   # Code source de chaque agent
│   ├── input_agent.py        # Validation & Métadonnées
│   ├── feature_extraction_agent.py # Extraction spectral et temporel
│   ├── decision_agent.py     # Communication Claude (LLM) / Deepgram
│   ├── execution_agent.py    # Wrapping de la commande FFmpeg
│   └── report_agent.py       # SNR & Quality report
└── data/                     # Généré automatiquement
    ├── audio_files/          # Fichiers audio d'entrée attendus
    ├── manifests/            # JSON générés entre les étapes
    └── outputs/              # Fichiers finaux compréssés et rapports
```

---

## 🚑 Troubleshooting & Problèmes Fréquents

1. **`ffprobe not found` ou `ffmpeg is not recognized`**
   - Causé par FFmpeg non installé ou absent du PATH Windows.
   - *Solution* : Installez FFmpeg (ex: via `winget install ffmpeg` sur Windows) et redémarrez votre terminal principal.

2. **Échec du `DecisionAgent` (LLM returning None)**
   - Causé par une absence de clé API ou de crédits Anthropic expirés.
   - *Solution* : Vérifiez `.env`. Sans clé validée, le système utilisera le système de `fallback_decision` interne qui se base sur des règles simples "If-Else".

3. **`anthropic package not installed`**
   - *Solution* : Exécutez `pip install anthropic`.

4. **L'audio de sortie est plus grand que l'audio d'entrée !**
   - *Explication* : Ce problème arrive si vous comprenez un fichier déjà hyper-compressé (ex: Opus à faible bitrate) avec un format d'export de plus haute qualité (ex: AAC 192kbps). Le système de Fallback ou les prompts de l'IA peuvent nécessiter d'être affinés pour votre jeu de données spécifique.
