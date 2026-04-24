# ML-Guided ASIC Synthesis Recipe Exploration (ABC)

## 📌 Overview

This project explores the impact of synthesis recipes on ASIC technology mapping using **Berkeley ABC**.

We generate **10,000 random synthesis recipes (length = 20)** and evaluate their **Area and Delay (QoR)** after mapping using a standard cell library.

---

## 🧠 Objective

* Explore large synthesis search space
* Generate dataset for ML-guided optimization
* Analyze QoR variation across random recipes

---

## ⚙️ Setup

### 1. Clone ABC

```bash
git clone https://github.com/berkeley-abc/abc
cd abc
make
```

### 2. Install dependencies

```bash
sudo apt install libreadline-dev
```

---

## 📁 Project Structure

```bash
ML4EDA_Project/
├── abc/
├── designs/
├── libs/
├── results/
├── scripts/
```

---

## 🧪 Running Experiments

### ✅ Basic (single-thread)

```bash
cd scripts
python3 run_recipes.py
```

### ⚡ Fast (multi-core)

```bash
cd scripts
python3 fast_run_recipes.py
```

### Resolving Parse Errors

Reads results file and using provided bench iteratively runs until all parse errors are resolved

```bash
cd scripts
python3 resolve_parse_errors.py
```

---

## ⚙️ Configuration

Edit inside scripts:

```python
NUM_RECIPES = 10000
RECIPE_LENGTH = 20
BENCH = "../designs/aes_orig.bench"
LIB = "../libs/nangate_45.lib"
```

---

## 🔁 Recipe Generation

Allowed transformations:

* balance
* rewrite
* rewrite -z
* refactor
* refactor -z
* resub
* resub -z

---

### 📈 Heatmap Visualization & Pareto Extraction

**Approach:** We used **Uniform Pareto Band Sampling** to isolate the optimal Area-Delay recipes and extract them evenly across delay tiers, ensuring a structurally diverse, high-quality dataset for ML training.

**Filtering & Extraction Math:** We isolate the **Top 5%** of the 10,000 recipes based on their Area-Delay Product (ADP). To prevent structural bias, we slice the delay spectrum into **10 equal buckets** and extract the **Top 10 most area-efficient recipes** from each bucket. This guarantees a final dataset of exactly **100 highly optimized and structurally diverse recipes** per design.

**Extracted ML Training Data:**

* Generates `extracted_uniform_<design>.csv` containing the final 100 balanced recipes ready for AIG cut extraction.
* Generates `uniform_sampling_<design>.png` heatmaps.

---

## 📊 Output

**Raw Run Data:**

CSV format:

```text
id, area, delay, status, recipe
```

Example:

```text
0,19382.62,996.42,SUCCESS,balance | rewrite | ...
```

---

## ⚠️ Notes

* Only AIG transformations before `map`
* Each run is independent
* Invalid runs logged as:

  * TIMEOUT
  * PARSE_ERROR
  * ERROR_RETURN_CODE

---

## 🚀 Future Work

* ML-based recipe prediction
* Cut-based optimization inside ABC

---

## 👨‍💻 Authors

* **Purab**
* **Maneesh**

---
