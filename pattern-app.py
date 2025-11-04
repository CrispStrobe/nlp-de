import gradio as gr
import traceback
from typing import Dict, Any

# --- Import pattern.de functions ---
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
    print("="*70)
    print(f"CRITICAL ERROR: Import failed: {e}")
    print("="*70)
    PATTERN_DE_AVAILABLE = False

VERBOSE = True  # Enable verbose debug output

def log(msg):
    """Print debug messages if verbose mode is on."""
    if VERBOSE:
        print(f"[DEBUG] {msg}")

# ============================================================================
# SMART WORD TYPE DETECTION
# ============================================================================

def detect_word_type(word: str) -> Dict[str, Any]:
    """
    Use pattern.de's parser as a hint, but also use heuristics.
    """
    log(f"Detecting type for: {word}")
    
    parser_result = {'pos': None, 'lemma': word, 'type': None}
    
    try:
        parsed = parse(word, lemmata=True)
        for sentence in split(parsed):
            if sentence.words:
                w = sentence.words[0]
                parser_result['pos'] = w.type or ""
                parser_result['lemma'] = w.lemma or word
                
                if w.type and w.type.startswith('NN'):
                    parser_result['type'] = 'noun'
                elif w.type and w.type.startswith('VB'):
                    parser_result['type'] = 'verb'
                elif w.type and w.type.startswith('JJ'):
                    parser_result['type'] = 'adjective'
                
                log(f"  Parser says: POS={w.type}, lemma={w.lemma}, type={parser_result['type']}")
    except Exception as e:
        log(f"  Parser failed: {e}")
    
    return parser_result


def is_good_analysis(analysis, analysis_type):
    """Check if an analysis has meaningful data."""
    if not analysis:
        return False
    
    if analysis_type == 'noun':
        # Must have declension data
        return len(analysis.get('declension', {})) >= 4
    
    elif analysis_type == 'verb':
        # Must have at least 4 present tense forms
        present = analysis.get('conjugation', {}).get('Präsens', {})
        if len(present) < 4:
            return False
        # All forms shouldn't be identical
        unique_forms = set(present.values())
        if len(unique_forms) < 2:
            return False
        return True
    
    elif analysis_type == 'adjective':
        # Must have attributive data
        return len(analysis.get('attributive', {})) > 0

    return False


# ============================================================================
# COMPREHENSIVE INFLECTION GENERATOR
# ============================================================================

def get_all_inflections(word: str) -> Dict[str, Any]:
    """
    Generates ALL possible inflections for a German word.
    TRUSTS the parser to determine word type.
    """
    if not PATTERN_DE_AVAILABLE:
        return {"error": "`PatternLite` library not installed."}

    if not word or not word.strip():
        return {"info": "Please enter a word."}

    word = word.strip()
    
    log("="*70)
    log(f"ANALYZING: {word}")
    log("="*70)
    
    # Get parser hint - TRUST IT!
    detection = detect_word_type(word)
    
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
        # Only analyze for the detected type (trust the parser!)
        detected_type = detection['type']
        
        if detected_type == 'noun':
            log("\n--- NOUN DETECTED - Analyzing as noun ---")
            noun_analysis = analyze_as_noun(word, detection['lemma'])
            if noun_analysis and is_good_analysis(noun_analysis, 'noun'):
                log("✓ Noun analysis successful")
                results["analyses"]["noun"] = noun_analysis
            else:
                log("✗ Noun analysis failed")
        
        elif detected_type == 'verb':
            log("\n--- VERB DETECTED - Analyzing as verb ---")
            verb_analysis = analyze_as_verb(word, detection['lemma'])
            if verb_analysis and is_good_analysis(verb_analysis, 'verb'):
                log("✓ Verb analysis successful")
                results["analyses"]["verb"] = verb_analysis
            else:
                log("✗ Verb analysis failed")
        
        elif detected_type == 'adjective':
            log("\n--- ADJECTIVE DETECTED - Analyzing as adjective ---")
            adj_analysis = analyze_as_adjective(word, detection['lemma'])
            if adj_analysis and is_good_analysis(adj_analysis, 'adjective'):
                log("✓ Adjective analysis successful")
                results["analyses"]["adjective"] = adj_analysis
            else:
                log("✗ Adjective analysis failed")
        
        else:
            # Parser couldn't detect type - try all analyses as fallback
            log("\n--- TYPE UNKNOWN - Trying all analyses ---")
            
            noun_analysis = analyze_as_noun(word, detection['lemma'])
            if noun_analysis and is_good_analysis(noun_analysis, 'noun'):
                log("✓ Noun analysis is good")
                results["analyses"]["noun"] = noun_analysis
            
            verb_analysis = analyze_as_verb(word, detection['lemma'])
            if verb_analysis and is_good_analysis(verb_analysis, 'verb'):
                log("✓ Verb analysis is good")
                results["analyses"]["verb"] = verb_analysis
            
            adj_analysis = analyze_as_adjective(word, detection['lemma'])
            if adj_analysis and is_good_analysis(adj_analysis, 'adjective'):
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


def analyze_as_noun(word: str, hint_lemma: str = None) -> Dict[str, Any]:
    """Comprehensive noun inflection analysis."""
    log(f"  Analyzing as noun (hint_lemma={hint_lemma})")
    
    analysis = {}
    
    # Try to determine base form
    singular = singularize(word)
    plural = pluralize(word)
    
    log(f"    singularize({word}) = {singular}")
    log(f"    pluralize({word}) = {plural}")
    
    # Determine base form
    if plural != word and singular != word:
        # pluralize changes it => likely already singular
        base = word
        log(f"    Word changes when pluralized => base = {base}")
    elif singular != word:
        # singularize changes it => likely plural
        base = singular
        log(f"    Word changes when singularized => base = {base}")
    elif hint_lemma and hint_lemma != word:
        base = hint_lemma
        log(f"    Using hint lemma => base = {base}")
    else:
        log(f"    Cannot determine base form")
        return None
    
    # Get gender
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
    
    # All case forms with articles
    analysis["declension"] = {}
    
    for number, number_name in [(SINGULAR, "Singular"), (PLURAL, "Plural")]:
        word_form = base if number == SINGULAR else pluralize(base)
        gender_for_article = g if number == SINGULAR else PLURAL
        
        for case, case_name in [(NOMINATIVE, "Nominativ"), (ACCUSATIVE, "Akkusativ"), 
                                 (DATIVE, "Dativ"), (GENITIVE, "Genitiv")]:
            
            try:
                def_art = article(word_form, DEFINITE, gender_for_article, case)
                indef_art = article(word_form, INDEFINITE, gender_for_article, case)
                
                analysis["declension"][f"{case_name} {number_name}"] = {
                    "definite": f"{def_art} {word_form}" if def_art else word_form,
                    "indefinite": f"{indef_art} {word_form}" if indef_art else word_form,
                    "bare": word_form
                }
            except Exception as e:
                log(f"    Failed to get article for {case_name} {number_name}: {e}")
    
    log(f"    Generated {len(analysis.get('declension', {}))} declension forms")
    return analysis


def analyze_as_verb(word: str, hint_lemma: str = None) -> Dict[str, Any]:
    """Comprehensive verb conjugation analysis."""
    log(f"  Analyzing as verb (hint_lemma={hint_lemma})")
    
    # Get lemma
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
    
    # Get lexeme
    try:
        lex = lexeme(verb_lemma)
        if lex and len(lex) > 1:
            analysis["lexeme"] = lex
            log(f"    lexeme has {len(lex)} forms")
    except Exception as e:
        log(f"    Failed to get lexeme: {e}")
    
    # Present tense
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
    
    # Past tense
    analysis["conjugation"]["Präteritum"] = {}
    for alias, name in [("1sgp", "ich"), ("2sgp", "du"), ("3sgp", "er/sie/es"),
                        ("1ppl", "wir"), ("2ppl", "ihr"), ("3ppl", "sie/Sie")]:
        try:
            form = conjugate(verb_lemma, alias)
            if form:
                analysis["conjugation"]["Präteritum"][name] = form
        except:
            pass
    
    # Participles
    analysis["participles"] = {}
    try:
        form = conjugate(verb_lemma, "part")
        if form:
            analysis["participles"]["Partizip Präsens"] = form
    except:
        pass
    
    try:
        form = conjugate(verb_lemma, "ppart")
        if form:
            analysis["participles"]["Partizip Perfekt"] = form
    except:
        pass
    
    # Imperative
    analysis["conjugation"]["Imperativ"] = {}
    for alias, name in [("2sg!", "du"), ("2pl!", "ihr")]:
        try:
            form = conjugate(verb_lemma, alias)
            if form:
                analysis["conjugation"]["Imperativ"][name] = form
        except:
            pass
    
    # Subjunctive I
    analysis["conjugation"]["Konjunktiv I"] = {}
    for alias, name in [("1sg?", "ich"), ("2sg?", "du"), ("3sg?", "er/sie/es"),
                        ("1pl?", "wir"), ("2pl?", "ihr"), ("3pl?", "sie/Sie")]:
        try:
            form = conjugate(verb_lemma, alias)
            if form:
                analysis["conjugation"]["Konjunktiv I"][name] = form
        except:
            pass
    
    # Subjunctive II
    analysis["conjugation"]["Konjunktiv II"] = {}
    for alias, name in [("1sgp?", "ich"), ("2sgp?", "du"), ("3sgp?", "er/sie/es"),
                        ("1ppl?", "wir"), ("2ppl?", "ihr"), ("3ppl?", "sie/Sie")]:
        try:
            form = conjugate(verb_lemma, alias)
            if form:
                analysis["conjugation"]["Konjunktiv II"][name] = form
        except:
            pass
    
    return analysis


def analyze_as_adjective(word: str, hint_lemma: str = None) -> Dict[str, Any]:
    """Comprehensive adjective inflection analysis."""
    log(f"  Analyzing as adjective (hint_lemma={hint_lemma})")
    
    # Get base form
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
    
    # Attributive forms
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
                        "form": attr_form,
                        "example": full_form
                    }
                    attr_count += 1
                except Exception as e:
                    log(f"    Failed attributive for {article_name}/{gender_name}/{case_name}: {e}")
    
    log(f"    Generated {attr_count} attributive forms")
    
    if attr_count == 0:
        return None
    
    return analysis


# ============================================================================
# UI
# ============================================================================

def create_interface():
    """Create the Gradio interface."""
    with gr.Blocks(title="German Word Inflection") as demo:
        gr.Markdown("# 🇩🇪 Complete German Word Inflection System")
        gr.Markdown("Powered by `PatternLite`. Check the console for verbose debug output!")
        
        with gr.Column():
            word_input = gr.Textbox(
                label="German Word",
                placeholder="z.B. Haus, gehen, schön, besser, lief"
            )
            generate_button = gr.Button("Generate All Forms", variant="primary")
        
        output = gr.JSON(label="Complete Inflection Analysis")

        generate_button.click(
            fn=get_all_inflections,
            inputs=[word_input],
            outputs=[output],
            api_name="get_all_inflections"
        )
        
        gr.Examples(
            [["Haus"], ["gehen"], ["schön"], ["besser"], ["ging"], ["schnellem"], ["Katze"]],
            inputs=[word_input],
            outputs=[output],
            fn=get_all_inflections,
        )

    return demo

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if not PATTERN_DE_AVAILABLE:
        print("\nStartup check failed. PatternLite not available.")
    
    print("\n" + "="*70)
    print("COMPLETE GERMAN INFLECTION SYSTEM (VERBOSE MODE)")
    print("="*70 + "\n")
    
    demo = create_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True)