import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, Any

# Assuming watt_calculation.py is in the same directory
from watt_calculation import calculate_required_wattage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_and_prepare_data(filepath: str) -> Dict[str, pd.DataFrame]:
    """
    Loads the cleaned data and prepares separate DataFrames for major components.

    Args:
        filepath (str): The path to the cleaned data CSV file.

    Returns:
        A dictionary containing separate DataFrames for panels, inverters, and batteries.
    """
    try:
        df = pd.read_csv(filepath)
        logging.info(f"Successfully loaded component data from '{filepath}'.")
    except FileNotFoundError:
        logging.error(f"Component data file not found at '{filepath}'.")
        return {}

    # For simplicity, we drop duplicates based on model numbers for each category
    # to get a cleaner list of available components.
    panels_df = df.dropna(subset=['Panel_Model', 'Panel_Wattage_W']).drop_duplicates(subset=['Panel_Model'])
    inverters_df = df.dropna(subset=['Inverter_Model', 'Inverter_Rating_kW']).drop_duplicates(subset=['Inverter_Model'])
    batteries_df = df.dropna(subset=['Battery_Model', 'Battery_Capacity_kWh_Usable']).drop_duplicates(subset=['Battery_Model'])

    return {
        "panels": panels_df,
        "inverters": inverters_df,
        "batteries": batteries_df
    }

def recommend_panels(required_wattage: float, panel_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Recommends a solar panel configuration to meet the required wattage.

    Args:
        required_wattage (float): The total required wattage from the solar array.
        panel_df (pd.DataFrame): DataFrame of available solar panels.

    Returns:
        A dictionary with the recommended panel details, or None if no suitable panel is found.
    """
    if panel_df.empty:
        logging.warning("Panel DataFrame is empty. Cannot recommend panels.")
        return None

    # Strategy: Select the most common panel wattage available in the dataset.
    # This represents a "typical" panel a user might buy.
    try:
        target_panel_wattage = panel_df['Panel_Wattage_W'].mode()[0]
    except KeyError:
        logging.error("Column 'Panel_Wattage_W' not found in panel data.")
        return None

    selected_panel = panel_df[panel_df['Panel_Wattage_W'] == target_panel_wattage].iloc[0]

    number_of_panels = np.ceil(required_wattage / target_panel_wattage)

    recommendation = {
        "panel_brand": selected_panel.get('Panel_Brand', 'N/A'),
        "panel_model": selected_panel.get('Panel_Model', 'N/A'),
        "individual_panel_wattage": target_panel_wattage,
        "number_of_panels": int(number_of_panels),
        "total_panel_wattage": int(number_of_panels * target_panel_wattage)
    }
    logging.info(f"Panel recommendation: {recommendation['number_of_panels']} x {recommendation['individual_panel_wattage']}W panels.")
    return recommendation

def recommend_inverter(required_wattage: float, inverter_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Recommends an inverter that can handle the solar array's power.

    Args:
        required_wattage (float): The total wattage of the solar array.
        inverter_df (pd.DataFrame): DataFrame of available inverters.

    Returns:
        A dictionary with the recommended inverter details, or None if no suitable one is found.
    """
    if inverter_df.empty:
        logging.warning("Inverter DataFrame is empty. Cannot recommend inverter.")
        return None

    required_inverter_kw = required_wattage / 1000

    # Strategy: Find the smallest inverter that is still large enough to handle the load.
    # This is often the most cost-effective choice.
    suitable_inverters = inverter_df[inverter_df['Inverter_Rating_kW'] >= required_inverter_kw]

    if suitable_inverters.empty:
        logging.warning(f"No suitable inverter found for a required power of {required_inverter_kw:.2f} kW. Selecting the largest available.")
        # Fallback: recommend the largest inverter available
        best_choice = inverter_df.loc[inverter_df['Inverter_Rating_kW'].idxmax()]
    else:
        # Select the one with the rating closest to our requirement (but still >=)
        best_choice = suitable_inverters.loc[suitable_inverters['Inverter_Rating_kW'].idxmin()]

    recommendation = {
        "inverter_brand": best_choice.get('Inverter_Brand', 'N/A'),
        "inverter_model": best_choice.get('Inverter_Model', 'N/A'),
        "inverter_rating_kw": best_choice.get('Inverter_Rating_kW'),
        "inverter_efficiency": best_choice.get('Inverter_Efficiency_%')
    }
    logging.info(f"Inverter recommendation: {recommendation['inverter_brand']} {recommendation['inverter_model']} ({recommendation['inverter_rating_kw']} kW).")
    return recommendation

def recommend_batteries(daily_kwh_consumption: float, battery_df: pd.DataFrame, days_of_autonomy: int = 2) -> Optional[Dict[str, Any]]:
    """
    Recommends a battery bank configuration.

    Args:
        daily_kwh_consumption (float): The user's average daily energy usage in kWh.
        battery_df (pd.DataFrame): DataFrame of available batteries.
        days_of_autonomy (int): How many days the battery bank should last without sun.

    Returns:
        A dictionary with the recommended battery details, or None if no suitable battery is found.
    """
    if battery_df.empty:
        logging.warning("Battery DataFrame is empty. Cannot recommend batteries.")
        return None

    # Calculate total required usable capacity
    required_usable_kwh = daily_kwh_consumption * days_of_autonomy

    # Strategy: Select the most common battery capacity available.
    try:
        target_battery_kwh = battery_df['Battery_Capacity_kWh_Usable'].mode()[0]
    except KeyError:
        logging.error("Column 'Battery_Capacity_kWh_Usable' not found in battery data.")
        return None

    if target_battery_kwh == 0:
        logging.warning("Most common battery has 0 usable kWh. Cannot proceed.")
        return None

    selected_battery = battery_df[battery_df['Battery_Capacity_kWh_Usable'] == target_battery_kwh].iloc[0]

    number_of_batteries = np.ceil(required_usable_kwh / target_battery_kwh)

    recommendation = {
        "battery_brand": selected_battery.get('Battery_Brand', 'N/A'),
        "battery_model": selected_battery.get('Battery_Model', 'N/A'),
        "individual_battery_kwh_usable": target_battery_kwh,
        "number_of_batteries": int(number_of_batteries),
        "total_battery_kwh_usable": float(number_of_batteries * target_battery_kwh),
        "days_of_autonomy": days_of_autonomy
    }
    logging.info(f"Battery recommendation: {recommendation['number_of_batteries']} x {recommendation['battery_brand']} batteries for {days_of_autonomy} days of autonomy.")
    return recommendation

def size_complete_system(
    monthly_kwh_consumption: float,
    component_data: Dict[str, pd.DataFrame],
    peak_sun_hours: float = 5.0,
    days_of_autonomy: int = 2
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the sizing of a complete solar power system.
    """
    if not all(k in component_data for k in ['panels', 'inverters', 'batteries']):
        logging.error("Component data is missing one or more key DataFrames: 'panels', 'inverters', 'batteries'.")
        return None

    # 1. Calculate required wattage
    required_wattage = calculate_required_wattage(monthly_kwh_consumption, peak_sun_hours)
    if required_wattage == 0:
        return None

    # 2. Recommend panels
    panel_rec = recommend_panels(required_wattage, component_data['panels'])
    if not panel_rec:
        return None # Cannot proceed without panels

    # 3. Recommend inverter based on final panel wattage
    inverter_rec = recommend_inverter(panel_rec['total_panel_wattage'], component_data['inverters'])

    # 4. Recommend batteries based on daily consumption
    daily_kwh = monthly_kwh_consumption / 30
    battery_rec = recommend_batteries(daily_kwh, component_data['batteries'], days_of_autonomy)

    return {
        "system_requirements": {
            "monthly_kwh_consumption": monthly_kwh_consumption,
            "peak_sun_hours": peak_sun_hours,
            "initial_required_wattage": round(required_wattage)
        },
        "panel_recommendation": panel_rec,
        "inverter_recommendation": inverter_rec,
        "battery_recommendation": battery_rec
    }

if __name__ == '__main__':
    print("--- Solar System Sizing Demonstration ---")

    # Load component data
    DATA_FILE = "cleaned_solar_data.csv"
    components = load_and_prepare_data(DATA_FILE)

    if components:
        # Example: A household that consumes 450 kWh per month.
        print("\nExample: Sizing a system for a household with 450 kWh/month consumption.")
        monthly_consumption = 450  # in kWh

        system_recommendation = size_complete_system(
            monthly_kwh_consumption=monthly_consumption,
            component_data=components
        )

        if system_recommendation:
            # Helper to convert numpy types to native Python types for JSON serialization
            def convert_numpy_types(obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                return obj

            import json
            print(json.dumps(system_recommendation, indent=2, default=convert_numpy_types))
    else:
        print("\nCould not run demonstration because component data failed to load.")
