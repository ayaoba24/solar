import pandas as pd
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_data(input_filepath: str, output_filepath: str) -> None:
    """
    Loads solar dataset, cleans it, and saves it to a new CSV file.

    This function performs the following cleaning steps:
    1. Loads data from an Excel file.
    2. Handles missing values by imputing with median/mode.
    3. Removes duplicate rows.
    4. Cleans text data (lowercase, strip whitespace).
    5. Corrects out-of-range numerical values (clips negatives to 0).
    6. Handles outliers by capping them using the IQR method.
    7. Saves the cleaned DataFrame to a CSV file.

    Args:
        input_filepath (str): The path to the raw data Excel file.
        output_filepath (str): The path to save the cleaned data CSV file.
    """
    logging.info(f"Starting data preprocessing for '{input_filepath}'...")

    # 1. Load Data
    try:
        df = pd.read_excel(input_filepath)
        logging.info(f"Successfully loaded data. Shape: {df.shape}")
    except FileNotFoundError:
        logging.error(f"Error: Input file not found at '{input_filepath}'")
        return
    except Exception as e:
        logging.error(f"Error loading Excel file: {e}")
        return

    # 2. Handle Missing Values
    logging.info("Handling missing values...")
    for col in df.columns:
        if df[col].dtype == 'object':
            # Impute categorical columns with mode
            mode_value = df[col].mode()
            if not mode_value.empty:
                df[col] = df[col].fillna(mode_value[0])
        else:
            # Impute numerical columns with median
            df[col] = df[col].fillna(df[col].median())
    logging.info(f"Missing values handled. Total missing values now: {df.isnull().sum().sum()}")

    # 3. Handle Duplicate Entries
    logging.info("Handling duplicate entries...")
    initial_rows = len(df)
    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True, inplace=True)
    logging.info(f"Removed {initial_rows - len(df)} duplicate rows.")

    # 4. Clean Text Data
    logging.info("Cleaning text data (lowercase and stripping whitespace)...")
    text_cols = df.select_dtypes(include=['object']).columns
    for col in text_cols:
        df[col] = df[col].astype(str).str.lower().str.strip()
    logging.info(f"Cleaned text data for columns: {list(text_cols)}")

    # 5. Correct Out-of-Range Numerical Values
    logging.info("Clipping negative values in numerical columns to 0...")
    numeric_cols = df.select_dtypes(include=np.number).columns
    for col in numeric_cols:
        negative_count = (df[col] < 0).sum()
        if negative_count > 0:
            logging.info(f"Found and clipped {negative_count} negative values in '{col}'.")
            df[col] = df[col].clip(lower=0)

    # 6. Handle Outliers using IQR
    logging.info("Handling outliers using the IQR method...")
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        if IQR > 0: # Avoid division by zero or constant columns
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outliers_low = (df[col] < lower_bound).sum()
            outliers_high = (df[col] > upper_bound).sum()

            if outliers_low > 0 or outliers_high > 0:
                logging.info(f"Capping {outliers_low + outliers_high} outliers in '{col}'.")
                df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

    # 7. Save Cleaned Data
    try:
        df.to_csv(output_filepath, index=False)
        logging.info(f"Successfully saved cleaned data to '{output_filepath}'. Final shape: {df.shape}")
    except Exception as e:
        logging.error(f"Error saving cleaned data to CSV: {e}")

if __name__ == '__main__':
    # Define file paths
    # The original notebook used 'ng_solar_dataset_10000 - Copy.xlsx'
    INPUT_FILE = "ng_solar_dataset_10000 - Copy.xlsx"
    OUTPUT_FILE = "cleaned_solar_data.csv"

    # Run the cleaning process
    clean_data(INPUT_FILE, OUTPUT_FILE)
