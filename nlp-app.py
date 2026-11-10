# ============================================================================
# 1. CONSOLIDATED IMPORTS
# ============================================================================
import gradio as gr
import spacy
from spacy import displacy
import base64
import traceback
import subprocess
import sys
import os
from pathlib import Path
import importlib
import site
import threading
import queue
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Set, Optional, Tuple

# --- LanguageTool Import ---
try:
    import language_tool_python
    LT_AVAILABLE = True
except ImportError:
    LT_AVAILABLE = False
    print("="*70)
    print("CRITICAL WARNING: `language-tool-python` library not found.")
    print("The 'German Grammar Check' tab will not function.")
    print("="*70)

# --- OdeNet (wn) Import ---
try:
    import wn
    WN_AVAILABLE = True
except ImportError:
    WN_AVAILABLE = False
    print("="*70)
    print("CRITICAL WARNING: `wn` library not found.")
    print("The 'German Thesaurus' tab will not function.")
    print("="*70)

# --- Pattern.de Import ---
try:
    from pattern.de import (
        pluralize, singularize, conjugate, tenses, lemma, lexeme,
        attributive, predicative,
        article, gender, MALE, FEMALE, NEUTRAL, PLURAL,
        INFINITIVE, PRESENT, PAST, PARTICIPLE,
        FIRST, SECOND, THIRD, SINGULAR, PLURAL as PL,
        INDICATIVE, IMPERATIVE, SUBJUNCTIVE,
        NOMINATIVE, ACCUSATIVE, DATIVE, GENITIVE,
        SUBJECT, OBJECT, INDIRECT, PROPERTY,
        DEFINITE, INDEFINITE,
        comparative, superlative,
        NOUN, VERB, ADJECTIVE,
        parse, split
    )
    PATTERN_DE_AVAILABLE = True
except ImportError as e:
    PATTERN_DE_AVAILABLE = False
    print("="*70)
    print(f"CRITICAL WARNING: `pattern.de` library not found: {e}")
    print("The 'German Inflections' tab will not function.")
    print("="*70)

# ============================================================================
# 2. SHARED GLOBALS & CONFIG
# ============================================================================
VERBOSE = True  # Enable verbose debug output for Pattern.de
def log(msg):
    """Print debug messages if verbose mode is on."""
    if VERBOSE:
        print(f"[DEBUG] {msg}")

# --- NEW HELPER ---
def _html_wrap(content: str, line_height: str = "2.0") -> str:
    """Wraps displaCy HTML in a consistent, scrollable div."""
    return f'<div style="overflow-x:auto; border: 1px solid #e6e9ef; border-radius: 0.25rem; padding: 1rem; line-height: {line_height};">{content}</div>'

# --- NEW HELPER for SVA ---
def _conjugate_to_person_number(verb_lemma: str, person: str, number: str) -> Optional[str]:
    """
    Return a present tense finite form for given person/number.
    person in {'1','2','3'}, number in {'sg','pl'}.
    """
    if not PATTERN_DE_AVAILABLE:
        return None
    try:
        alias = {"1sg":"1sg","2sg":"2sg","3sg":"3sg","1pl":"1pl","2pl":"2pl","3pl":"3pl"}[f"{person}{number}"]
        return conjugate(verb_lemma, alias)
    except Exception:
        return None

# ============================================================================
# 3. SPACY ANALYZER LOGIC (from spacy-app.py)
# ============================================================================

# --- Globals & Config for spaCy ---
SPACY_MODEL_INFO: Dict[str, Tuple[str, str, str]] = {
    "de": ("German", "de_core_news_md", "spacy"),
    "en": ("English", "en_core_web_md", "spacy"),
    "es": ("Spanish", "es_core_news_md", "spacy"),
    "grc-proiel-trf": ("Ancient Greek (PROIEL TRF)", "grc_proiel_trf", "grecy"),
    "grc-perseus-trf": ("Ancient Greek (Perseus TRF)", "grc_perseus_trf", "grecy"),
    "grc_ner_trf": ("Ancient Greek (NER TRF)", "grc_ner_trf", "grecy"),
    "grc-proiel-lg": ("Ancient Greek (PROIEL LG)", "grc_proiel_lg", "grecy"),
    "grc-perseus-lg": ("Ancient Greek (Perseus LG)", "grc_perseus_lg", "grecy"),
    "grc-proiel-sm": ("Ancient Greek (PROIEL SM)", "grc_proiel_sm", "grecy"),
    "grc-perseus-sm": ("Ancient Greek (Perseus SM)", "grc_perseus_sm", "grecy"),
}

SPACY_UI_TEXT = {
    "de": {
        "title": "# 🔍 Mehrsprachiger Morpho-Syntaktischer Analysator",
        "subtitle": "Analysieren Sie Texte auf Deutsch, Englisch, Spanisch und Altgriechisch",
        "ui_lang_label": "Benutzeroberflächensprache",
        "model_lang_label": "Textsprache für Analyse",
        "input_label": "Text eingeben",
        "input_placeholder": "Geben Sie hier Ihren Text ein...",
        "button_text": "Text analysieren",
        "button_processing_text": "Verarbeitung läuft...",
        "tab_graphic": "Grafische Darstellung",
        "tab_table": "Tabelle",
        "tab_json": "JSON",
        "tab_ner": "Entitäten",
        "html_label": "Abhängigkeitsparsing",
        "table_label": "Morphologische Analyse",
        "table_headers": ["Wort", "Lemma", "POS", "Tag", "Morphologie", "Abhängigkeit"],
        "json_label": "JSON-Ausgabe",
        "ner_label": "Benannte Entitäten",
        "error_message": "Fehler: "
    },
    "en": {
        "title": "# 🔍 Multilingual Morpho-Syntactic Analyzer",
        "subtitle": "Analyze texts in German, English, Spanish, and Ancient Greek",
        "ui_lang_label": "Interface Language",
        "model_lang_label": "Text Language for Analysis",
        "input_label": "Enter Text",
        "input_placeholder": "Enter your text here...",
        "button_text": "Analyze Text",
        "button_processing_text": "Processing...",
        "tab_graphic": "Graphic View",
        "tab_table": "Table",
        "tab_json": "JSON",
        "tab_ner": "Entities",
        "html_label": "Dependency Parsing",
        "table_label": "Morphological Analysis",
        "table_headers": ["Word", "Lemma", "POS", "Tag", "Morphology", "Dependency"],
        "json_label": "JSON Output",
        "ner_label": "Named Entities",
        "error_message": "Error: "
    },
    "es": {
        "title": "# 🔍 Analizador Morfo-Sintáctico Multilingüe",
        "subtitle": "Analice textos en alemán, inglés, español y griego antiguo",
        "ui_lang_label": "Idioma de la Interfaz",
        "model_lang_label": "Idioma del Texto para Análisis",
        "input_label": "Introducir Texto",
        "input_placeholder": "Ingrese su texto aquí...",
        "button_text": "Analizar Texto",
        "button_processing_text": "Procesando...",
        "tab_graphic": "Vista Gráfica",
        "tab_table": "Tabla",
        "tab_json": "JSON",
        "tab_ner": "Entidades",
        "html_label": "Análisis de Dependencias",
        "table_label": "Análisis Morfológico",
        "table_headers": ["Palabra", "Lema", "POS", "Etiqueta", "Morfología", "Dependencia"],
        "json_label": "Salida JSON",
        "ner_label": "Entidades Nombradas",
        "error_message": "Error: "
    }
}
SPACY_MODELS: Dict[str, Optional[spacy.Language]] = {}

# --- Dependency Installation ---
def spacy_install_spacy_transformers_once():
    """ Installs spacy-transformers, required for all _trf models. """
    marker_file = Path(".spacy_transformers_installed")
    if marker_file.exists():
        print("✓ spacy-transformers already installed (marker found)")
        return True
    
    print("Installing spacy-transformers (for _trf models)...")
    cmd = [sys.executable, "-m", "pip", "install", "spacy-transformers"]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=900) # Increased timeout
        print("✓ Successfully installed spacy-transformers")
        marker_file.touch()
        return True
    except Exception as e:
        print(f"✗ FAILED to install spacy-transformers: {e}")
        if hasattr(e, 'stdout'): print(f"STDOUT: {e.stdout}")
        if hasattr(e, 'stderr'): print(f"STDERR: {e.stderr}")
        return False

def spacy_install_grecy_model_from_github(model_name: str) -> bool:
    """ Installs a greCy model from GitHub Release. """
    marker_file = Path(f".{model_name}_installed")
    if marker_file.exists():
        print(f"✓ {model_name} already installed (marker found)")
        return True

    print(f"Installing grecy model: {model_name}...")

    if model_name == "grc_proiel_trf":
        wheel_filename = "grc_proiel_trf-3.7.5-py3-none-any.whl"
    elif model_name in ["grc_perseus_trf", "grc_proiel_lg", "grc_perseus_lg", 
                        "grc_proiel_sm", "grc_perseus_sm", "grc_ner_trf"]:
        wheel_filename = f"{model_name}-0.0.0-py3-none-any.whl"
    else:
        print(f"✗ Unknown grecy model: {model_name}")
        return False

    install_url = f"https://github.com/CrispStrobe/greCy/releases/download/v1.0-models/{wheel_filename}"
    cmd = [sys.executable, "-m", "pip", "install", install_url, "--no-deps"]

    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=900)
        if result.stdout: print("STDOUT:", result.stdout)
        if result.stderr: print("STDERR:", result.stderr)
        print(f"✓ Successfully installed {model_name} from GitHub")
        marker_file.touch()
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Installation subprocess FAILED with code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False
    except Exception as e:
        print(f"✗ Installation exception: {e}")
        traceback.print_exc()
        return False

# --- Model Loading (Lazy Loading) ---
def spacy_load_spacy_model(model_name: str) -> Optional[spacy.Language]:
    """Load or install a standard spaCy model."""
    try:
        return spacy.load(model_name)
    except OSError:
        print(f"Installing {model_name}...")
        try:
            subprocess.check_call([sys.executable, "-m", "spacy", "download", model_name])
            return spacy.load(model_name)
        except Exception as e:
            print(f"✗ Failed to install {model_name}: {e}")
            if hasattr(e, 'stderr'): print(f"STDERR: {e.stderr}")
            return None

def spacy_load_grecy_model(model_name: str) -> Optional[spacy.Language]:
    """ Load a grecy model, installing from GitHub if needed. """
    if not spacy_install_grecy_model_from_github(model_name):
        print(f"✗ Cannot load {model_name} because installation failed.")
        return None
    try:
        print("Refreshing importlib to find new package...")
        importlib.invalidate_caches()
        try: importlib.reload(site)
        except Exception: pass

        print(f"Trying: spacy.load('{model_name}')")
        nlp = spacy.load(model_name)
        print(f"✓ Successfully loaded {model_name}")
        return nlp
    except Exception as e:
        print(f"✗ Model {model_name} is installed but FAILED to load.")
        print(f"   Error: {e}")
        traceback.print_exc()
        return None

def spacy_initialize_models():
    """ Pre-load standard models and ensure _trf dependencies are ready. """
    print("\n" + "="*70)
    print("INITIALIZING SPACY MODELS")
    print("="*70 + "\n")
    
    spacy_install_spacy_transformers_once()
    
    loaded_count = 0
    spacy_model_count = 0
    
    for lang_code, (lang_name, model_name, model_type) in SPACY_MODEL_INFO.items():
        if model_type == "spacy":
            spacy_model_count += 1
            print(f"Loading {lang_name} ({model_name})...")
            nlp = spacy_load_spacy_model(model_name)
            SPACY_MODELS[lang_code] = nlp
            if nlp:
                print(f"✓ {lang_name} ready\n")
                loaded_count += 1
            else:
                print(f"✗ {lang_name} FAILED\n")
        else:
            print(f"✓ {lang_name} ({model_name}) will be loaded on first use.\n")
            SPACY_MODELS[lang_code] = None
    
    print(f"Pre-loaded {loaded_count}/{spacy_model_count} standard models.")
    print("="*70 + "\n")

# --- Analysis Logic ---
def spacy_get_analysis(ui_lang: str, model_lang_key: str, text: str):
    """Analyze text and return results."""
    ui_config = SPACY_UI_TEXT.get(ui_lang.lower(), SPACY_UI_TEXT["en"])
    error_prefix = ui_config["error_message"]
    
    try:
        if not text.strip():
            # Return empty values for all outputs
            return ([], [], "<p style='color: orange;'>No text provided.</p>", "<p>No text provided.</p>",
                    gr.Button(value=ui_config["button_text"], interactive=True))
        
        nlp = SPACY_MODELS.get(model_lang_key)
        
        if nlp is None:
            print(f"First use of {model_lang_key}. Loading model...")
            if model_lang_key not in SPACY_MODEL_INFO:
                 # Check key before access
                 raise ValueError(f"Unknown model key: {model_lang_key}")
            _, model_name, model_type = SPACY_MODEL_INFO[model_lang_key]
            
            if model_type == "grecy":
                nlp = spacy_load_grecy_model(model_name)
            else:
                nlp = spacy_load_spacy_model(model_name)
            
            if nlp is None:
                SPACY_MODELS.pop(model_lang_key, None)
                err_msg = f"Model for {model_lang_key} ({model_name}) FAILED to load. Check logs."
                err_html = f"<p style='color: red;'>{err_msg}</p>"
                # Return error tuple on load failure
                return ([], {"error": err_msg}, err_html, err_html,
                        gr.Button(value=ui_config["button_text"], interactive=True))
            else:
                SPACY_MODELS[model_lang_key] = nlp
                print(f"✓ {model_lang_key} is now loaded and cached.")
        
        doc = nlp(text)
        
        dataframe_output = []
        json_output = []
        
        for token in doc:
            # --- Robust attribute access ---
            lemma_str = token.lemma_
            morph_str = str(token.morph) if token.morph else ''
            dep_str = token.dep_ if doc.is_parsed else ''
            tag_str = token.tag_ or ''
            pos_str = token.pos_ or ''
            # --- End robust access ---
            
            json_output.append({
                "word": token.text, "lemma": lemma_str, "pos": pos_str,
                "tag": tag_str, "morphology": morph_str, "dependency": dep_str,
                "is_stopword": token.is_stop
            })
            dataframe_output.append([token.text, lemma_str, pos_str, tag_str, morph_str, dep_str])
        
        # --- DEPENDENCY PARSE VISUALIZATION ---
        html_dep_out = ""
        if "parser" in nlp.pipe_names and doc.is_parsed:
            try:
                options = {"compact": True, "bg": "#ffffff", "color": "#000000", "font": "Source Sans Pro"}
                # --- Use direct HTML, no base64 ---
                html_svg = displacy.render(doc, style="dep", jupyter=False, options=options)
                html_dep_out = _html_wrap(html_svg, line_height="2.5")
                # --- End direct HTML ---
            except Exception as e:
                html_dep_out = f"<p style='color: orange;'>Visualization error (DEP): {e}</p>"
        else:
            html_dep_out = "<p style='color: orange;'>Dependency parsing ('parser') not available or doc not parsed.</p>"
        
        # --- NAMED ENTITY VISUALIZATION ---
        html_ner_out = ""
        if "ner" in nlp.pipe_names:
            if doc.ents:
                try:
                    html_ner = displacy.render(doc, style="ent", jupyter=False)
                    html_ner_out = _html_wrap(html_ner, line_height="2.5")
                except Exception as e:
                    html_ner_out = f"<p style='color: orange;'>Visualization error (NER): {e}</p>"
            else:
                html_ner_out = "<p>No named entities found in this text.</p>"
        else:
            html_ner_out = "<p style='color: orange;'>Named Entity Recognition ('ner') not available for this model.</p>"
        
        return (dataframe_output, json_output, html_dep_out, html_ner_out,
                gr.Button(value=ui_config["button_text"], interactive=True))
        
    except Exception as e:
        traceback.print_exc()
        error_html = f"<div style='color: red; border: 1px solid red; padding: 10px; border-radius: 5px; background-color: #fff5f5;'><strong>{error_prefix}</strong> {str(e)}</div>"
        # --- Consistent error return shape ---
        return ([], {"error": str(e)}, error_html, error_html,
                gr.Button(value=ui_config["button_text"], interactive=True))

# --- UI Update Logic ---
def spacy_update_ui(ui_lang: str):
    """Update UI language for the spaCy tab."""
    ui_config = SPACY_UI_TEXT.get(ui_lang.lower(), SPACY_UI_TEXT["en"])
    # --- Return component UPDATES, not new components ---
    return [
        gr.Markdown.update(value=ui_config["title"]),
        gr.Markdown.update(value=ui_config["subtitle"]),
        gr.update(label=ui_config["ui_lang_label"]),
        gr.update(label=ui_config["model_lang_label"]),
        gr.Textbox.update(label=ui_config["input_label"], placeholder=ui_config["input_placeholder"]),
        gr.Button.update(value=ui_config["button_text"]),
        gr.update(label=ui_config["tab_graphic"]),
        gr.update(label=ui_config["tab_table"]),
        gr.update(label=ui_config["tab_json"]),
        gr.update(label=ui_config["tab_ner"]),
        gr.HTML.update(label=ui_config["html_label"]),
        gr.DataFrame.update(label=ui_config["table_label"], headers=ui_config["table_headers"]),
        gr.JSON.update(label=ui_config["json_label"]),
        gr.HTML.update(label=ui_config["ner_label"])
    ]
    # --- End component updates ---

# ============================================================================
# 4. LANGUAGETOOL LOGIC (from languagetool-server.py)
# ============================================================================

# --- Globals for LanguageTool ---
LT_TOOL_INSTANCE: language_tool_python.LanguageTool = None
LT_TOOL_LOCK = threading.Lock()

def lt_get_language_tool() -> language_tool_python.LanguageTool:
    """
    Thread-safe function to get a single instance of the LanguageTool.
    """
    global LT_TOOL_INSTANCE
    
    if not LT_AVAILABLE:
        raise ImportError("language-tool-python library is not installed.")

    # Fast path: If the tool is already initialized, return it.
    if LT_TOOL_INSTANCE:
        return LT_TOOL_INSTANCE
    
    # Slow path: Tool is not initialized. Acquire the lock.
    with LT_TOOL_LOCK:
        # Check again *inside* the lock
        if LT_TOOL_INSTANCE:
            return LT_TOOL_INSTANCE
        
        try:
            print("Initializing LanguageTool for German (de-DE)...")
            tool = language_tool_python.LanguageTool('de-DE')
            try:
                tool.picky = True
            except Exception:
                pass
            # Warm-up to ensure rules are loaded
            _ = tool.check("Dies ist ein Test.")
            print("LanguageTool (local server) initialized successfully.")
            LT_TOOL_INSTANCE = tool
            return LT_TOOL_INSTANCE
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to initialize LanguageTool: {e}")
            return None

# --- Grammar Checking Logic ---
def lt_check_grammar(text: str) -> List[Dict[str, Any]]:
    """
    Checks a German text for grammar and spelling errors and returns a JSON list.
    """
    try:
        # Get the singleton instance of the tool.
        tool = lt_get_language_tool()
        
        if tool is None:
            return [{"error": "LanguageTool service failed to initialize."}]
            
        if not text or not text.strip():
            return [{"info": "No text provided to check."}]

        print(f"Checking text: {text}")
        matches = tool.check(text)
        
        if not matches:
            try:
                tool.picky = True
                matches = tool.check(text)
            except Exception:
                pass

        if not matches:
            return [{"info": "No errors found!", "status": "perfect"}]

        errors_list = []
        for match in matches:
            # --- Robust attribute access for match ---
            error = {
                "message": match.message,
                "rule_id": match.ruleId,
                "category": getattr(match.category, 'name', match.category),
                "incorrect_text": text[match.offset : match.offset + match.errorLength],
                "replacements": match.replacements,
                "offset": match.offset,
                "length": match.errorLength,
                "context": getattr(match, "context", None),
                "short_message": getattr(match, "shortMessage", None)
            }
            # --- End robust access ---
            errors_list.append(error)
            
        print(f"Found {len(errors_list)} errors.")
        return errors_list

    except Exception as e:
        traceback.print_exc()
        return [{"error": f"An unexpected error occurred: {str(e)}"}]

# ============================================================================
# 5. ODENET THESAURUS LOGIC (from odenet_app.py)
# ============================================================================

# --- Globals & Classes for OdeNet ---
@dataclass
class OdeNetWorkItem:
    """Represents a lookup request."""
    word: str
    response_queue: queue.Queue

class OdeNetWorkerState(Enum):
    NOT_STARTED = 1
    INITIALIZING = 2
    READY = 3
    ERROR = 4

odenet_worker_state = OdeNetWorkerState.NOT_STARTED
odenet_worker_thread = None
odenet_work_queue = queue.Queue()
odenet_de_wn = None  # Single WordNet instance for the worker thread

# --- Worker Thread Logic ---
def odenet_download_wordnet_data():
    """Download WordNet data. Called once by worker thread."""
    if not WN_AVAILABLE:
        print("[OdeNet Worker] 'wn' library not available. Skipping download.")
        return False
    try:
        print("[OdeNet Worker] Downloading WordNet data...")
        try:
            wn.download('odenet:1.4')
        except Exception as e:
            print(f"[OdeNet Worker] Note: odenet download: {e}")
        
        try:
            wn.download('cili:1.0')
        except Exception as e:
            print(f"[OdeNet Worker] Note: cili download: {e}")
        
        print("[OdeNet Worker] ✓ WordNet data ready")
        return True
    except Exception as e:
        print(f"[OdeNet Worker] ✗ Failed to download WordNet data: {e}")
        return False

def odenet_worker_loop():
    """
    Worker thread main loop.
    This is the ONLY thread that accesses the SQLite database.
    """
    global odenet_worker_state, odenet_de_wn
    
    if not WN_AVAILABLE:
        print("[OdeNet Worker] 'wn' library not available. Worker cannot start.")
        odenet_worker_state = OdeNetWorkerState.ERROR
        return
        
    try:
        print("[OdeNet Worker] Starting worker thread...")
        odenet_worker_state = OdeNetWorkerState.INITIALIZING
        
        if not odenet_download_wordnet_data():
            odenet_worker_state = OdeNetWorkerState.ERROR
            print("[OdeNet Worker] Failed to initialize")
            return
        
        print("[OdeNet Worker] Creating WordNet instance...")
        odenet_de_wn = wn.Wordnet('odenet:1.4')
        odenet_worker_state = OdeNetWorkerState.READY
        print("[OdeNet Worker] Ready to process requests")
        
        while True:
            try:
                item: OdeNetWorkItem = odenet_work_queue.get(timeout=1)
                
                try:
                    result = odenet_process_word_lookup(item.word)
                    item.response_queue.put(("success", result))
                except Exception as e:
                    traceback.print_exc()
                    item.response_queue.put(("error", str(e)))
                finally:
                    odenet_work_queue.task_done()
                    
            except queue.Empty:
                continue
                
    except Exception as e:
        print(f"[OdeNet Worker] Fatal error: {e}")
        traceback.print_exc()
        odenet_worker_state = OdeNetWorkerState.ERROR

def odenet_process_word_lookup(word: str) -> Dict[str, Any]:
    """
    Process a single word lookup. Runs in the worker thread.
    """
    global odenet_de_wn
    
    if not word or not word.strip():
        return {"info": "No word provided to check."}
    
    word = word.strip().lower()
    
    senses = odenet_de_wn.senses(word)
    
    if not senses:
        return {"info": f"The word '{word}' was not found in the thesaurus."}
    
    results: Dict[str, Any] = {
        "input_word": word,
        "senses": []
    }
    
    for sense in senses:
        synset = sense.synset()
        
        def get_lemmas(synsets, remove_self=False):
            lemmas: Set[str] = set()
            for s in synsets:
                for lemma in s.lemmas():
                    if not (remove_self and lemma.lower() == word):  # OdeNet capitalises nouns
                        lemmas.add(lemma)
            return sorted(list(lemmas))
        
        antonym_words: Set[str] = set()
        try:
            for ant_sense in sense.get_related('antonym'):
                antonym_words.add(ant_sense.word().lemma())
        except Exception:
            pass
        
        sense_info = {
            "pos": synset.pos,
            "definition": synset.definition() or "No definition available.",
            "synonyms": get_lemmas([synset], remove_self=True),
            "antonyms": sorted(list(antonym_words)),
            "hypernyms (is a type of)": get_lemmas(synset.hypernyms()),
            "hyponyms (examples are)": get_lemmas(synset.hyponyms()),
            "holonyms (is part of)": get_lemmas(synset.holonyms()),
            "meronyms (has parts)": get_lemmas(synset.meronyms()),
        }
        
        results["senses"].append(sense_info)
    
    print(f"[OdeNet Worker] Found {len(results['senses'])} senses for '{word}'")
    return results

def odenet_start_worker():
    """Start the worker thread if not already started."""
    global odenet_worker_thread, odenet_worker_state
    
    if odenet_worker_state != OdeNetWorkerState.NOT_STARTED:
        return
    
    if not WN_AVAILABLE:
        print("[OdeNet] 'wn' library not available. Worker will not be started.")
        odenet_worker_state = OdeNetWorkerState.ERROR
        return
    
    odenet_worker_thread = threading.Thread(target=odenet_worker_loop, daemon=True, name="OdeNetWorker")
    odenet_worker_thread.start()
    
    timeout = 30  # 30 seconds
    for _ in range(timeout * 10):
        if odenet_worker_state in (OdeNetWorkerState.READY, OdeNetWorkerState.ERROR):
            break
        threading.Event().wait(0.1)
    
    if odenet_worker_state != OdeNetWorkerState.READY:
        raise Exception("OdeNet Worker failed to initialize")

# --- Public API (Called by Gradio) ---
def odenet_get_thesaurus_info(word: str) -> Dict[str, Any]:
    """
    Public API: Finds thesaurus info for a German word. Thread-safe.
    """
    if not WN_AVAILABLE:
        return {"error": "WordNet (wn) library is not available."}
    
    if odenet_worker_state != OdeNetWorkerState.READY:
        return {"error": "WordNet service is not ready yet. Please try again in a moment."}
    
    try:
        response_queue = queue.Queue()
        item = OdeNetWorkItem(word=word, response_queue=response_queue)
        odenet_work_queue.put(item)
        
        try:
            status, result = response_queue.get(timeout=30)
            if status == "success":
                return result
            else:
                return {"error": f"Lookup failed: {result}"}
                
        except queue.Empty:
            return {"error": "Request timed out"}
            
    except Exception as e:
        traceback.print_exc()
        return {"error": f"An unexpected error occurred: {str(e)}"}

# ============================================================================
# 6. PATTERN INFLECTION LOGIC (from pattern-app.py)
# ============================================================================

# --- Word Type Detection ---
def pattern_detect_word_type(word: str) -> Dict[str, Any]:
    """
    Use pattern.de's parser as a hint.
    """
    if not PATTERN_DE_AVAILABLE:
        return {'pos': None, 'lemma': word, 'type': 'unknown'}
    
    # --- FIX: Replaced special ellipsis '…' with '...' ---
    if not word or not word.strip() or all(ch in ".,;:!?()[]{}-–—'.../\|" for ch in word):
        return {'pos': None, 'lemma': word, 'type': 'unknown'}
    word_norm = word.strip()
        
    log(f"Detecting type for: {word_norm}")
    parser_result = {'pos': None, 'lemma': word_norm, 'type': None}
    
    try:
        parsed = parse(word_norm, lemmata=True)
        for sentence in split(parsed):
            # --- Robust attribute access ---
            if hasattr(sentence, "words") and sentence.words:
                w = sentence.words[0]
                w_type = getattr(w, "type", None) or getattr(w, "pos", None)
                w_lemma = (getattr(w, "lemma", None) or word_norm)
                
                # Ignore common German function POS from pattern.de
                non_content_prefixes = ("DT","ART","IN","APPR","APPRART","APPO","APZR","PTK","PRP","PPER","PPOS","PDS","PIS","KOUI","KON","$,","$.")
                if w_type and any(w_type.startswith(p) for p in non_content_prefixes):
                    return {'pos': w_type, 'lemma': w_lemma, 'type': None}

                parser_result['pos'] = w_type or ""
                parser_result['lemma'] = w_lemma
                
                if w_type and w_type.startswith('NN'):
                    parser_result['type'] = 'noun'
                elif w_type and w_type.startswith('VB'):
                    parser_result['type'] = 'verb'
                elif w_type and w_type.startswith('JJ'):
                    parser_result['type'] = 'adjective'
                
                log(f"  Parser says: POS={w_type}, lemma={w_lemma}, type={parser_result['type']}")
            # --- End robust access ---
    except Exception as e:
        log(f"  Parser failed: {e}")
    
    return parser_result

def pattern_is_good_analysis(analysis, analysis_type):
    """Check if an analysis has meaningful data."""
    if not analysis:
        return False
    
    if analysis_type == 'noun':
        return len(analysis.get('declension', {})) >= 4
    elif analysis_type == 'verb':
        present = analysis.get('conjugation', {}).get('Präsens', {})
        if len(present) < 4:
            return False
        unique_forms = set(present.values())
        if len(unique_forms) < 2:
            return False
        return True
    elif analysis_type == 'adjective':
        return len(analysis.get('attributive', {})) > 0
    return False

# --- Inflection Generators ---
def pattern_analyze_as_noun(word: str, hint_lemma: str = None) -> Dict[str, Any]:
    """Comprehensive noun inflection analysis."""
    log(f"  Analyzing as noun (hint_lemma={hint_lemma})")
    analysis = {}
    
    singular = singularize(word)
    plural = pluralize(word)
    log(f"    singularize({word}) = {singular}")
    log(f"    pluralize({word}) = {plural}")
    
    if plural != word and singular != word:
        base = word
        log(f"    Word changes when pluralized => base = {base}")
    elif singular != word:
        base = singular
        log(f"    Word changes when singularized => base = {base}")
    elif hint_lemma and hint_lemma != word:
        base = hint_lemma
        log(f"    Using hint lemma => base = {base}")
    else:
        log(f"    Cannot determine base form")
        return None
    
    g = gender(base, pos=NOUN)
    log(f"    gender({base}) = {g}")
    
    if g is None:
        g = MALE
        log(f"    Gender unknown, defaulting to MALE")
    
    gender_str = {MALE: "Masculine", FEMALE: "Feminine", NEUTRAL: "Neuter"}.get(g, "Unknown")
    
    analysis["base_form"] = base
    analysis["gender"] = gender_str
    analysis["plural"] = pluralize(base)
    analysis["singular"] = base
    analysis["declension"] = {}
    
    for number, number_name in [(SINGULAR, "Singular"), (PLURAL, "Plural")]:
        word_form = base if number == SINGULAR else pluralize(base)
        # --- FIX: Capitalize noun form for presentation ---
        word_form_cap = word_form.capitalize()
        gender_for_article = g if number == SINGULAR else PLURAL
        
        for case, case_name in [(NOMINATIVE, "Nominativ"), (ACCUSATIVE, "Akkusativ"), 
                                 (DATIVE, "Dativ"), (GENITIVE, "Genitiv")]:
            try:
                def_art = article(word_form, DEFINITE, gender_for_article, case)
                indef_art = article(word_form, INDEFINITE, gender_for_article, case)
                
                indef_form = f"{indef_art} {word_form_cap}" if indef_art else word_form_cap
                
                # --- FIX: German has no plural indefinite article, set to '—' ---
                if number == PLURAL:
                    indef_form = "—"

                analysis["declension"][f"{case_name} {number_name}"] = {
                    "definite": f"{def_art} {word_form_cap}" if def_art else word_form_cap,
                    "indefinite": indef_form,
                    "bare": word_form_cap
                }
            except Exception as e:
                log(f"    Failed to get article for {case_name} {number_name}: {e}")
    
    log(f"    Generated {len(analysis.get('declension', {}))} declension forms")
    return analysis

def pattern_analyze_as_verb(word: str, hint_lemma: str = None) -> Dict[str, Any]:
    """Comprehensive verb conjugation analysis."""
    log(f"  Analyzing as verb (hint_lemma={hint_lemma})")
    
    verb_lemma = lemma(word)
    log(f"    lemma({word}) = {verb_lemma}")
    
    if not verb_lemma or verb_lemma == word:
        if hint_lemma and hint_lemma != word:
            verb_lemma = hint_lemma
            log(f"    Using hint lemma: {verb_lemma}")
        elif not verb_lemma:
            log(f"    No lemma found")
            return None
    
    analysis = {"infinitive": verb_lemma}
    
    try:
        lex = lexeme(verb_lemma)
        if lex and len(lex) > 1:
            analysis["lexeme"] = lex
            log(f"    lexeme has {len(lex)} forms")
    except Exception as e:
        log(f"    Failed to get lexeme: {e}")
    
    analysis["conjugation"] = {}
    analysis["conjugation"]["Präsens"] = {}
    
    present_count = 0
    for alias, name in [("1sg", "ich"), ("2sg", "du"), ("3sg", "er/sie/es"),
                        ("1pl", "wir"), ("2pl", "ihr"), ("3pl", "sie/Sie")]:
        try:
            form = conjugate(verb_lemma, alias)
            if form:
                analysis["conjugation"]["Präsens"][name] = form
                present_count += 1
        except Exception as e:
            log(f"    Failed conjugate({verb_lemma}, {alias}): {e}")
    
    log(f"    Generated {present_count} present tense forms")
    if present_count < 4:
        log(f"    Too few present forms, not a valid verb")
        return None
    
    analysis["conjugation"]["Präteritum"] = {}
    for alias, name in [("1sgp", "ich"), ("2sgp", "du"), ("3sgp", "er/sie/es"),
                        ("1ppl", "wir"), ("2ppl", "ihr"), ("3ppl", "sie/Sie")]:
        try:
            form = conjugate(verb_lemma, alias)
            if form: analysis["conjugation"]["Präteritum"][name] = form
        except: pass
    
    analysis["participles"] = {}
    try:
        form = conjugate(verb_lemma, "part")
        if form: analysis["participles"]["Partizip Präsens"] = form
    except: pass
    try:
        form = conjugate(verb_lemma, "ppart")
        if form: analysis["participles"]["Partizip Perfekt"] = form
    except: pass
    
    analysis["conjugation"]["Imperativ"] = {}
    for alias, name in [("2sg!", "du"), ("2pl!", "ihr")]:
        try:
            form = conjugate(verb_lemma, alias)
            if form: analysis["conjugation"]["Imperativ"][name] = form
        except: pass

    analysis["conjugation"]["Konjunktiv I"] = {}
    for alias, name in [("1sg?", "ich"), ("2sg?", "du"), ("3sg?", "er/sie/es"),
                        ("1pl?", "wir"), ("2pl?", "ihr"), ("3pl?", "sie/Sie")]:
        try:
            form = conjugate(verb_lemma, alias)
            if form: analysis["conjugation"]["Konjunktiv I"][name] = form
        except: pass
            
    analysis["conjugation"]["Konjunktiv II"] = {}
    for alias, name in [("1sgp?", "ich"), ("2sgp?", "du"), ("3sgp?", "er/sie/es"),
                        ("1ppl?", "wir"), ("2ppl?", "ihr"), ("3ppl?", "sie/Sie")]:
        try:
            form = conjugate(verb_lemma, alias)
            if form: analysis["conjugation"]["Konjunktiv II"][name] = form
        except: pass
    
    return analysis

def pattern_analyze_as_adjective(word: str, hint_lemma: str = None) -> Dict[str, Any]:
    """Comprehensive adjective inflection analysis."""
    log(f"  Analyzing as adjective (hint_lemma={hint_lemma})")
    
    base = predicative(word)
    log(f"    predicative({word}) = {base}")
    
    if base == word.lower() and hint_lemma and hint_lemma != word:
        base = hint_lemma
        log(f"    Using hint lemma: {base}")
    
    analysis = {}
    analysis["predicative"] = base
    analysis["comparative"] = comparative(base)
    analysis["superlative"] = superlative(base)
    log(f"    comparative = {analysis['comparative']}")
    log(f"    superlative = {analysis['superlative']}")
    
    analysis["attributive"] = {}
    attr_count = 0
    for article_type, article_name in [(None, "Strong"), (INDEFINITE, "Mixed"), (DEFINITE, "Weak")]:
        analysis["attributive"][article_name] = {}
        for gender, gender_name in [(MALE, "Masculine"), (FEMALE, "Feminine"), 
                                     (NEUTRAL, "Neuter"), (PLURAL, "Plural")]:
            analysis["attributive"][article_name][gender_name] = {}
            for case, case_name in [(NOMINATIVE, "Nom"), (ACCUSATIVE, "Acc"),
                                     (DATIVE, "Dat"), (GENITIVE, "Gen")]:
                try:
                    attr_form = attributive(base, gender, case, article_type)
                    if article_type:
                        art = article("_", article_type, gender, case)
                        full_form = f"{art} {attr_form} [Noun]" if art else f"{attr_form} [Noun]"
                    else:
                        full_form = f"{attr_form} [Noun]"
                    analysis["attributive"][article_name][gender_name][case_name] = {
                        "form": attr_form, "example": full_form
                    }
                    attr_count += 1
                except Exception as e:
                    log(f"    Failed attributive for {article_name}/{gender_name}/{case_name}: {e}")
    
    log(f"    Generated {attr_count} attributive forms")
    if attr_count == 0:
        return None
    return analysis

# --- Public API (Called by Gradio) ---
def pattern_get_all_inflections(word: str) -> Dict[str, Any]:
    """
    Generates ALL possible inflections for a German word.
    """
    if not PATTERN_DE_AVAILABLE:
        return {"error": "`PatternLite` library not available."}

    if not word or not word.strip():
        return {"info": "Please enter a word."}

    word = word.strip()
    log("="*70); log(f"ANALYZING: {word}"); log("="*70)
    
    detection = pattern_detect_word_type(word)
    results: Dict[str, Any] = {
        "input_word": word,
        "parser_hint": {
            "pos": detection['pos'],
            "lemma": detection['lemma'],
            "type": detection['type']
        },
        "analyses": {}
    }

    try:
        detected_type = detection['type']
        
        if detected_type == 'noun':
            log("\n--- NOUN DETECTED - Analyzing as noun ---")
            noun_analysis = pattern_analyze_as_noun(word, detection['lemma'])
            if noun_analysis and pattern_is_good_analysis(noun_analysis, 'noun'):
                log("✓ Noun analysis successful")
                results["analyses"]["noun"] = noun_analysis
            else: log("✗ Noun analysis failed")
        
        elif detected_type == 'verb':
            log("\n--- VERB DETECTED - Analyzing as verb ---")
            verb_analysis = pattern_analyze_as_verb(word, detection['lemma'])
            if verb_analysis and pattern_is_good_analysis(verb_analysis, 'verb'):
                log("✓ Verb analysis successful")
                results["analyses"]["verb"] = verb_analysis
            else: log("✗ Verb analysis failed")
        
        elif detected_type == 'adjective':
            log("\n--- ADJECTIVE DETECTED - Analyzing as adjective ---")
            adj_analysis = pattern_analyze_as_adjective(word, detection['lemma'])
            if adj_analysis and pattern_is_good_analysis(adj_analysis, 'adjective'):
                log("✓ Adjective analysis successful")
                results["analyses"]["adjective"] = adj_analysis
            else: log("✗ Adjective analysis failed")
        
        else:
            log("\n--- TYPE UNKNOWN - Trying all analyses ---")
            noun_analysis = pattern_analyze_as_noun(word, detection['lemma'])
            if noun_analysis and pattern_is_good_analysis(noun_analysis, 'noun'):
                log("✓ Noun analysis is good")
                results["analyses"]["noun"] = noun_analysis
            
            verb_analysis = pattern_analyze_as_verb(word, detection['lemma'])
            if verb_analysis and pattern_is_good_analysis(verb_analysis, 'verb'):
                log("✓ Verb analysis is good")
                results["analyses"]["verb"] = verb_analysis
            
            adj_analysis = pattern_analyze_as_adjective(word, detection['lemma'])
            if adj_analysis and pattern_is_good_analysis(adj_analysis, 'adjective'):
                log("✓ Adjective analysis is good")
                results["analyses"]["adjective"] = adj_analysis

        if not results["analyses"]:
            results["info"] = "Word could not be analyzed."

        log(f"\nFinal result: {len(results['analyses'])} analysis/analyses")
        return results

    except Exception as e:
        log(f"\nERROR: {e}")
        traceback.print_exc()
        return {"error": f"An unexpected error occurred: {str(e)}"}

# ============================================================================
# 7. COMBINED ANALYZER LOGIC
# ============================================================================

def comprehensive_german_analysis(text: str) -> Dict[str, Any]:
    """
    Combines NLP tools for a deep analysis of German text.
    """
    if not text or not text.strip():
        return {"info": "Please enter text to analyze."}

    print(f"\n[Comprehensive Analysis] Starting analysis for: \"{text}\"")
    results: Dict[str, Any] = {"input_text": text}

    # --- 1. LanguageTool Grammar Check ---
    print("[Comprehensive Analysis] Running LanguageTool...")
    if LT_AVAILABLE:
        try:
            results["grammar_check"] = lt_check_grammar(text)
        except Exception as e:
            results["grammar_check"] = {"error": f"LanguageTool failed: {e}"}
    else:
        results["grammar_check"] = {"error": "LanguageTool not available."}

    # --- 2. spaCy Morpho-Syntactic Backbone ---
    print("[Comprehensive Analysis] Running spaCy...")
    spacy_json_output = []
    # --- Always call spacy_get_analysis to handle lazy-loading ---
    try:
        _, spacy_json, _, _, _ = spacy_get_analysis("en", "de", text)
        if isinstance(spacy_json, list):
            spacy_json_output = spacy_json
            results["spacy_analysis"] = spacy_json_output
        else:
            results["spacy_analysis"] = spacy_json # Could be an error dict
    except Exception as e:
         results["spacy_analysis"] = {"error": f"spaCy analysis failed: {e}"}
    # --- End lazy-load call ---

    # --- 2b. Heuristic SVA check if LT missed it ---
    try:
        if isinstance(results.get("grammar_check"), list) and any(d.get("status") == "perfect" for d in results["grammar_check"]):
            # Find subject and finite verb
            subj_num = None
            verb_num = None
            verb_token = None
            subj_token = None
            for tok in spacy_json_output:
                if tok.get("dependency") in {"sb", "nsubj"}:
                    m = tok.get("morphology","")
                    if "Number=Sing" in m:
                        subj_num = "Sing"
                        subj_token = tok
                
                spacy_pos_up = (tok.get("pos") or "").upper()
                if (spacy_pos_up in {"VERB", "AUX"}) and ("VerbForm=Fin" in tok.get("morphology","")):
                    verb_token = tok
                    m = tok.get("morphology","")
                    if "Number=Plur" in m:
                        verb_num = "Plur"
            
            if subj_num == "Sing" and verb_num == "Plur":
                # --- Build suggestions ---
                corrected_sentence_sg = None
                corrected_sentence_pl = None
                replacements = []
                
                v_lemma = verb_token.get("lemma")
                v_word = verb_token.get("word")
                v_3sg = _conjugate_to_person_number(v_lemma, "3", "sg") if v_lemma else None
                if v_3sg and v_word:
                    corrected_sentence_sg = text.replace(v_word, v_3sg, 1)
                    replacements.append(corrected_sentence_sg)

                subj_word = subj_token.get("word") if subj_token else None
                subj_pl = None
                if subj_word and PATTERN_DE_AVAILABLE:
                    try:
                        subj_pl = pluralize(subj_word)
                    except Exception:
                        subj_pl = None
                
                if subj_word and subj_pl and subj_pl != subj_word:
                    corrected_sentence_pl = text.replace(subj_word, subj_pl, 1)
                    replacements.append(corrected_sentence_pl)
                # --- End build suggestions ---

                sva = {
                    "message": "Möglicher Kongruenzfehler: Singular-Subjekt mit pluralischer Verbform.",
                    "rule_id": "HEURISTIC_SUBJ_VERB_AGREEMENT",
                    "category": "Grammar",
                    "incorrect_text": f"{verb_token.get('word')}" if verb_token else "",
                    "replacements": replacements,
                    "offset": None,
                    "length": None,
                    "context": None,
                    "short_message": "Subjekt–Verb-Kongruenz"
                }
                results["grammar_check"] = [sva]
    except Exception as e:
        print(f"SVA Heuristic failed: {e}") # Don't crash, just log
        pass 

    # --- 3. Token-by-Token Deep Dive (Pattern & OdeNet) ---
    print("[Comprehensive Analysis] Running Token Deep Dive...")
    FUNCTION_POS = {"DET","ADP","AUX","PUNCT","SCONJ","CCONJ","PART","PRON","NUM","SYM","X"}
    deep_dive = []
    
    if not spacy_json_output:
        print("[Comprehensive Analysis] No spaCy tokens to analyze. Skipping deep dive.")
    else:
        for token in spacy_json_output:
            word = token.get("word")
            lemma = token.get("lemma")
            pos = (token.get("pos") or "").upper()
            if not word: 
                continue

            print(f"[Deep Dive] Analyzing token: '{word}' (Lemma: '{lemma}')")
            token_analysis = {"word": word, "spacy_pos": pos, "spacy_lemma": lemma}
            
            skip_for_pattern = pos in FUNCTION_POS
            skip_for_wn = pos in FUNCTION_POS or lemma in {None, "", "--"}

            # 3a. Pattern.de Inflection Analysis
            if PATTERN_DE_AVAILABLE and not skip_for_pattern:
                try:
                    # --- FIX: Use spaCy POS to guide Pattern analysis ---
                    desired_type = None
                    if pos in {"VERB","AUX"}: desired_type = "verb"
                    elif pos in {"ADJ","ADV"}: desired_type = "adjective"
                    elif pos in {"NOUN","PROPN"}: desired_type = "noun"
                    
                    pattern_word = lemma if desired_type in {"verb","adjective"} and lemma and lemma != "--" else word
                    
                    pattern_info = pattern_get_all_inflections(pattern_word)
                    token_analysis["pattern_hint"] = pattern_info.get("parser_hint", {})
                    
                    analyses = pattern_info.get("analyses", {})
                    if desired_type and desired_type in analyses:
                        # Filter to only the analysis that matches spaCy's POS
                        token_analysis["pattern_analyses"] = { desired_type: analyses[desired_type] }
                    else:
                        # Otherwise, show all (or none if empty)
                        token_analysis["pattern_analyses"] = analyses
                    # --- End Fix ---

                except Exception as e:
                    token_analysis["pattern_analyses"] = {"error": f"Pattern.de failed: {e}"}
            else:
                token_analysis["pattern_analyses"] = {"info": "Skipped (function word or non-content POS)"}
            
            # 3b. OdeNet Thesaurus (using the lemma)
            lookup_word = lemma if lemma and lemma != "--" else word # Use lemma, but fallback to word
            if WN_AVAILABLE and not skip_for_wn:
                try:
                    thesaurus_info = odenet_get_thesaurus_info(lookup_word)
                    token_analysis["thesaurus_senses"] = thesaurus_info.get("senses", [])
                    if not token_analysis["thesaurus_senses"]:
                        token_analysis["thesaurus_info"] = thesaurus_info.get("info", "No senses found.")
                except Exception as e:
                    token_analysis["thesaurus_senses"] = {"error": f"OdeNet failed: {e}"}
            else:
                token_analysis["thesaurus_senses"] = []
                token_analysis["thesaurus_info"] = "Skipped (function word or missing lemma)."
            
            deep_dive.append(token_analysis)
    
    results["token_deep_dive"] = deep_dive
    print("[Comprehensive Analysis] Analysis complete.")
    return results

# ============================================================================
# 8. GRADIO UI CREATION
# ============================================================================

def create_spacy_tab():
    """Creates the UI for the spaCy tab."""
    config = SPACY_UI_TEXT["en"]
    model_choices = list(SPACY_MODEL_INFO.keys())
    
    with gr.Row():
        ui_lang_radio = gr.Radio(["DE", "EN", "ES"], label=config["ui_lang_label"], value="EN")
        model_lang_radio = gr.Radio(
            choices=[(SPACY_MODEL_INFO[k][0], k) for k in model_choices],
            label=config["model_lang_label"],
            value=model_choices[0]
        )
    
    markdown_title = gr.Markdown(config["title"])
    markdown_subtitle = gr.Markdown(config["subtitle"])
    text_input = gr.Textbox(label=config["input_label"], placeholder=config["input_placeholder"], lines=5)
    analyze_button = gr.Button(config["button_text"], variant="primary")
    
    with gr.Tabs():
        with gr.Tab(config["tab_graphic"]) as tab_graphic:
            html_dep_out = gr.HTML(label=config["html_label"])
        with gr.Tab(config["tab_ner"]) as tab_ner:
            html_ner_out = gr.HTML(label=config["ner_label"])
        with gr.Tab(config["tab_table"]) as tab_table:
            df_out = gr.DataFrame(label=config["table_label"], headers=config["table_headers"], interactive=False)
        with gr.Tab(config["tab_json"]) as tab_json:
            json_out = gr.JSON(label=config["json_label"])
    
    analyze_button.click(fn=spacy_get_analysis, 
                         inputs=[ui_lang_radio, model_lang_radio, text_input],
                         outputs=[df_out, json_out, html_dep_out, html_ner_out, analyze_button], 
                         api_name="get_morphology") # Preserved original API name
    
    ui_lang_radio.change(fn=spacy_update_ui, 
                         inputs=ui_lang_radio,
                         outputs=[markdown_title, markdown_subtitle, ui_lang_radio, model_lang_radio,
                                  text_input, analyze_button, tab_graphic, tab_table, tab_json, tab_ner,
                                  html_dep_out, df_out, json_out, html_ner_out])

def create_languagetool_tab():
    """Creates the UI for the LanguageTool tab."""
    gr.Markdown("# 🇩🇪 German Grammar & Spelling Checker")
    gr.Markdown("Powered by `language-tool-python`. This service checks German text for grammatical errors and spelling mistakes.")
    
    with gr.Column():
        text_input = gr.Textbox(
            label="German Text to Check",
            placeholder="e.g., Ich sehe dem Mann. Das ist ein Huas.",
            lines=5
        )
        check_button = gr.Button("Check Text", variant="primary")
    
    output = gr.JSON(label="Detected Errors (JSON)")

    check_button.click(
        fn=lt_check_grammar,
        inputs=[text_input],
        outputs=[output],
        api_name="check_grammar" # Preserved original API name
    )
    
    gr.Examples(
        [["Das ist ein Huas."], ["Ich sehe dem Mann."],
         ["Die Katze schlafen auf dem Tisch."], ["Er fragt ob er gehen kann."]],
        inputs=[text_input], outputs=[output], fn=lt_check_grammar
    )

def create_odenet_tab():
    """Creates the UI for the OdeNet tab."""
    gr.Markdown("# 🇩🇪 German Thesaurus (WordNet) Service")
    gr.Markdown("Powered by `wn` and `OdeNet (odenet:1.4)`. Finds synonyms, antonyms, and other semantic relations for German words.")
    
    with gr.Column():
        word_input = gr.Textbox(
            label="German Word",
            placeholder="e.g., Haus, schnell, gut, Katze"
        )
        check_button = gr.Button("Find Relations", variant="primary")
    
    output = gr.JSON(label="Thesaurus Information (JSON)")

    check_button.click(
        fn=odenet_get_thesaurus_info,
        inputs=[word_input],
        outputs=[output],
        api_name="get_thesaurus" # Preserved original API name
    )
    
    gr.Examples(
        [["Hund"], ["gut"], ["laufen"], ["Haus"], ["schnell"]],
        inputs=[word_input], outputs=[output], fn=odenet_get_thesaurus_info
    )

def create_pattern_tab():
    """Creates the UI for the Pattern.de tab."""
    gr.Markdown("# 🇩🇪 Complete German Word Inflection System")
    gr.Markdown("Powered by `PatternLite`. Generates complete inflection tables (declension, conjugation) for German words.")
    
    with gr.Column():
        word_input = gr.Textbox(
            label="German Word",
            placeholder="z.B. Haus, gehen, schön, besser, lief"
        )
        generate_button = gr.Button("Generate All Forms", variant="primary")
    
    output = gr.JSON(label="Complete Inflection Analysis")

    generate_button.click(
        fn=pattern_get_all_inflections,
        inputs=[word_input],
        outputs=[output],
        api_name="get_all_inflections" # Preserved original API name
    )
    
    gr.Examples(
        [["Haus"], ["gehen"], ["schön"], ["besser"], ["ging"], ["schnellem"], ["Katze"]],
        inputs=[word_input], outputs=[output], fn=pattern_get_all_inflections
    )

def create_combined_tab():
    """Creates the UI for the new Comprehensive Analyzer tab."""
    gr.Markdown("# 🇩🇪 Comprehensive German Text Analyzer")
    gr.Markdown("This tool combines NLP libraries (spaCy, LanguageTool, Pattern, OdeNet) to give a deep analysis of a German text. Results are in JSON format.")
    with gr.Column():
        text_input = gr.Textbox(
            label="German Text",
            placeholder="e.g., Die schnelle Katze springt über den faulen Hund.",
            lines=5
        )
        analyze_button = gr.Button("Run Comprehensive Analysis", variant="primary")
    
    output = gr.JSON(label="Comprehensive Analysis (JSON)")
    
    analyze_button.click(
        fn=comprehensive_german_analysis,
        inputs=[text_input],
        outputs=[output],
        api_name="comprehensive_analysis" # New API endpoint
    )
    
    gr.Examples(
        [["Die Katze schlafen auf dem Tisch."], ["Das ist ein Huas."], ["Ich laufe schnell."]],
        inputs=[text_input], outputs=[output], fn=comprehensive_german_analysis
    )

# --- Main UI Builder ---
def create_consolidated_interface():
    """Builds the final Gradio app with all tabs."""
    with gr.Blocks(title="Consolidated Linguistics Hub", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🏛️ Consolidated Linguistics Hub")
        gr.Markdown("One interface for 4 linguistic tools: spaCy, LanguageTool, Pattern.de, and OdeNet.")
        
        with gr.Tabs():
            # New Combined Tab first
            with gr.Tab("🚀 Comprehensive Analyzer (DE)"):
                create_combined_tab()

            # Original Tabs
            with gr.Tab("🔬 spaCy Analyzer (Multi-lingual)"):
                create_spacy_tab()
            
            with gr.Tab("✅ Grammar Check (DE)"):
                create_languagetool_tab()

            with gr.Tab("📚 Inflections (DE)"):
                create_pattern_tab()

            with gr.Tab("📖 Thesaurus (DE)"):
                create_odenet_tab()
    
    return demo

# ============================================================================
# 9. MAIN EXECUTION BLOCK
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("CONSOLIDATED LINGUISTICS HUB (STARTING)")
    print("="*70 + "\n")

    # --- 1. Initialize spaCy Models ---
    print("--- Initializing spaCy Models ---")
    spacy_initialize_models()
    print("--- spaCy Done ---\n")
    
    # --- 2. Initialize OdeNet Worker ---
    print("--- Initializing OdeNet Worker ---")
    if WN_AVAILABLE:
        try:
            odenet_start_worker()
            print("✓ OdeNet worker is starting/ready.")
        except Exception as e:
            print(f"✗ FAILED to start OdeNet worker: {e}")
            print("  The 'Thesaurus' and 'Comprehensive' tabs may fail.")
    else:
        print("INFO: OdeNet ('wn') library not available, skipping worker.")
    print("--- OdeNet Done ---\n")

    # --- 3. Check LanguageTool ---
    print("--- Checking LanguageTool ---")
    if not LT_AVAILABLE:
        print("WARNING: language-tool-python not available. 'Grammar' tab will fail.")
    else:
        print("✓ LanguageTool library is available (will lazy-load on first use).")
    print("--- LanguageTool Done ---\n")

    # --- 4. Check Pattern.de ---
    print("--- Checking Pattern.de ---")
    if not PATTERN_DE_AVAILABLE:
        print("WARNING: pattern.de library not available. 'Inflections' tab will fail.")
    else:
        print("✓ Pattern.de library is available.")
    print("--- Pattern.de Done ---\n")

    print("="*70)
    print("All services initialized. Launching Gradio Hub...")
    print("="*70 + "\n")
    
    # --- 5. Launch Gradio ---
    demo = create_consolidated_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True)
