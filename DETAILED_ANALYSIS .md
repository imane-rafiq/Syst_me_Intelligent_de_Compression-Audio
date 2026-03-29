# 📊 Analyse Détaillée: Système Intelligent de Compression Audio

Ce rapport couvre les résultats, les métriques et les capacités complètes du "Système Intelligent de Compression Audio Multi-Agents" développé dans le cadre du cours de Transmission de Données Multimédia (Licence IRM - FSTM).

---

## SECTION 1: ARCHITECTURE MULTI-AGENTS
Gérée et documentée en profondeur dans `ARCHITECTURE.md`. Il y a 5 agents implémentés orchestrés via Rest/JSON ou instanciés de bas-niveau par la classe `AudioCompressionOrchestrator`.

---

## SECTION 2: INTÉGRATION DU LLM (Intelligence Artificielle)

Le système intègre l'intelligence générative comme cerveau de son architecture "DecisionMaker", utilisant un agent prompté de type Expert.

**LLM UTILISÉ:** Claude-3.5-Sonnet (20241022) / Deepgram (pour Speech-to-Text)
**Provider:** Anthropic / Deepgram
**Version:** Rest API / SDK Python (v0.5.0 pour Anthropic)

### FONCTIONNALITÉS:
- Analyse technique de données purement chiffrées (pas de LLM "Audio-MutiModal", le LLM lit un log d'extraction FFT transformé en JSON)
- Sélection des paramètres du processus compressif (Sample Rate, Codec, Bitrate).
- Justification claire et technique du choix permettant d'alimenter les logs utilisateurs.
- Fallbacks de sécurité internes en code dur au cas où les serveurs Cloud sont défaillants.

### PROMPT SYSTEM UTILISÉ:
```text
You are an expert audio compression engineer.

Audio Information:
{JSON de l'agent 1 InputMetadata}

Audio Features:
{JSON de l'agent 2 librosa extraction}

Analyze this audio and decide the best compression parameters.

Guidelines:
- Voice/Speech: Prefer Opus codec, 32-96 kbps, mono allowed
- Music: Prefer AAC or MP3, 128-256 kbps, maintain stereo
- Ambient/Nature: MP3 or OGG, 96-128 kbps
- Mixed content: AAC at 128 kbps as balanced choice
- High-quality requirement: Consider FLAC (lossless)

Return ONLY valid JSON (no explanation):
{
    "codec": "opus|aac|mp3|ogg|flac",
    "bitrate": 32|48|64|96|128|192|256,
    "sample_rate": [metadata hz],
    "channels": 1|2,
    "reasoning": "brief explanation..."
}
```

### GESTION DES TOKENS:
- Demande plafonnée à `max_tokens=400`
- Limite stricte pour obliger du JSON sans fioritures et limiter l'hallucination tout en minimisant les coûts inférentiels.
- Coût par requête: Inferieur à `0.005$` (Input en Token JSON très courts, Output < 100 Tks).

---

## SECTION 3: TYPES DE CONTENUS AUDIO GÉRÉS

Le système catégorise les données en 4 grandes catégories logiques via le croisement du `Zero-Crossing-Rate` et de `l'Entropie Spectrale`.

### CATÉGORIE 1: 🎙️ Enregistrements Vocaux (Voix/Podcast/VoiceNote)
**Caractéristiques détectées:**
- ZCR (Zero Crossing): `> 0.08`
- Centroïde spectral restreint: `1200 <= hz <= 3500`
- Bandwith Limitée: `< 2500 hz`
- **Recommandation Produite**: Codec **Opus**, Mono (1 Channel), Bitrate 48-64 kbps.
- **Justification**: "Opus conserve à merveille l'intelligibilité de la parole à très bas bitrate. Supprimer le channel stéréo divise automatiquement la taille de stockage par 2."

### CATÉGORIE 2: 🎼 Musique 
**Caractéristiques détectées:**
- Entropie élevée: `> 4.2`
- Large Bandwith: `> 1800 hz`
- Énergie (RMS): `> 0.01` (Évite de trigger l'audio sur des silences corrompus par du bruit blanc)
- **Recommandation Produite**: Codec **AAC**, Stereo (2 Channels), Bitrate 128-256 kbps.
- **Justification**: "Un large spectre demande de ne pas couper les hautes fréquences, l'AAC à >128kbps conserve la clarté et la spatialisation stéréo."

### CATÉGORIE 3: 🍃 Ambiance / Sons Environnementaux
**Caractéristiques détectées:**
- Énergie (RMS): `< 0.01` (Très calme, souvent non détectable comme voix ou musique)
- Entropie: `< 3.0`
- **Recommandation Produite**: Codec **MP3** ou **OGG**, Bitrate 96-128 kbps.
- **Justification**: "Les ambiances de fond n'ont pas besoin de la précision clinique de l'AAC ni du focus humain d'Opus."

### CATÉGORIE 4: 🎛️ Contenus Mixtes
- Hybridité de ZCR ou Centroïde désaxé. Mène au Codec passe-partout: **AAC 128kbps**.

---

## SECTION 4: FORMATS DE COMPRESSION SUPPORTÉS

| Format   | Qualité       | Lossy/Lossless | Cas d'Utilisation Recommandé | Points Forts du Codec dans `Execution Agent` |
| -------- | --------- | -------------- | ----------------------| ------------------------------------------- |
| **MP3**  | Good      | Lossy          | Ambiance, Legacy      | Encapsulation `libmp3lame`, universel.       |
| **AAC**  | Excellent | Lossy          | Musique, Podcast HQ   | Remplaçant d'Apple, très stable et équilibré|
| **Opus** | Excellent | Lossy          | Voix parlée, Telecom  | Indiscutablement le roi de la basse résolution|
| **OGG**  | Very Good | Lossy          | Gaming, Web Audio     | Librairie `libvorbis`, excellent à moyen bitrate|
| **FLAC** | Perfect   | Lossless       | Studio, Archive de Test | Aucun bitrate spécifié car compression sans pertes (algorithmique) |

*Contraintes FFmpeg du projet:* Si un format n'est pas supporté (ex: choix halluciné par l'IA de type "ALAC"), le système force automatiquement un **Fallback vers l'AAC** (standard web universel).

---

## SECTION 5: CARACTÉRISTIQUES AUDIO EXTRAITES (Librosa)

```text
CATÉGORIE: Métadonnées (ffprobe via subprocess)
├─ Durée (Float en secondes)
├─ Format d'origine & Codec Name
├─ File Size Bytes 
├─ Sample rate & Channels originaux
└─ Bit depth

CATÉGORIE: Analyse Spectrale (librosa MEL)
├─ Centroid (Centre de masse de l'énergie audio)
├─ Entropie Spectrale (Complexité, Hasard)
└─ Bande passante (Spectral Bandwith)

CATÉGORIE: Caractéristiques Temporelles
├─ Zero-crossing rate (ZCR, utile pour distinguer parole/bruit)
├─ Energy (RMS de l'amplitude totale)
└─ Peak amplitude (Highest value limit peak)
```

**Temps de calcul moyen:** Le `FeatureExtractionAgent` charge l'audio avec un cap temporel en conversion mono fixe de **44100hz**. Traitement standard Librosa : ~2.5s pour un fichier de 3 minutes sur CPU.

---

## SECTION 6: MÉTRIQUES DE QUALITÉ IMPLÉMENTÉES

### RÉDUCTION / TAUX DE COMPRESSION (τ)
- **Formule**: `τ = (1.0 - (Taille_compressée / Taille_originale))` affiché en % de `Compression_Ratio`.
- **Interprétation**: Si τ = 0.833, alors le fichier a perdu 83.3% de sa taille originelle. 
- **Code**: Présent explicitement ligne 72 de `execution_agent.py` => `compression_ratio = (1.0 - (compressed_size / original_size))`

### SNR (Signal-to-Noise Ratio)
- **Formule Numérique (DB)**: `10 * log10(Puissance_Signal_Original / Puissance_Erreur)`
- **Interprétation**: L'erreur correspond à la distance euclidienne de soustraction `(Signal_Pur - Signal_Compressé)`. Plus l'erreur introduite par le codec à perte (Lossy) est faible, plus le SNR est haut (Meilleure Qualité).
- **Implémentation**: Présent explicitement ligne 116 de `report_agent.py` => `snr = 10 * np.log10(signal_power / noise_power)`
- **Seuils observés**:
  - `> 30 dB`: Excellent / Indistinguable à l'oreille non entraînée.
  - `20 - 30 dB`: Moyen à Bon / Légères perturbations algorithmiques (artefacts codec aigus).
  - `< 15 dB`: Faible / Perte claire de dynamique audio (Low Bitrate brut).

---

## SECTION 7: RÉSULTATS HYPOTHÉTIQUES INTÉGRATION CONTINUE (Tests de Validation)

*(Basé sur les standards attendus pour l'infrastructure développée).*

**Comparaison de Performance Théorique par Codecs selon les règles de ce code:**

┌────────┬──────────────┬──────────┬─────────────┬────────────┐
│ Codec  │ Catégorie    │ τ attendu│ SNR Théor.  │ Temps Moy  │
├────────┼──────────────┼──────────┼─────────────┼────────────┤
│ Opus   │ Voice        │ 85-92%   │ 28-32 dB    │ Très Rapide│
│ AAC    │ Music        │ 60-70%   │ 35-40 dB    │ Standard   │
│ MP3    │ Ambiance     │ 75-80%   │ 25-28 dB    │ Stand/Rapide│
│ FLAC   │ Music / Mixte│ 35-45%   │ Infinity*   │ Lent       │
└────────┴──────────────┴──────────┴─────────────┴────────────┘
*(Infinity: Flac étant lossless, le bruit est theoriquement nul si le Sample Rate Source = Target).*

---

## SECTION 8: DIFFICULTÉS ET SOLUTIONS IDENTIFIÉES

**1. Problème: OOM (Out of Memory) lors de l'Analyse SNR**
- **Cause**: L'Agent 5 `Report` utilisait `librosa.load()` avec `sr=None` qui charge le fichier entier non compressé en RAM de façon pure sur 64 bits Floating Points.
- **Solution appliquée**: Utilisation de slices `min_len = min(len(y_original), len(y_compressed))` avant l'opération mathématique pour éviter un crash complet dû à une latence ou à un sample rate de sortie différent.

**2. Problème: Coût et latence API LLM**
- **Cause**: Le LLM renvoyait du texte "Markdown" (du type "Here is your JSON:") ou des explications de 4 pages.
- **Solution appliquée**: Un try/except de parsing robuste (`split('```json')`) et le fallback hardcodé si le Json Decode Crash ou si `response.status_code != 200` garantissant une exécution 100% autonome à faible coût.

**3. Problème: Timeout FFprobe**
- **Solution appliquée**: Paramétrage strict d'un timeout=15s dans le code de process d'`input_agent.py`.

---

## SECTION 9: RECOMMANDATIONS FUTURES

1. **Intégration TensorBoard/Matplotlib**: Ajouter à l'agent de reporting un plot de comparaison spectrale d'avant/après compression et le parser via FastAPI (Static files display).
2. **Caching LLM Intelligent**: Empêcher le LLM d'être rappelé pour des features spectro-temporelles qui sont de ressemblance euclidienne quasi similaire (Clusterisation des décisions au delà de 10k fichiers traités).
3. **Métrique PESQ (Perceptual Evaluation of Speech Quality)**: Pousser l'analyse au delà du SNR (Signal Bruit Brut) par l'utilisation de tests algorithmiques sur la base de la psychoacoustique humaine. (ex: la librairie pypesq).
