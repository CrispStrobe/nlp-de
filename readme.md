# 🏛️ nlp-de

A comprehensive German NLP toolkit combining multiple linguistic analysis tools into a unified API platform. This repository contains both standalone Gradio applications and a consolidated hub that provides an integrated suite of German language processing capabilities.

[![Hugging Face Space](https://img.shields.io/badge/🤗%20Hugging%20Face-Space-blue)](https://huggingface.co/spaces/cstr/nlp-de)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
  - [Consolidated Hub (nlp-app.py)](#1-consolidated-hub-nlp-apppy)
  - [Individual Applications](#individual-applications)
- [API Reference](#api-reference)
- [Installation & Setup](#installation--setup)
- [Testing with Dart](#testing-with-dart)
- [Usage Examples](#usage-examples)
- [Performance](#performance)
- [Contributing](#contributing)
- [License](#license)

---

## 🌟 Overview

This project provides a set of linguistic analysis tools for German (and multi-lingual) text processing:

1. **🔬 spaCy Analyzer** - Multi-lingual morpho-syntactic analysis with dependency parsing and NER
2. **✅ Grammar Checker** - German grammar and spelling correction using LanguageTool
3. **📚 Inflection Engine** - Complete German word inflection tables (nouns, verbs, adjectives)
4. **📖 Thesaurus** - German OdeNet (WordNet) integration for semantic relations
5. **🎯 Comprehensive Analyzer** - Token-by-token deep analysis combining all tools

### Key Features

- ✨ **Unified API** - Single endpoint for all linguistic tools
- 🌍 **Multi-lingual Support** - spaCy models for German, English, Spanish, and Ancient Greek
- 🎨 **Rich Visualizations** - Interactive dependency trees and entity highlighting
- 🔄 **Thread-Safe** - Production-ready concurrent processing
- 📊 **Comprehensive Output** - JSON responses with detailed linguistic annotations
- 🚀 **Gradio UI** - User-friendly web interface for each tool
- 🐛 **Robust Error Handling** - Graceful degradation and informative error messages

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Consolidated Linguistics Hub                 │
│                        (nlp-app.py)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   spaCy      │  │ LanguageTool │  │  Pattern.de  │           │
│  │  Analyzer    │  │   Grammar    │  │  Inflections │           │
│  │              │  │   Checker    │  │              │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                 │
│  ┌──────────────┐  ┌────────────────────────────────┐           │
│  │   OdeNet     │  │   Comprehensive Analyzer       │           │
│  │  Thesaurus   │  │   (All Tools Combined)         │           │
│  │              │  │                                │           │
│  └──────────────┘  └────────────────────────────────┘           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                         Gradio API Layer                        │
│              /get_morphology | /check_grammar                   │
│         /get_all_inflections | /get_thesaurus                   │
│              /comprehensive_analysis                            │
└─────────────────────────────────────────────────────────────────┘
```

### Design Philosophy

- **Modularity** - Each tool is a standalone application that can be used independently
- **Consolidation** - All tools are unified in `nlp-app.py` for one-stop linguistic analysis
- **API-First** - RESTful JSON APIs for easy integration
- **Worker Threads** - Thread-safe database access for concurrent requests (OdeNet)
- **Lazy Loading** - Models loaded on-demand to optimize memory usage

---

## 🧩 Components

### 1. Consolidated Hub (`nlp-app.py`)

**The main application** - A unified Gradio interface combining all four linguistic tools plus a comprehensive analyzer.

#### Features

- 🔬 **Multi-lingual spaCy Analysis** - Morphology, syntax, dependencies, NER
- ✅ **German Grammar Checking** - Spelling, grammar, style suggestions
- 📚 **German Inflections** - Complete declension/conjugation tables
- 📖 **German Thesaurus** - Synonyms, antonyms, hypernyms, hyponyms, etc.
- 🎯 **Comprehensive Analysis** - Token-by-token deep dive with all tools

#### Technologies

- **spaCy** - Industrial-strength NLP (v3.x)
- **LanguageTool** - Grammar/spelling checker (local server)
- **Pattern.de** - German morphological analysis, we use PatternLink (text-only)
- **wn (WordNet)** - OdeNet German semantic network
- **Gradio** - Web UI and API framework

#### API Endpoints

```python
# 1. Morphological Analysis
/get_morphology(ui_lang, model_lang_key, text)

# 2. Grammar Checking  
/check_grammar(text)

# 3. Inflection Tables
/get_all_inflections(word)

# 4. Thesaurus Lookup
/get_thesaurus(word)

# 5. Comprehensive Analysis
/comprehensive_analysis(text)
```

---

### Individual Applications

Each tool is also available as a standalone Gradio application:

#### 2. spaCy Analyzer (`spacy-app.py`)

Multi-lingual morpho-syntactic analyzer with dependency parsing and named entity recognition.

**Supported Languages:**
- 🇩🇪 German (`de_core_news_md`)
- 🇬🇧 English (`en_core_web_md`)
- 🇪🇸 Spanish (`es_core_news_md`)
- 🏛️ Ancient Greek - 7 models via [greCy](https://github.com/CrispStrobe/greCy)
  - `grc_proiel_trf` (transformer-based)
  - `grc_perseus_trf` (transformer-based)
  - `grc_ner_trf` (NER specialist)
  - And 4 more...

**Output:**
- 📊 Morphological table (word, lemma, POS, tag, morphology, dependency)
- 🌳 Interactive dependency parse visualization (SVG)
- 🏷️ Named entity recognition with color-coded entities
- 📄 Complete JSON token data

**Example:**
```python
Input: "Angela Merkel war Bundeskanzlerin von Deutschland."

Output:
- "Angela Merkel" → PER (Person)
- "Deutschland" → LOC (Location)
- Dependency: war (ROOT) ← Merkel (sb) ← Angela (pnc)
- Morphology: Gender=Fem, Number=Sing, Case=Nom
```

---

#### 3. LanguageTool Grammar Checker (`languagetool-app.py`)

Professional-grade grammar and spelling checker for German text using LanguageTool's local server.

**Features:**
- ✅ Spelling corrections
- ✅ Grammar agreement checks
- ✅ Punctuation suggestions
- ✅ Style improvements
- ✅ Context-aware suggestions

**Output Format:**
```json
{
  "message": "Möglicher Tippfehler gefunden.",
  "rule_id": "GERMAN_SPELLER_RULE",
  "category": "TYPOS",
  "incorrect_text": "Huas",
  "replacements": ["Haus", "Aus", "Haas"],
  "context": "Das ist ein Huas mit großem Garten.",
  "offset": 12,
  "length": 4
}
```

**Thread-Safety:**
- Singleton pattern with lock for concurrent access
- Lazy initialization on first use
- Warm-up check to ensure rules are loaded

---

#### 4. Pattern Inflection Engine (`pattern-app.py`)

Complete German word inflection analysis using Pattern.de library.

**Capabilities:**

**Nouns:**
- Gender detection (Masculine, Feminine, Neuter)
- Full declension table (4 cases × 2 numbers)
- Definite and indefinite article forms

**Verbs:**
- Complete conjugation tables (6 persons × multiple tenses)
- Präsens, Präteritum, Imperativ
- Konjunktiv I & II
- Participles (Präsens, Perfekt)
- Full lexeme (all word forms)

**Adjectives:**
- Predicative, comparative, superlative forms
- Attributive declension (Strong, Mixed, Weak)
- All gender/case combinations

**Example:**
```python
Input: "schön"

Output:
{
  "predicative": "schön",
  "comparative": "schöner", 
  "superlative": "schönst",
  "attributive": {
    "Strong": {
      "Masculine": {
        "Nom": {"form": "schöner", "example": "schöner Tag"},
        "Acc": {"form": "schönen", "example": "schönen Tag"},
        ...
      },
      ...
    }
  }
}
```

---

#### 5. OdeNet Thesaurus (`odenet-app.py`)

German WordNet integration providing rich semantic relations via the OdeNet lexical database.

**Semantic Relations:**
- 🔄 **Synonyms** - Words with similar meaning
- ⚡ **Antonyms** - Words with opposite meaning  
- ⬆️ **Hypernyms** - More general terms ("is a type of")
- ⬇️ **Hyponyms** - More specific terms ("examples are")
- 🔗 **Holonyms** - Part-of relationships ("is part of")
- 🧩 **Meronyms** - Has-part relationships ("has parts")

**Thread-Safe Architecture:**
- Dedicated worker thread for SQLite database access
- Queue-based request handling
- No database lock contention
- Safe for concurrent Gradio requests

**Example:**
```python
Input: "Hund"

Output:
{
  "senses": [
    {
      "pos": "n",
      "definition": "Haustier aus Familie der Canidae",
      "synonyms": ["Köter", "Fiffi", "Fellnase"],
      "hypernyms": ["Haustier", "Säugetier"],
      "hyponyms": ["Schäferhund", "Pudel", "Dackel"]
    }
  ]
}
```

---

## 📡 API Reference

### 1. Get Morphology

**Endpoint:** `/get_morphology`

**Description:** Analyze text morphology, syntax, dependencies, and named entities.

**Parameters:**
- `ui_lang` (str): Interface language - `"DE"`, `"EN"`, `"ES"`
- `model_lang_key` (str): Analysis language - `"de"`, `"en"`, `"es"`, `"grc-proiel-trf"`, etc.
- `text` (str): Text to analyze

**Returns:** Tuple of 4 elements
1. Morphological table (dict with headers/data)
2. JSON token data (list of dicts)
3. Dependency parse HTML/SVG (str)
4. Named entity HTML (str)

**Python Client Example:**
```python
from gradio_client import Client

client = Client("cstr/nlp-de")
result = client.predict(
    ui_lang="EN",
    model_lang_key="de",
    text="Die Katze schläft auf dem Tisch.",
    api_name="/get_morphology"
)
table, tokens, dep_viz, ner_viz = result
```

---

### 2. Check Grammar

**Endpoint:** `/check_grammar`

**Description:** Check German text for grammar, spelling, and style errors.

**Parameters:**
- `text` (str): German text to check

**Returns:** List of error objects or `{"status": "perfect"}` if no errors

**Error Object Schema:**
```json
{
  "message": "Error description",
  "rule_id": "RULE_IDENTIFIER",
  "category": "TYPOS|GRAMMAR|STYLE",
  "incorrect_text": "erroneous text",
  "replacements": ["suggestion1", "suggestion2"],
  "offset": 12,
  "length": 4,
  "context": "surrounding text",
  "short_message": "brief summary"
}
```

**Python Client Example:**
```python
from gradio_client import Client

client = Client("cstr/nlp-de")
result = client.predict(
    text="Das ist ein Huas.",
    api_name="/check_grammar"
)
print(result)
# [{"message": "Möglicher Tippfehler...", "replacements": ["Haus", ...]}]
```

---

### 3. Get All Inflections

**Endpoint:** `/get_all_inflections`

**Description:** Generate complete inflection tables for German words.

**Parameters:**
- `word` (str): German word to inflect

**Returns:** Dict with parser hint and analysis objects

**Response Schema:**
```json
{
  "input_word": "gehen",
  "parser_hint": {
    "pos": "VB",
    "lemma": "gehen",
    "type": "verb"
  },
  "analyses": {
    "verb": {
      "infinitive": "gehen",
      "conjugation": {
        "Präsens": {"ich": "gehe", "du": "gehst", ...},
        "Präteritum": {"ich": "ging", ...},
        ...
      },
      "participles": {...},
      "lexeme": [...]
    }
  }
}
```

**Python Client Example:**
```python
from gradio_client import Client

client = Client("cstr/nlp-de")
result = client.predict(
    word="Haus",
    api_name="/get_all_inflections"
)
```

---

### 4. Get Thesaurus

**Endpoint:** `/get_thesaurus`

**Description:** Find semantic relations for German words using OdeNet WordNet.

**Parameters:**
- `word` (str): German word to look up

**Returns:** Dict with word senses and semantic relations

**Response Schema:**
```json
{
  "input_word": "gut",
  "senses": [
    {
      "pos": "a",
      "definition": "positive Charaktereigenschaft",
      "synonyms": ["herzensgut", "gütig"],
      "antonyms": ["böse", "schlecht"],
      "hypernyms (is a type of)": [...],
      "hyponyms (examples are)": [...],
      "holonyms (is part of)": [...],
      "meronyms (has parts)": [...]
    }
  ]
}
```

**Python Client Example:**
```python
from gradio_client import Client

client = Client("cstr/nlp-de")
result = client.predict(
    word="Hund",
    api_name="/get_thesaurus"
)
```

---

### 5. Comprehensive Analysis

**Endpoint:** `/comprehensive_analysis`

**Description:** Deep token-by-token analysis combining all linguistic tools.

**Parameters:**
- `text` (str): German text to analyze

**Returns:** Dict with complete analysis

**Response Schema:**
```json
{
  "input_text": "Die Katze schläft.",
  "grammar_check": [...],
  "spacy_analysis": [...],
  "token_deep_dive": [
    {
      "word": "Katze",
      "spacy_pos": "NOUN",
      "spacy_lemma": "Katze",
      "pattern_analyses": {
        "noun": {
          "gender": "Feminine",
          "declension": {...}
        }
      },
      "thesaurus_senses": [...]
    }
  ]
}
```

**Python Client Example:**
```python
from gradio_client import Client

client = Client("cstr/nlp-de")
result = client.predict(
    text="Der schnelle Fuchs springt.",
    api_name="/comprehensive_analysis"
)
```

---

## 🚀 Installation & Setup

### Prerequisites

- Python 3.10+
- pip package manager
- 8GB+ RAM recommended (for spaCy models)

### Local Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/nlp-hub.git
cd nlp-hub

# Install Python dependencies
pip install -r requirements.txt

# Download spaCy models
python -m spacy download de_core_news_md
python -m spacy download en_core_web_md
python -m spacy download es_core_news_md

# Download WordNet data (automatic on first use)
# The app will download OdeNet and CILI on first run

# Run the consolidated hub
python nlp-app.py

# OR run individual apps
python spacy-app.py
python languagetool-app.py
python pattern-app.py
python odenet-app.py
```

### Requirements

```txt
# requirements.txt
gradio>=4.0.0
spacy>=3.7.0
language-tool-python>=2.8.0
wn>=0.9.0
PatternLite>=3.6.0
```

### HuggingFace Space

The consolidated hub is deployed as a HuggingFace Space:

🔗 **[https://huggingface.co/spaces/cstr/nlp-de](https://huggingface.co/spaces/cstr/nlp-de)**

No local installation required - you can use the Gradio Client or REST API directly!

---

## 🧪 Testing with Dart

### Dart API Showcase Script (`test-nlp.dart`)

A comprehensive testing and demonstration script that showcases API capabilities with colored terminal output.

#### Features

- 🏥 **Health Check** - Tests endpoint availability before running
- 🎨 **Rich Visualization** - ANSI colors and box-drawing characters
- 📊 **Structured Data Display** - nested structures, formatted
- 💾 **JSON Export** - Optional saving of all results
- 🎯 **Selective Testing** - Run specific test suites

#### Installation

```bash
# Install Dart SDK
# macOS: brew install dart
# Linux: apt-get install dart
# Windows: choco install dart-sdk

# Add http package
dart pub add http

# OR create pubspec.yaml:
# name: nlp_test
# dependencies:
#   http: ^1.1.0
```

#### Usage

```bash
# Run all tests with health check
dart test-nlp.dart

# Run with JSON output saving
dart test-nlp.dart --save-json

# Skip health check
dart test-nlp.dart --skip-health

# Run specific test suites
dart test-nlp.dart spacy              # Only spaCy tests
dart test-nlp.dart grammar            # Only grammar tests
dart test-nlp.dart inflections        # Only inflection tests
dart test-nlp.dart thesaurus          # Only thesaurus tests
dart test-nlp.dart comprehensive      # Only comprehensive analysis

# Combine options
dart test-nlp.dart comprehensive --save-json
```

#### Output Example

```
╔═══════════════════════════════════════════════════════════════════╗
║ 🏛️  CONSOLIDATED LINGUISTICS HUB - COMPREHENSIVE SHOWCASE    ║
╚═══════════════════════════════════════════════════════════════════╝

🏥 HEALTH CHECK - Testing API Endpoints
──────────────────────────────────────────────────────────────────────
✓ get_morphology - Available
✓ check_grammar - Available
✓ get_all_inflections - Available
✓ get_thesaurus - Available
✓ comprehensive_analysis - Available
──────────────────────────────────────────────────────────────────────
Available: 5/5 endpoints

╔═══════════════════════════════════════════════════════════════════╗
║ SPACY ANALYZER (spacy_de_complex)
╚═══════════════════════════════════════════════════════════════════╝
Model: de
Text: "Der fleißige Student lernt jeden Tag Deutsch in der Bibliothek."

MORPHOLOGICAL & SYNTACTIC ANALYSIS
┌────────────┬────────────┬──────┬──────────┬──────────────────────┬────────────┐
│ Word       │ Lemma      │ POS  │ Tag      │ Morphology           │ Dependency │
├════════════╪════════════╪══════╪══════════╪══════════════════════╪════════════┤
│ Der        │ der        │ DET  │ ART      │ Case=Nom|Definite... │ nk         │
│ fleißige   │ fleißig    │ ADJ  │ ADJA     │ Case=Nom|Degree=P... │ nk         │
...
```

#### Test Coverage

**Test Suite 1: spaCy Analyzer**
- ✅ English complex sentence
- ✅ German complex sentence  
- ✅ Spanish sentence with NER
- ✅ Ancient Greek (Homer)

**Test Suite 2: Grammar Checker**
- ✅ Spelling error detection
- ✅ Agreement error detection
- ✅ Perfect sentence (no errors)

**Test Suite 3: Inflections**
- ✅ Noun declension (Haus)
- ✅ Verb conjugation (gehen)
- ✅ Adjective comparison (schön)

**Test Suite 4: Thesaurus**
- ✅ Common noun (Hund)
- ✅ Adjective (gut)
- ✅ Verb (laufen)

**Test Suite 5: Comprehensive Analysis**
- ✅ Simple sentence
- ✅ Complex sentence
- ✅ Sentence with grammar error

---

## 💡 Usage Examples

### Python Examples

#### Example 1: Multi-tool German Analysis

```python
from gradio_client import Client

client = Client("cstr/nlp-de")

# Comprehensive analysis
text = "Der schnelle Fuchs springt über den faulen Hund."
result = client.predict(text=text, api_name="/comprehensive_analysis")

# Access results
grammar_check = result['grammar_check']
spacy_analysis = result['spacy_analysis']
token_details = result['token_deep_dive']

# Print token info
for token in token_details:
    print(f"Word: {token['word']}")
    print(f"  POS: {token['spacy_pos']}")
    print(f"  Pattern: {token['pattern_analyses']}")
    print(f"  Synonyms: {token['thesaurus_senses']}")
```

#### Example 2: Batch Processing

```python
from gradio_client import Client
import json

client = Client("cstr/nlp-de")

sentences = [
    "Das ist ein Test.",
    "Die Katze schläft.",
    "Ich gehe nach Hause."
]

results = []
for sentence in sentences:
    result = client.predict(
        text=sentence,
        api_name="/check_grammar"
    )
    results.append({
        "text": sentence,
        "errors": result
    })

# Save results
with open("grammar_check_results.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
```

#### Example 3: Building a Vocabulary Trainer

```python
from gradio_client import Client

client = Client("cstr/nlp-de")

def get_word_info(word):
    """Get complete information about a German word"""
    
    # Get inflections
    inflections = client.predict(
        word=word,
        api_name="/get_all_inflections"
    )
    
    # Get semantic relations
    thesaurus = client.predict(
        word=word,
        api_name="/get_thesaurus"
    )
    
    return {
        "word": word,
        "inflections": inflections,
        "thesaurus": thesaurus
    }

# Example usage
word_info = get_word_info("lernen")
print(json.dumps(word_info, indent=2, ensure_ascii=False))
```

### Dart Examples

#### Example 1: Simple API Call

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

Future<void> checkGrammar(String text) async {
  final client = http.Client();
  final baseUrl = 'https://cstr-nlp-de.hf.space/gradio_api/call';
  
  // Step 1: POST to get event_id
  final postResponse = await client.post(
    Uri.parse('$baseUrl/check_grammar'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({"data": [text]}),
  );
  
  final eventId = jsonDecode(postResponse.body)['event_id'];
  
  // Step 2: GET stream results
  final getResponse = await client.get(
    Uri.parse('$baseUrl/check_grammar/$eventId'),
    headers: {'Accept': 'text/event-stream'},
  );
  
  print('Grammar check results: ${getResponse.body}');
  client.close();
}

void main() async {
  await checkGrammar("Das ist ein Huas.");
}
```

#### Example 2: Using the Showcase Script

```dart
// Use the provided test-nlp.dart script
import 'test-nlp.dart';

void main(List<String> args) async {
  // Run all tests
  await main(args);
  
  // Or run specific suite
  await main(['grammar', '--save-json']);
}
```

---

## 🛠️ Development

### Project Structure

```
nlp-hub/
├── nlp-app.py              # Main consolidated application
├── spacy-app.py            # Standalone spaCy analyzer
├── languagetool-app.py     # Standalone grammar checker
├── pattern-app.py          # Standalone inflection engine
├── odenet-app.py           # Standalone thesaurus
├── test-nlp.dart           # Comprehensive API test suite
├── requirements.txt        # Python dependencies
├── pubspec.yaml           # Dart dependencies
└── README.md              # This file
```

### Adding New Features

#### Adding a New spaCy Model

```python
# In nlp-app.py, update SPACY_MODEL_INFO:
SPACY_MODEL_INFO = {
    # ... existing models ...
    "fr": ("French", "fr_core_news_md", "spacy"),
}

# Update UI text dictionaries with translations
# Model will auto-download on first use
```

#### Adding a New Language to Grammar Check

```python
# In nlp-app.py, modify lt_get_language_tool():
def lt_get_language_tool(language='de-DE'):
    # Change default or add parameter
    tool = language_tool_python.LanguageTool(language)
    return tool
```

### Testing

```bash
# Test individual apps
python spacy-app.py &
python languagetool-app.py &
python pattern-app.py &
python odenet-app.py &

# Test consolidated hub
python nlp-app.py

# Run Dart test suite
dart test-nlp.dart --save-json

# Check specific functionality
dart test-nlp.dart grammar
```

## 📚 References

### Libraries & Tools

- **[spaCy](https://spacy.io/)** - Industrial-strength NLP
- **[LanguageTool](https://languagetool.org/)** - Grammar and spell checker
- **[Pattern](https://github.com/clips/pattern)** - Web mining and NLP (PatternLite fork)
- **[wn](https://github.com/goodmami/wn)** - WordNet interface
- **[OdeNet](https://github.com/hdaSprachtechnologie/odenet)** - German WordNet
- **[Gradio](https://gradio.app/)** - ML web interfaces and APIs
- **[greCy](https://github.com/CrispStrobe/greCy)** - Ancient Greek spaCy models

---

## 📄 License

This project is licensed under the AGPLv3 License.

### Third-Party Licenses

- spaCy: MIT License
- LanguageTool: LGPL 2.1
- Pattern: BSD 3 License  
- WordNet: Princeton WordNet License
- OdeNet: CC-BY-SA 4.0

---

## 🙏 Acknowledgments

- **Explosion AI** for spaCy and training infrastructure
- **LanguageTool** team for the open-source grammar checker
- **CLIPS** for the Pattern library
- **OdeNet** team for German semantic resources
- **HuggingFace** for free Space hosting
- **Gradio** team for the excellent framework

---

**Built with ❤️ by the NLP community**
