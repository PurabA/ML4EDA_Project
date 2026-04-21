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

```
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

## 📊 Output

CSV format:

```
id, area, delay, status, recipe
```

Example:

```
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

* Heatmap visualization
* ML-based recipe prediction
* Cut-based optimization inside ABC

---

## 👨‍💻 Author

Purab
