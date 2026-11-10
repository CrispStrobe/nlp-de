import gradio as gr
import traceback
from typing import Dict, Any, Set
import threading
import queue
from dataclasses import dataclass
from enum import Enum

# --- Import the 'wn' library ---
try:
    import wn
    WN_AVAILABLE = True
except ImportError:
    print("="*70)
    print("CRITICAL ERROR: `wn` library not found.")
    print("Please install it: pip install wn")
    print("="*70)
    WN_AVAILABLE = False

# ============================================================================
# QUEUE-BASED WORKER (Single Thread for all DB access)
# ============================================================================

@dataclass
class WorkItem:
    """Represents a lookup request."""
    word: str
    response_queue: queue.Queue

class WorkerState(Enum):
    NOT_STARTED = 1
    INITIALIZING = 2
    READY = 3
    ERROR = 4

# Global worker state
worker_state = WorkerState.NOT_STARTED
worker_thread = None
work_queue = queue.Queue()
de_wn = None  # Single WordNet instance for the worker thread

def download_wordnet_data():
    """Download WordNet data. Called once by worker thread."""
    try:
        print("Downloading WordNet data...")
        try:
            wn.download('odenet:1.4')
        except Exception as e:
            print(f"Note: odenet download: {e}")
        
        try:
            wn.download('cili:1.0')
        except Exception as e:
            print(f"Note: cili download: {e}")
        
        print("✓ WordNet data ready")
        return True
    except Exception as e:
        print(f"✗ Failed to download WordNet data: {e}")
        return False


def worker_loop():
    """
    Worker thread main loop.
    This is the ONLY thread that accesses the SQLite database.
    """
    global worker_state, de_wn
    
    try:
        print("[Worker] Starting worker thread...")
        worker_state = WorkerState.INITIALIZING
        
        # Download data if needed
        if not download_wordnet_data():
            worker_state = WorkerState.ERROR
            print("[Worker] Failed to initialize")
            return
        
        # Create single WordNet instance for this worker
        print("[Worker] Creating WordNet instance...")
        de_wn = wn.Wordnet('odenet:1.4')
        worker_state = WorkerState.READY
        print("[Worker] Ready to process requests")
        
        # Process requests from queue
        while True:
            try:
                # Get work item (blocking)
                item: WorkItem = work_queue.get(timeout=1)
                
                # Process the request
                try:
                    result = process_word_lookup(item.word)
                    item.response_queue.put(("success", result))
                except Exception as e:
                    traceback.print_exc()
                    item.response_queue.put(("error", str(e)))
                finally:
                    work_queue.task_done()
                    
            except queue.Empty:
                # No work, continue waiting
                continue
                
    except Exception as e:
        print(f"[Worker] Fatal error: {e}")
        traceback.print_exc()
        worker_state = WorkerState.ERROR


def process_word_lookup(word: str) -> Dict[str, Any]:
    """
    Process a single word lookup.
    This runs in the worker thread with access to de_wn.
    """
    global de_wn
    
    if not word or not word.strip():
        return {"info": "No word provided to check."}
    
    word = word.strip().lower()
    
    # Find all senses
    senses = de_wn.senses(word)
    
    if not senses:
        return {"info": f"The word '{word}' was not found in the thesaurus."}
    
    # Prepare response
    results: Dict[str, Any] = {
        "input_word": word,
        "senses": []
    }
    
    # Loop through each sense
    for sense in senses:
        synset = sense.synset()
        
        # Helper to get lemma strings
        def get_lemmas(synsets, remove_self=False):
            lemmas: Set[str] = set()
            for s in synsets:
                for lemma in s.lemmas():
                    if not (remove_self and lemma.lower() == word):  # OdeNet capitalises nouns
                        lemmas.add(lemma)
            return sorted(list(lemmas))
        
        # Get antonyms
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
    
    print(f"[Worker] Found {len(results['senses'])} senses for '{word}'")
    return results


def start_worker():
    """Start the worker thread if not already started."""
    global worker_thread, worker_state
    
    if worker_state != WorkerState.NOT_STARTED:
        return
    
    worker_thread = threading.Thread(target=worker_loop, daemon=True, name="OdeNetWorker")
    worker_thread.start()
    
    # Wait for initialization
    timeout = 30  # 30 seconds
    for _ in range(timeout * 10):
        if worker_state in (WorkerState.READY, WorkerState.ERROR):
            break
        threading.Event().wait(0.1)
    
    if worker_state != WorkerState.READY:
        raise Exception("Worker failed to initialize")


# ============================================================================
# PUBLIC API (Called by Gradio from any thread)
# ============================================================================

def get_thesaurus_info(word: str) -> Dict[str, Any]:
    """
    Public API: Finds thesaurus info for a German word.
    Thread-safe: Can be called from any Gradio worker thread.
    """
    if not WN_AVAILABLE:
        return {"error": "WordNet service is not available."}
    
    if worker_state != WorkerState.READY:
        return {"error": "WordNet service is not ready yet. Please try again in a moment."}
    
    try:
        # Create response queue for this request
        response_queue = queue.Queue()
        
        # Submit work item
        item = WorkItem(word=word, response_queue=response_queue)
        work_queue.put(item)
        
        # Wait for response (with timeout)
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
# UI
# ============================================================================

def create_interface():
    """Create the Gradio interface."""
    with gr.Blocks(title="German Thesaurus (OdeNet)") as demo:
        gr.Markdown("# 🇩🇪 German Thesaurus (WordNet) Service")
        gr.Markdown("""
        Powered by `wn` and `OdeNet (odenet:1.4)`. 
        
        This service finds synonyms, antonyms, and other semantic relations for German words.
        
        **Thread-safe design**: Uses a queue-based worker for reliable concurrent access.
        """)
        
        with gr.Column():
            word_input = gr.Textbox(
                label="German Word",
                placeholder="e.g., Haus, schnell, gut, Katze"
            )
            check_button = gr.Button("Find Relations", variant="primary")
        
        output = gr.JSON(label="Thesaurus Information (JSON)")

        check_button.click(
            fn=get_thesaurus_info,
            inputs=[word_input],
            outputs=[output],
            api_name="get_thesaurus"
        )
        
        gr.Examples(
            [["Hund"], ["gut"], ["laufen"], ["Haus"], ["schnell"]],
            inputs=[word_input],
            outputs=[output],
            fn=get_thesaurus_info,
        )

    return demo


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if not WN_AVAILABLE:
        print("\nStartup check failed. 'wn' library is not available.")
        exit(1)
    
    print("\n" + "="*70)
    print("GERMAN THESAURUS (OdeNet) SERVICE")
    print("Thread-safe queue-based architecture")
    print("="*70 + "\n")
    
    # Start the worker thread
    try:
        print("Starting worker thread...")
        start_worker()
        print("✓ Worker ready\n")
    except Exception as e:
        print(f"✗ Failed to start worker: {e}")
        exit(1)
    
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0", 
        server_port=7860, 
        show_error=True
    )