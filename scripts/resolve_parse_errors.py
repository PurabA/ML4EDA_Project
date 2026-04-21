import subprocess
import random
import csv
import re
import os
import time
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

# ===== PATH & FILE CONFIGURATION =====
ABC_EXEC = "../abc/abc"
LIB = "../libs/nangate_45.lib"
BENCH = "../designs/sqrt_orig.bench"
CSV_FILE = "../results/results_sqrt_full.csv"
TEMP_CSV_FILE = "../results/results_temp.csv"
LOG_FILE = "../results/error_resolution.log"

# ===== SETTINGS =====
RECIPE_LENGTH = 20
TIMEOUT_SEC = 20

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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# ===== CORE FUNCTIONS =====
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
        if result.returncode != 0:
            return "ERROR_RETURN_CODE", result.stderr
        return "SUCCESS", result.stdout

    except subprocess.TimeoutExpired:
        return "TIMEOUT", None
    except Exception as e:
        return "EXCEPTION", str(e)

def extract_metrics(output):
    area_match = re.search(r"Area\s*=\s*([\d\.]+)", output)
    delay_match = re.search(r"Delay\s*=\s*([\d\.]+)", output)

    if not area_match or not delay_match:
        return None, None

    try:
        return float(area_match.group(1)), float(delay_match.group(1))
    except ValueError:
        return None, None

# ===== WORKER TASK =====
def repair_worker(row_idx, original_id):
    """Generates a new random recipe, runs ABC, and returns the updated row data."""
    new_recipe = [random.choice(TRANSFORMS) for _ in range(RECIPE_LENGTH)]
    new_recipe_str = " | ".join(new_recipe)
    
    status, output = run_abc(new_recipe)
    
    if status != "SUCCESS":
        return row_idx, original_id, "", "", status, new_recipe_str
        
    area, delay = extract_metrics(output)
    if area is None or delay is None:
        return row_idx, original_id, "", "", "PARSE_ERROR", new_recipe_str
        
    return row_idx, original_id, area, delay, "SUCCESS", new_recipe_str

# ===== MAIN LOOP =====
def main():
    if not os.path.exists(CSV_FILE):
        logging.error(f"Target CSV file not found: {CSV_FILE}")
        return 0

    # 1. Read the existing CSV into memory
    logging.info(f"Reading data from {CSV_FILE}...")
    rows = []
    failed_indices = []
    
    with open(CSV_FILE, "r") as f:
        reader = csv.reader(f)
        header = next(reader)
        for i, row in enumerate(reader):
            rows.append(row)
            # Assuming row format: [id, area, delay, status, recipe]
            if len(row) >= 4 and row[3] == "PARSE_ERROR":
                failed_indices.append(i)

    num_failed = len(failed_indices)
    logging.info(f"Found {num_failed} rows with PARSE_ERROR out of {len(rows)} total rows.")

    if num_failed == 0:
        logging.info("No errors to resolve. Exiting.")
        return 0

    # 2. Process the failed rows using Multiprocessing
    start_time = time.time()
    completed = 0
    successful_repairs = 0

    logging.info(f"Starting multiprocessing pool with {os.cpu_count()} cores to resolve errors...")

    with ProcessPoolExecutor() as executor:
        # Pass the list index (row_idx) and the actual recipe ID (original_id) to the worker
        futures = {executor.submit(repair_worker, idx, rows[idx][0]): idx for idx in failed_indices}
        
        try:
            for future in as_completed(futures):
                row_idx, original_id, area, delay, status, recipe_str = future.result()
                
                # Update the row in memory
                rows[row_idx] = [original_id, area if area else "", delay if delay else "", status, recipe_str]
                
                completed += 1
                if status == "SUCCESS":
                    successful_repairs += 1
                    logging.info(f"[Fixed ID: {original_id}] New Area={area:.2f}, New Delay={delay:.2f}")
                else:
                    logging.warning(f"[Failed Again ID: {original_id}] Status: {status}")

        except KeyboardInterrupt:
            logging.error("Interrupted! Will save the partially repaired data...")
            executor.shutdown(wait=False, cancel_futures=True)

    # 3. Write safely back to CSV
    logging.info(f"Writing updated results to temporary file: {TEMP_CSV_FILE}")
    with open(TEMP_CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    # Atomic replace to ensure no data corruption
    os.replace(TEMP_CSV_FILE, CSV_FILE)
    
    total_time = time.time() - start_time
    logging.info(f"DONE. Replaced original CSV safely. Successfully repaired {successful_repairs}/{num_failed} errors in {total_time:.2f}s.")
    return num_failed - successful_repairs

if __name__ == "__main__":
    while True:
        remaining_errors = main()
        if remaining_errors <= 0 or remaining_errors is None:
            break
        logging.info(f"{remaining_errors} errors remain. Retrying...")