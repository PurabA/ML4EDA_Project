import subprocess
import random
import csv
import re
import os
import time
import itertools
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

# ===== PATH CONFIG (VERY IMPORTANT) =====
ABC_EXEC = "../abc/abc"   # script runs from scripts/
LIB = "../libs/nangate_45.lib"
BENCH = "../designs/aes_orig.bench"
OUTPUT_CSV = "../results/results_aes.csv"
LOG_FILE = "../results/synthesis_run.log"

# ===== SETTINGS =====
NUM_RECIPES = 10000
RECIPE_LENGTH = 20
TIMEOUT_SEC = 20  # prevent hanging runs

TRANSFORMS = [
    "balance",
    "rewrite",
    "rewrite -z",
    "refactor",
    "refactor -z",
    "resub",
    "resub -z"
]

# ===== LOGGING SETUP =====
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# ===== RECIPE GENERATOR =====
def generate_unique_recipes(num_recipes, length):
    """
    Deterministically assigns the first two transforms (49 combinations) 
    and randomizes the rest, ensuring no duplicates in the final list.
    """
    seen = set()
    recipes = []
    
    # Generate all 49 possible 2-length prefixes
    prefixes = list(itertools.product(TRANSFORMS, repeat=2))
    prefix_idx = 0
    
    logging.info(f"Generating {num_recipes} unique recipes...")
    
    while len(recipes) < num_recipes:
        # Pick the next prefix sequentially
        prefix = list(prefixes[prefix_idx % len(prefixes)])
        # Randomize the rest of the recipe
        suffix = [random.choice(TRANSFORMS) for _ in range(length - 2)]
        
        recipe = prefix + suffix
        recipe_tuple = tuple(recipe) # Tuples are hashable, lists are not
        
        if recipe_tuple not in seen:
            seen.add(recipe_tuple)
            recipes.append(recipe)
        
        prefix_idx += 1

    logging.info("Recipe generation complete.")
    return recipes

# ===== RUN ABC =====
def run_abc(recipe):
    commands = [
        f"read_lib {LIB}",
        f"read_bench {BENCH}",
        "strash"
    ]
    commands.extend(recipe)
    commands.extend(["map", "stime"])

    abc_input = "\n".join(commands) + "\n"

    try:
        result = subprocess.run(
            [ABC_EXEC],
            input=abc_input,
            text=True,
            capture_output=True,
            timeout=TIMEOUT_SEC
        )
        # Check if abc failed internally (e.g., segfault)
        if result.returncode != 0:
            return "ERROR_RETURN_CODE", result.stderr
            
        return "SUCCESS", result.stdout

    except subprocess.TimeoutExpired:
        return "TIMEOUT", None
    except Exception as e:
        return "EXCEPTION", str(e)

# ===== PARSE OUTPUT =====
def extract_metrics(output):
    # Area = 19382.62   Delay = 996.42 ps
    area_match = re.search(r"Area\s*=\s*([\d\.]+)", output)
    delay_match = re.search(r"Delay\s*=\s*([\d\.]+)", output)

    if not area_match or not delay_match:
        return None, None

    try:
        area = float(area_match.group(1))
        delay = float(delay_match.group(1))
        return area, delay
    except ValueError:
        return None, None

# ===== WORKER WRAPPER =====
def worker_task(task_id, recipe):
    """Function executed by each independent process."""
    status, output = run_abc(recipe)
    
    if status != "SUCCESS":
        return task_id, recipe, None, None, status
        
    area, delay = extract_metrics(output)
    if area is None or delay is None:
        return task_id, recipe, None, None, "PARSE_ERROR"
        
    return task_id, recipe, area, delay, "SUCCESS"

# ===== MAIN LOOP =====
def main():
    recipes = generate_unique_recipes(NUM_RECIPES, RECIPE_LENGTH)
    
    # Check if file exists to write header safely
    file_exists = os.path.isfile(OUTPUT_CSV) and os.path.getsize(OUTPUT_CSV) > 0
    
    start_time = time.time()
    completed = 0
    successful = 0
    
    logging.info(f"Starting multiprocessing pool with {os.cpu_count()} cores...")

    # Using 'a' mode ensures we don't overwrite partial runs if we restart
    with open(OUTPUT_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["id", "area", "delay", "status", "recipe"])

        # Create process pool 
        with ProcessPoolExecutor() as executor:
            # Submit all tasks to the pool
            futures = {executor.submit(worker_task, i, r): i for i, r in enumerate(recipes)}
            
            try:
                # as_completed yields tasks as soon as they finish, regardless of start order
                for future in as_completed(futures):
                    task_id, recipe, area, delay, status = future.result()
                    recipe_str = " | ".join(recipe)
                    
                    completed += 1
                    
                    # Write immediately to CSV and flush to disk
                    writer.writerow([task_id, area if area else "", delay if delay else "", status, recipe_str])
                    f.flush() 

                    if status == "SUCCESS":
                        successful += 1
                        logging.debug(f"[{task_id}] Area={area:.2f}, Delay={delay:.2f}")
                    else:
                        logging.warning(f"[{task_id}] FAILED: {status}")

                    # Progress update
                    if completed % 100 == 0:
                        elapsed = time.time() - start_time
                        speed = completed / elapsed
                        logging.info(f"--- {completed}/{NUM_RECIPES} runs done | {successful} successful | {elapsed:.1f}s elapsed ({speed:.2f} runs/sec) ---")
                        
            except KeyboardInterrupt:
                logging.error("Execution interrupted by user. Shutting down pool safely...")
                executor.shutdown(wait=False, cancel_futures=True)
                logging.info(f"Partial results ({completed} runs) have been safely saved to {OUTPUT_CSV}.")
                return

    total_time = time.time() - start_time
    logging.info(f"DONE. Completed {completed} runs in {total_time:.2f}s.")

if __name__ == "__main__":
    main()