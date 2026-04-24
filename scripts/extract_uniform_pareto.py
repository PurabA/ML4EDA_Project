import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def extract_uniform_recipes(csv_filename, design_name, top_percentile=0.05, num_buckets=10, samples_per_bucket=10):
    print(f"\n--- Running Uniform Pareto Extraction for {design_name.upper()} ---")
    
    # 1. Load and Clean Data
    df = pd.read_csv(csv_filename)
    df = df[df['status'] == 'SUCCESS'].copy()
    
    # Calculate Area-Delay Product (ADP)
    df['ADP'] = df['area'] * df['delay']
    
    # 2. Isolate the "Pareto Band" (Top X% of ADP)
    adp_threshold = df['ADP'].quantile(top_percentile)
    band_df = df[df['ADP'] <= adp_threshold].copy()
    
    print(f"Total valid recipes: {len(df)}")
    print(f"Recipes in Top {top_percentile*100}% Band: {len(band_df)}")
    
    # 3. Create Mathematical Delay Buckets
    # Find the min and max delay strictly within the elite band
    min_delay = band_df['delay'].min()
    max_delay = band_df['delay'].max()
    
    # Use pandas to cut the delay space into equal-width bins
    band_df['delay_bucket'] = pd.cut(band_df['delay'], bins=num_buckets, labels=False)
    
    # 4. Extract Top N from each Bucket
    selected_recipes = []
    
    for bucket_id in range(num_buckets):
        bucket_data = band_df[band_df['delay_bucket'] == bucket_id]
        
        # Sort by Area (ascending) to get the best hardware trade-offs in this specific delay zone
        best_in_bucket = bucket_data.sort_values(by='area').head(samples_per_bucket)
        selected_recipes.append(best_in_bucket)
    
    # Combine all extracted buckets into one final dataset
    final_extracted_df = pd.concat(selected_recipes, ignore_index=True)
    
    print(f"Extracted exactly {len(final_extracted_df)} uniformly distributed optimal recipes.")
    
    # Save the extracted recipes for the ML pipeline
    output_csv = f"../results/extracted_uniform_{design_name}.csv"
    final_extracted_df.to_csv(output_csv, index=False)
    print(f"Saved extracted recipes to: {output_csv}")
    
    # 5. Visualization: Proving the Uniform Distribution
    plt.figure(figsize=(12, 8))
    
    # Plot all valid background points (Light Gray)
    plt.scatter(df['delay'], df['area'], color='lightgray', alpha=0.3, s=5, label='All Random Recipes')
    
    # Plot the isolated Top 5% Band (Light Blue)
    plt.scatter(band_df['delay'], band_df['area'], color='lightblue', alpha=0.6, s=15, label=f'Top {top_percentile*100}% ADP Band')
    
    # Highlight the uniformly extracted points (Bright Red)
    plt.scatter(final_extracted_df['delay'], final_extracted_df['area'], 
                color='red', alpha=1.0, s=40, edgecolor='black', zorder=5, 
                label='Extracted Uniform Samples')
    
    # Draw vertical lines to show the bucket boundaries
    bucket_edges = np.linspace(min_delay, max_delay, num_buckets + 1)
    for edge in bucket_edges:
        plt.axvline(x=edge, color='black', linestyle='--', alpha=0.4)
        
    plt.title(f"Uniform Pareto Band Extraction - {design_name.upper()}\n({num_buckets} Buckets, {samples_per_bucket} Samples/Bucket)")
    plt.xlabel("Delay (ps)")
    plt.ylabel("Area (um^2)")
    plt.legend(loc='upper right')
    
    # Save the visualization
    plot_filename = f"../results/uniform_sampling_{design_name}.png"
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved visual proof to: {plot_filename}")

# Execute for both AES and SQRT benchmark designs
if __name__ == "__main__":
    # Adjust parameters: Top 5% band, 10 delay buckets, pull the 10 best areas per bucket
    extract_uniform_recipes('../results/results_aes_full.csv', 'aes', top_percentile=0.05, num_buckets=10, samples_per_bucket=10)
    extract_uniform_recipes('../results/results_sqrt_full.csv', 'sqrt', top_percentile=0.05, num_buckets=10, samples_per_bucket=10)