#!/bin/bash

# Define the regions and the base URL
regions=("europe-west1")
base_url="daring-blend-452617-n1.ew.r.appspot.com"  # Cloud app domain without protocol

# Loop through each region and construct the full URL dynamically
for region in "${regions[@]}"
do
  # Construct the full URL dynamically with the region (example for cloud)
  url="https://$region.$base_url"  # Example: https://europe-west1.daring-blend-452617-n1.ew.r.appspot.com
  output_file="results_${region}.json"  # Separate output file for each region
  echo "Running test for $region..."

  # Run the artillery test with the dynamically constructed URL
  artillery run --target "$url" latest.yml --output "$output_file"
done
