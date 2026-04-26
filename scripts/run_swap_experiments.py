import subprocess
import csv
import re
import os
import time

# ===== PATH CONFIG =====
ABC_EXEC = "../abc/abc"
LIB = "../libs/nangate_45.lib"
AES_BENCH = "../designs/aes_orig.bench"
SQRT_BENCH = "../designs/sqrt_orig.bench"
OUTPUT_CSV = "../results/swap_experiment_results.csv"

TIMEOUT_SEC = 120  # generous timeout for default recipes (they expand internally)

# ===== WINNER RECIPES (from Teammate 2's ML optimization) =====
AES_WINNER_RECIPE = [
    "rewrite -z", "refactor -z", "refactor -z", "balance",
    "refactor -z", "rewrite -z", "refactor -z", "balance",
    "refactor -z", "resub -z", "resub", "rewrite -z",
    "resub -z", "refactor -z", "rewrite", "resub -z",
    "balance", "resub -z", "refactor", "resub -z"
]

SQRT_WINNER_RECIPE = [
    "refactor -z", "refactor", "rewrite -z", "rewrite -z",
    "refactor", "balance", "refactor", "refactor",
    "resub", "refactor -z", "refactor", "refactor -z",
    "refactor -z", "resub", "refactor -z", "rewrite",
    "refactor", "refactor -z", "balance", "balance"
]

# ===== EXPERIMENT DEFINITIONS =====
# Each experiment: (run_id, design_name, bench_file, recipe_name, recipe_commands)
# For default recipes (resyn, resyn2, compress2), ABC treats them as built-in aliases
EXPERIMENTS = [
    # Step 1: Default Runs on AES (Design 1)
    (1, "aes", AES_BENCH, "resyn",     ["resyn"]),
    (2, "aes", AES_BENCH, "resyn2",    ["resyn2"]),
    (3, "aes", AES_BENCH, "compress2", ["compress2"]),
    # Step 1: Default Runs on SQRT (Design 2)
    (4, "sqrt", SQRT_BENCH, "resyn",     ["resyn"]),
    (5, "sqrt", SQRT_BENCH, "resyn2",    ["resyn2"]),
    (6, "sqrt", SQRT_BENCH, "compress2", ["compress2"]),
    # Step 2: Winner Swap Runs
    (7, "aes",  AES_BENCH,  "sqrt_winner (Recipe B)", SQRT_WINNER_RECIPE),
    (8, "sqrt", SQRT_BENCH, "aes_winner (Recipe A)",  AES_WINNER_RECIPE),
]

# ===== RUN ABC =====
def run_abc(bench_file, recipe_commands):
    """Run ABC with the given bench file and recipe, return raw stdout."""
    commands = [
        f"read_lib {LIB}",
        f"read_bench {bench_file}",
        "strash",
    ]
    commands.extend(recipe_commands)
    commands.extend(["map", "stime"])

    abc_input = "\n".join(commands) + "\n"

    try:
        result = subprocess.run(
            [ABC_EXEC],
            input=abc_input,
            text=True,
            capture_output=True,
            timeout=TIMEOUT_SEC,
        )
        if result.returncode != 0:
            return "ERROR", result.stderr
        return "SUCCESS", result.stdout
    except subprocess.TimeoutExpired:
        return "TIMEOUT", None
    except Exception as e:
        return "EXCEPTION", str(e)

# ===== PARSE OUTPUT =====
def extract_metrics(output):
    """Extract Area and Delay from ABC stime output."""
    area_match = re.search(r"Area\s*=\s*([\d\.]+)", output)
    delay_match = re.search(r"Delay\s*=\s*([\d\.]+)", output)

    if not area_match or not delay_match:
        return None, None

    try:
        return float(area_match.group(1)), float(delay_match.group(1))
    except ValueError:
        return None, None

# ===== MAIN =====
def main():
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    results = []

    print("=" * 70)
    print("  ML4EDA: ABC Cross-Testing ('Swap') Experiments")
    print("=" * 70)
    print()

    for run_id, design, bench, recipe_name, recipe_cmds in EXPERIMENTS:
        print(f"  Run {run_id}: {design.upper()} + {recipe_name} ... ", end="", flush=True)

        start = time.time()
        status, output = run_abc(bench, recipe_cmds)
        elapsed = time.time() - start

        if status == "SUCCESS":
            area, delay = extract_metrics(output)
            if area is None or delay is None:
                status = "PARSE_ERROR"
                print(f"PARSE_ERROR ({elapsed:.1f}s)")
            else:
                print(f"Area={area:.2f}, Delay={delay:.2f} ({elapsed:.1f}s)")
        else:
            area, delay = None, None
            print(f"{status} ({elapsed:.1f}s)")

        recipe_detail = " | ".join(recipe_cmds)
        results.append([run_id, design, recipe_name, area, delay, status, recipe_detail])

    # Write CSV
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["run_id", "design", "recipe_name", "area", "delay", "status", "recipe_detail"])
        writer.writerows(results)

    print()
    print(f"  Results saved to: {OUTPUT_CSV}")
    print()

    # Print formatted summary table
    print("=" * 70)
    print("  FINAL RESULTS SUMMARY (for Teammate 2)")
    print("=" * 70)
    print()
    print(f"  {'Run':<5} {'Design':<8} {'Recipe':<28} {'Area':>12} {'Delay':>12}")
    print(f"  {'-'*5} {'-'*8} {'-'*28} {'-'*12} {'-'*12}")

    for row in results:
        run_id, design, recipe_name, area, delay, status, _ = row
        area_str = f"{area:.2f}" if area else "FAILED"
        delay_str = f"{delay:.2f}" if delay else "FAILED"
        print(f"  {run_id:<5} {design.upper():<8} {recipe_name:<28} {area_str:>12} {delay_str:>12}")

    print()
    print("=" * 70)

if __name__ == "__main__":
    main()
