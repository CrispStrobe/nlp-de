import gradio as gr
import traceback
from typing import List, Dict, Any
import threading

# ============================================================================
# INITIALIZATION
# ============================================================================

# We will use a thread-safe singleton pattern to initialize LanguageTool.
# This means it will be loaded only ONCE, by the first API call.
# This is crucial for Hugging Face Spaces to prevent timeouts on boot.

try:
    import language_tool_python
    LT_AVAILABLE = True
except ImportError:
    print("="*70)
    print("CRITICAL ERROR: `language-tool-python` library not found.")
    print("Please install it: pip install language-tool-python")
    print("The app will not function.")
    print("="*70)
    LT_AVAILABLE = False

# Global variables for our singleton
TOOL_INSTANCE: language_tool_python.LanguageTool = None
TOOL_LOCK = threading.Lock()

def get_language_tool() -> language_tool_python.LanguageTool:
    """
    Thread-safe function to get a single instance of the LanguageTool.
    The first call will be slow as it downloads and starts the Java server.
    Subsequent calls will be instantaneous.
    """
    global TOOL_INSTANCE
    
    if not LT_AVAILABLE:
        raise ImportError("language-tool-python library is not installed.")

    # Fast path: If the tool is already initialized, return it.
    if TOOL_INSTANCE:
        return TOOL_INSTANCE
    
    # Slow path: Tool is not initialized. Acquire the lock.
    with TOOL_LOCK:
        # Check again *inside* the lock, in case another thread
        # initialized it while we were waiting for the lock.
        if TOOL_INSTANCE:
            return TOOL_INSTANCE
        
        # This is the first and only time this code will run.
        try:
            print("Initializing LanguageTool for German (de-DE)...")
            # This downloads the ~200MB .jar file and starts the server
            tool = language_tool_python.LanguageTool('de-DE')
            # Set the .picky attribute on the instance.
            tool.picky = True
            print("LanguageTool (local server) initialized successfully.")
            TOOL_INSTANCE = tool
            return TOOL_INSTANCE
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to initialize LanguageTool: {e}")
            return None

# ============================================================================
# GRAMMAR CHECKING LOGIC
# ============================================================================

def check_grammar(text: str) -> List[Dict[str, Any]]:
    """
    Checks a German text for grammar and spelling errors and returns a JSON list.
    """
    try:
        # Get the singleton instance of the tool.
        # This will be fast after the first call.
        tool = get_language_tool()
        
        if tool is None:
            return [{"error": "LanguageTool service failed to initialize."}]
            
        if not text or not text.strip():
            return [{"info": "No text provided to check."}]

        print(f"Checking text: {text}")
        matches = tool.check(text)
        
        if not matches:
            return [{"info": "No errors found!", "status": "perfect"}]

        # Convert the complex 'match' objects into a simple JSON list
        # This is perfect for our Dart app to consume.
        errors_list = []
        for match in matches:
            error = {
                "message": match.message,
                "rule_id": match.ruleId,
                "category": match.category,
                "incorrect_text": text[match.offset : match.offset + match.errorLength],
                "replacements": match.replacements,
                "offset": match.offset,
                "length": match.errorLength,
            }
            errors_list.append(error)
            
        print(f"Found {len(errors_list)} errors.")
        return errors_list

    except Exception as e:
        traceback.print_exc()
        return [{"error": f"An unexpected error occurred: {str(e)}"}]

# ============================================================================
# UI
# ============================================================================

def create_interface():
    """Create the Gradio interface."""
    with gr.Blocks(title="German Grammar Checker") as demo:
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

        # --- API & Event Listeners ---
        check_button.click(
            fn=check_grammar,
            inputs=[text_input],
            outputs=[output],
            api_name="check_grammar" # This is the API endpoint name
        )
        
        gr.Examples(
            [
                ["Das ist ein Huas."],
                ["Ich sehe dem Mann."],
                ["Die Katze schlafen auf dem Tisch."],
                ["Er fragt ob er gehen kann."]
            ],
            inputs=[text_input],
            outputs=[output],
            fn=check_grammar,
        )

    return demo

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if not LT_AVAILABLE:
        print("\nStartup check failed. language-tool-python is not available.")
    
    print("\n" + "="*70)
    print("GERMAN GRAMMAR CHECKER (Standalone)")
    print("="*70 + "\n")
    
    demo = create_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True)