import gradio as gr
import spacy
from spacy import displacy
import base64
import traceback
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
import importlib
import site

# ============================================================================
# CONFIGURATION
# ============================================================================

MODEL_INFO: Dict[str, Tuple[str, str, str]] = {
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

# --- *** THE FIX IS HERE *** ---
# Added the 'table_headers' key to each language
UI_TEXT = {
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
        "table_headers": ["Wort", "Lemma", "POS", "Tag", "Morphologie", "Abhängigkeit"], # <-- WAS MISSING
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
        "table_headers": ["Word", "Lemma", "POS", "Tag", "Morphology", "Dependency"], # <-- WAS MISSING
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
        "table_headers": ["Palabra", "Lema", "POS", "Etiqueta", "Morfología", "Dependencia"], # <-- WAS MISSING
        "json_label": "Salida JSON",
        "ner_label": "Entidades Nombradas",
        "error_message": "Error: "
    }
}
# --- *** END FIX *** ---

MODELS: Dict[str, Optional[spacy.Language]] = {}

# ============================================================================
# DEPENDENCY INSTALLATION
# ============================================================================

def install_spacy_transformers_once():
    """ Installs spacy-transformers, required for all _trf models. """
    marker_file = Path(".spacy_transformers_installed")
    if marker_file.exists():
        print("✓ spacy-transformers already installed (marker found)")
        return True
    
    print("Installing spacy-transformers (for _trf models)...")
    cmd = [sys.executable, "-m", "pip", "install", "spacy-transformers"]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
        print("✓ Successfully installed spacy-transformers")
        marker_file.touch()
        return True
    except Exception as e:
        print(f"✗ FAILED to install spacy-transformers: {e}")
        if hasattr(e, 'stderr'): print(e.stderr)
        return False

def install_grecy_model_from_github(model_name: str) -> bool:
    """ Installs a greCy model from your specific GitHub Release. """
    marker_file = Path(f".{model_name}_installed")
    if marker_file.exists():
        print(f"✓ {model_name} already installed (marker found)")
        return True

    print(f"Installing grecy model: {model_name}...")

    if model_name == "grc_proiel_trf":
        wheel_filename = "grc_proiel_trf-3.7.5-py3-none-any.whl"
    elif model_name in ["grc_perseus_trf", "grc_proiel_lg", "grc_perseus_lg", 
                        "grc_proiel_sm", "grc_perseus_sm", "grc_ner_trf"]:
        # Note: Wheel name uses underscore (grc_ner_trf), not hyphen
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

# ============================================================================
# MODEL LOADING (LAZY LOADING)
# ============================================================================

def load_spacy_model(model_name: str) -> Optional[spacy.Language]:
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
            return None

def load_grecy_model(model_name: str) -> Optional[spacy.Language]:
    """ Load a grecy model, installing from GitHub if needed. """
    if not install_grecy_model_from_github(model_name):
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

def initialize_models():
    """ Pre-load standard models and ensure _trf dependencies are ready. """
    print("\n" + "="*70)
    print("INITIALIZING MODELS")
    print("="*70 + "\n")
    
    install_spacy_transformers_once()
    
    loaded_count = 0
    spacy_model_count = 0
    
    for lang_code, (lang_name, model_name, model_type) in MODEL_INFO.items():
        if model_type == "spacy":
            spacy_model_count += 1
            print(f"Loading {lang_name} ({model_name})...")
            nlp = load_spacy_model(model_name)
            MODELS[lang_code] = nlp
            if nlp:
                print(f"✓ {lang_name} ready\n")
                loaded_count += 1
            else:
                print(f"✗ {lang_name} FAILED\n")
        else:
            print(f"✓ {lang_name} ({model_name}) will be loaded on first use.\n")
            MODELS[lang_code] = None
    
    print(f"Pre-loaded {loaded_count}/{spacy_model_count} standard models.")
    print("="*70 + "\n")

# ============================================================================
# ANALYSIS (WITH NER)
# ============================================================================

def get_analysis(ui_lang: str, model_lang_key: str, text: str):
    """Analyze text and return results."""
    ui_config = UI_TEXT.get(ui_lang.lower(), UI_TEXT["en"])
    error_prefix = ui_config["error_message"]
    
    try:
        if not text.strip():
            # Return empty values for all outputs
            return ([], [], "<p style='color: orange;'>No text provided.</p>", "",
                    gr.Button(value=ui_config["button_text"], interactive=True))
        
        nlp = MODELS.get(model_lang_key)
        
        if nlp is None:
            print(f"First use of {model_lang_key}. Loading model...")
            if model_lang_key not in MODEL_INFO:
                 raise ValueError(f"Unknown model key: {model_lang_key}")
            _, model_name, model_type = MODEL_INFO[model_lang_key]
            
            if model_type == "grecy":
                nlp = load_grecy_model(model_name)
            else:
                nlp = load_spacy_model(model_name)
            
            if nlp is None:
                MODELS.pop(model_lang_key, None)
                raise ValueError(f"Model for {model_lang_key} ({model_name}) FAILED to load. Check logs.")
            else:
                MODELS[model_lang_key] = nlp
                print(f"✓ {model_lang_key} is now loaded and cached.")
        
        doc = nlp(text)
        
        dataframe_output = []
        json_output = []
        
        for token in doc:
            lemma_str = token.lemma_
            morph_str = str(token.morph) if token.has_morph() else ''
            dep_str = token.dep_ if doc.has_annotation("DEP") else ''
            tag_str = token.tag_ if token.tag_ != "" else ''
            pos_str = token.pos_ if token.pos_ != "" else ''
            
            json_output.append({
                "word": token.text, "lemma": lemma_str, "pos": pos_str,
                "tag": tag_str, "morphology": morph_str, "dependency": dep_str,
                "is_stopword": token.is_stop
            })
            dataframe_output.append([token.text, lemma_str, pos_str, tag_str, morph_str, dep_str])
        
        # --- DEPENDENCY PARSE VISUALIZATION ---
        html_dep_out = ""
        if "parser" in nlp.pipe_names:
            try:
                options = {"compact": True, "bg": "#ffffff", "color": "#000000", "font": "Source Sans Pro"}
                html_svg = displacy.render(doc, style="dep", jupyter=False, options=options)
                svg_b64 = base64.b64encode(html_svg.encode("utf-8")).decode("utf-8")
                html_dep_out = f'<div style="overflow-x: auto; border: 1px solid #e6e9ef; border-radius: 0.25rem; padding: 1rem; line-height: 2.5;"><img src="data:image/svg+xml;base64,{svg_b64}" /></div>'
            except Exception as e:
                html_dep_out = f"<p style='color: orange;'>Visualization error (DEP): {e}</p>"
        else:
            html_dep_out = "<p style='color: orange;'>Dependency parsing ('parser') not available for this model.</p>"
        
        # --- NAMED ENTITY VISUALIZATION (NEW) ---
        html_ner_out = ""
        if "ner" in nlp.pipe_names:
            if doc.ents:
                try:
                    # Let displacy use its default colors
                    html_ner_out = displacy.render(doc, style="ent", jupyter=False)
                    html_ner_out = f'<div style="overflow-x: auto; border: 1px solid #e6e9ef; border-radius: 0.25rem; padding: 1rem; line-height: 2.5;">{html_ner_out}</div>'
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
        # Return error for all 4 outputs
        return ([[f"{error_prefix}{str(e)}"]], {"error": str(e)}, error_html, error_html,
                gr.Button(value=ui_config["button_text"], interactive=True))

# ============================================================================
# UI (UPDATED FOR NER)
# ============================================================================

def update_ui(ui_lang: str):
    """Update UI language."""
    ui_config = UI_TEXT.get(ui_lang.lower(), UI_TEXT["en"])
    return [
        gr.Markdown(value=ui_config["title"]),
        gr.Markdown(value=ui_config["subtitle"]),
        gr.Radio(label=ui_config["ui_lang_label"]),
        gr.Radio(label=ui_config["model_lang_label"]),
        gr.Textbox(label=ui_config["input_label"], placeholder=ui_config["input_placeholder"]),
        gr.Button(value=ui_config["button_text"]),
        gr.Tab(label=ui_config["tab_graphic"]),
        gr.Tab(label=ui_config["tab_table"]),
        gr.Tab(label=ui_config["tab_json"]),
        gr.Tab(label=ui_config["tab_ner"]),
        gr.HTML(label=ui_config["html_label"]),
        gr.DataFrame(label=ui_config["table_label"], headers=ui_config["table_headers"], interactive=False),
        gr.JSON(label=ui_config["json_label"]),
        gr.HTML(label=ui_config["ner_label"])
    ]

def create_interface():
    """Create Gradio interface."""
    config = UI_TEXT["en"]
    model_choices = list(MODEL_INFO.keys())
    
    with gr.Blocks(title="Multilingual Morpho-Syntactic Analyzer") as demo:
        with gr.Row():
            ui_lang_radio = gr.Radio(["DE", "EN", "ES"], label=config["ui_lang_label"], value="EN")
            model_lang_radio = gr.Radio(
                choices=[(MODEL_INFO[k][0], k) for k in model_choices],
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
                # This is the line that was crashing
                df_out = gr.DataFrame(label=config["table_label"], headers=config["table_headers"], interactive=False)
            with gr.Tab(config["tab_json"]) as tab_json:
                json_out = gr.JSON(label=config["json_label"])
        
        analyze_button.click(fn=get_analysis, 
                             inputs=[ui_lang_radio, model_lang_radio, text_input],
                             outputs=[df_out, json_out, html_dep_out, html_ner_out, analyze_button], 
                             api_name="get_morphology")
        
        ui_lang_radio.change(fn=update_ui, 
                             inputs=ui_lang_radio,
                             outputs=[markdown_title, markdown_subtitle, ui_lang_radio, model_lang_radio,
                                      text_input, analyze_button, tab_graphic, tab_table, tab_json, tab_ner,
                                      html_dep_out, df_out, json_out, html_ner_out])
    return demo

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("MULTILINGUAL MORPHO-SYNTACTIC ANALYZER")
    print("="*70 + "\n")
    
    initialize_models()
    
    demo = create_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True)