import subprocess
import random
import csv
import re
import os
import time

# ===== PATH CONFIG (VERY IMPORTANT) =====
ABC_EXEC = "../abc/abc"   # script runs from scripts/
LIB = "../libs/nangate_45.lib"
BENCH = "../designs/aes_orig.bench"
OUTPUT_CSV = "../results/results_aes.csv"

# ===== SETTINGS =====
NUM_RECIPES = 7
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

# ===== RECIPE GENERATOR =====
def generate_recipe():
    return [random.choice(TRANSFORMS) for _ in range(RECIPE_LENGTH)]

# ===== RUN ABC =====
def run_abc(recipe):
    commands = [
        f"read_lib {LIB}",
        f"read_bench {BENCH}",
        "strash"
    ]

    commands.extend(recipe)

    commands.extend([
        "map",
        "stime"
    ])

    abc_input = "\n".join(commands) + "\n"

    try:
        result = subprocess.run(
            [ABC_EXEC],
            input=abc_input,
            text=True,
            capture_output=True,
            timeout=TIMEOUT_SEC
        )
        return result.stdout

    except subprocess.TimeoutExpired:
        return "TIMEOUT"

# ===== PARSE OUTPUT =====
def extract_metrics(output):
    if output == "TIMEOUT":
        return None, None

    # Example line:
    # Area = 19382.62   Delay = 996.42 ps
    area_match = re.search(r"Area\s*=\s*([\d\.]+)", output)
    delay_match = re.search(r"Delay\s*=\s*([\d\.]+)", output)

    if not area_match or not delay_match:
        return None, None

    try:
        area = float(area_match.group(1))
        delay = float(delay_match.group(1))
        return area, delay
    except:
        return None, None

# ===== MAIN LOOP =====
def main():
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "area", "delay", "recipe"])

        start_time = time.time()

        for i in range(NUM_RECIPES):
            recipe = generate_recipe()
            recipe_str = " | ".join(recipe)

            output = run_abc(recipe)
            area, delay = extract_metrics(output)

            # Logging
            if area is None or delay is None:
                print(f"[{i}] FAILED")
            else:
                print(f"[{i}] Area={area:.2f}, Delay={delay:.2f}")

            writer.writerow([i, area, delay, recipe_str])

            # Progress update every 100 runs
            if i % 100 == 0 and i > 0:
                elapsed = time.time() - start_time
                print(f"--- {i} runs done | {elapsed:.1f}s elapsed ---")

    print("DONE.")

if __name__ == "__main__":
    main()