import pandas as pd
import logging
from typing import Dict, Any, Optional

# For demonstration purposes, we import from other modules
from system_sizing import size_complete_system, load_and_prepare_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_component_price(model: str, model_col: str, price_col: str, df: pd.DataFrame) -> float:
    """Helper function to look up the price of a specific component model."""
    try:
        price = df.loc[df[model_col] == model, price_col].iloc[0]
        return float(price)
    except (IndexError, KeyError):
        logging.warning(f"Could not find price for model '{model}' in column '{model_col}'. Defaulting to 0.")
        return 0.0

def estimate_total_cost(
    system_recommendation: Dict[str, Any],
    component_data: Dict[str, pd.DataFrame],
    installation_cost_percentage: float = 0.15
) -> Optional[Dict[str, Any]]:
    """
    Estimates the total cost of a recommended solar system.

    Args:
        system_recommendation (Dict): The dictionary output from size_complete_system.
        component_data (Dict): The dictionary of component DataFrames.
        installation_cost_percentage (float): The percentage of equipment cost to add
                                              for installation. Defaults to 0.15 (15%).

    Returns:
        A dictionary with a detailed cost breakdown, or None if inputs are invalid.
    """
    if not all(k in system_recommendation for k in ['panel_recommendation', 'inverter_recommendation', 'battery_recommendation']):
        logging.error("Invalid system_recommendation object provided.")
        return None

    panel_rec = system_recommendation['panel_recommendation']
    inverter_rec = system_recommendation['inverter_recommendation']
    battery_rec = system_recommendation['battery_recommendation']

    panels_df = component_data['panels']
    inverters_df = component_data['inverters']
    batteries_df = component_data['batteries']

    price_col = 'Component_Price_NGN' # Using Nigerian Naira for costing

    # 1. Calculate cost of each component type
    panel_price_per_unit = get_component_price(panel_rec['panel_model'], 'Panel_Model', price_col, panels_df)
    total_panel_cost = panel_price_per_unit * panel_rec['number_of_panels']

    inverter_price = get_component_price(inverter_rec['inverter_model'], 'Inverter_Model', price_col, inverters_df)

    battery_price_per_unit = get_component_price(battery_rec['battery_model'], 'Battery_Model', price_col, batteries_df)
    total_battery_cost = battery_price_per_unit * battery_rec['number_of_batteries']

    # 2. Calculate total equipment cost
    total_equipment_cost = total_panel_cost + inverter_price + total_battery_cost

    # 3. Calculate installation cost
    installation_cost = total_equipment_cost * installation_cost_percentage

    # 4. Calculate final total system cost
    total_system_cost = total_equipment_cost + installation_cost

    cost_breakdown = {
        "panel_cost": round(total_panel_cost),
        "inverter_cost": round(inverter_price),
        "battery_cost": round(total_battery_cost),
        "total_equipment_cost": round(total_equipment_cost),
        "estimated_installation_cost": round(installation_cost),
        "total_system_cost": round(total_system_cost),
        "currency": "NGN"
    }

    logging.info(f"Cost estimation complete. Total estimated cost: {cost_breakdown['total_system_cost']} {cost_breakdown['currency']}.")

    return cost_breakdown


if __name__ == '__main__':
    print("--- Solar System Cost Estimation Demonstration ---")

    # Load component data
    DATA_FILE = "cleaned_solar_data.csv"
    components = load_and_prepare_data(DATA_FILE)

    if components:
        # First, get a system recommendation
        monthly_consumption = 450  # in kWh
        system_recommendation = size_complete_system(
            monthly_kwh_consumption=monthly_consumption,
            component_data=components
        )

        if system_recommendation:
            print(f"\nCosting the system for a household with {monthly_consumption} kWh/month consumption...")
            # Now, estimate the cost of that recommendation
            cost_details = estimate_total_cost(system_recommendation, components)

            if cost_details:
                import json

                # Helper to convert numpy types to native Python types for JSON serialization
                def convert_numpy_types(obj):
                    if isinstance(obj, pd.NA):
                        return None
                    if isinstance(obj, (np.integer, pd.Int64Dtype)):
                        return int(obj)
                    elif isinstance(obj, (np.floating, pd.Float64Dtype)):
                        return float(obj)
                    elif isinstance(obj, np.ndarray):
                        return obj.tolist()
                    return obj

                print(json.dumps(cost_details, indent=2, default=convert_numpy_types))

    else:
        print("\nCould not run demonstration because component data failed to load.")
