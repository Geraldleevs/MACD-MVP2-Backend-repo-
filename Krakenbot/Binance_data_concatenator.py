import os
import pandas as pd
from glob import glob
from datetime import datetime

# Specify the directory containing the CSV files
directory = 'rawdata'

# Define the header
header = ['open_time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_time', 'Quote_volume', 'Count', 'Taker_buy_volume', 'Taker_buy_quote_volume', 'Ignore']

# Create a list to store DataFrames
dataframes = []

# Get all files matching the pattern
file_pattern = os.path.join(directory, 'SANDUSDT-1m-202*.csv')
files = sorted(glob(file_pattern))

# Debugging: Print the files found
print(f'Files found: {files}')

# Read each file into a DataFrame and append it to the list
for file in files:
    try:
        df = pd.read_csv(file, header=None, names=header)

        # Convert relevant columns to numeric
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Quote_volume', 'Taker_buy_volume', 'Taker_buy_quote_volume']
        df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')
        
        # Convert 'open_time' and 'close_time' from UNIX time (milliseconds) to datetime
        df['open_time_converted'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close_time_converted'] = pd.to_datetime(df['Close_time'], unit='ms')
        
        dataframes.append(df)
        
        # Debugging: Print the shape of each DataFrame read
        print(f'Read {file}: {df.shape}')
        
    except Exception as e:
        print(f'Error reading {file}: {e}')

# Check if there are any dataframes to concatenate
if dataframes:
    # Concatenate all DataFrames
    concatenated_df = pd.concat(dataframes, ignore_index=True)

    # Save the concatenated DataFrame to a new CSV file with the specified header
    output_file = os.path.join(directory, 'BackTest1yr-Concatenated-SANDUSDT-1m-2023-4.csv')
    concatenated_df.to_csv(output_file, index=False)
    print(f'Concatenated file saved as {output_file}')
else:
    print('No dataframes to concatenate.')
