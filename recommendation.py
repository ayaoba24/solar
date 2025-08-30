import logging
from typing import Dict, Any, Optional

# Import the core functions from our other modules
from system_sizing import load_and_prepare_data, size_complete_system
from cost_estimation import estimate_total_cost

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_recommendation(
    monthly_kwh_consumption: float,
    budget_ngn: Optional[float] = None,
    peak_sun_hours: float = 5.0,
    days_of_autonomy: int = 2,
    data_filepath: str = "cleaned_solar_data.csv"
) -> Optional[Dict[str, Any]]:
    """
    Generates a complete solar system recommendation and cost analysis.

    This is the main engine that integrates all the other modules. It sizes a
    system, estimates its cost, and checks it against a user's budget.

    Args:
        monthly_kwh_consumption (float): The user's monthly energy need in kWh.
        budget_ngn (Optional[float]): The user's optional budget in NGN.
        peak_sun_hours (float): Average peak sun hours for the location.
        days_of_autonomy (int): Desired days of battery backup.
        data_filepath (str): Path to the cleaned component data file.

    Returns:
        A dictionary containing the full recommendation, or None if a system
        cannot be configured.
    """
    logging.info(f"Generating recommendation for {monthly_kwh_consumption} kWh/month consumption.")

    # 1. Load component data
    component_data = load_and_prepare_data(data_filepath)
    if not component_data:
        logging.error("Failed to load component data. Aborting recommendation.")
        return None

    # 2. Size a complete system based on energy needs
    system_recommendation = size_complete_system(
        monthly_kwh_consumption=monthly_kwh_consumption,
        component_data=component_data,
        peak_sun_hours=peak_sun_hours,
        days_of_autonomy=days_of_autonomy
    )
    if not system_recommendation:
        logging.error("Failed to size a system with the given requirements.")
        return None

    # 3. Estimate the cost of the sized system
    cost_analysis = estimate_total_cost(
        system_recommendation=system_recommendation,
        component_data=component_data
    )
    if not cost_analysis:
        logging.error("Failed to estimate cost for the sized system.")
        return None

    # 4. Perform budget check
    is_within_budget = None
    if budget_ngn is not None:
        is_within_budget = cost_analysis['total_system_cost'] <= budget_ngn
        logging.info(f"Budget check: System cost ({cost_analysis['total_system_cost']}) vs Budget ({budget_ngn}). Within budget: {is_within_budget}")

    # 5. Combine all information into a final recommendation object
    # This is the final object that would be passed to a user interface.
    final_recommendation = {
        "user_requirements": {
            "monthly_kwh_consumption": monthly_kwh_consumption,
            "budget_ngn": budget_ngn,
            "peak_sun_hours": peak_sun_hours,
            "days_of_autonomy": days_of_autonomy
        },
        "system_recommendation": system_recommendation,
        "cost_analysis": cost_analysis,
        "budget_analysis": {
            "is_within_budget": is_within_budget
        }
    }

    # Advanced implementation note:
    # To generate multiple options, the `size_complete_system` could be modified
    # to return a list of possible systems (e.g., using different panel models).
    # This engine would then iterate through them, get costs for each, and rank
    # them based on criteria like 'lowest_cost' or 'highest_power_within_budget'.

    return final_recommendation

if __name__ == '__main__':
    print("--- Solar Recommendation Engine Demonstration ---")

    # --- Example 1: User with a clear budget ---
    print("\n--- Example 1: User with 450 kWh/month consumption and a 210,000,000 NGN budget. ---")
    user_kwh_1 = 450
    user_budget_1 = 210_000_000 # 210 Million NGN

    recommendation_1 = generate_recommendation(
        monthly_kwh_consumption=user_kwh_1,
        budget_ngn=user_budget_1
    )

    if recommendation_1:
        import json
        # Using a simple print for readability here, but JSON dump is available
        print("Recommendation Generated!")
        print(f"  - System Cost: {recommendation_1['cost_analysis']['total_system_cost']:,} NGN")
        print(f"  - User Budget: {user_budget_1:,} NGN")
        print(f"  - Is Within Budget? {'Yes' if recommendation_1['budget_analysis']['is_within_budget'] else 'No'}")
        # print(json.dumps(recommendation_1, indent=2)) # For full details

    # --- Example 2: User with no budget specified ---
    print("\n--- Example 2: User with 800 kWh/month consumption and no budget. ---")
    user_kwh_2 = 800

    recommendation_2 = generate_recommendation(
        monthly_kwh_consumption=user_kwh_2
    )

    if recommendation_2:
        print("Recommendation Generated!")
        print(f"  - System Cost: {recommendation_2['cost_analysis']['total_system_cost']:,} NGN")
        print("  - Panel configuration: "
              f"{recommendation_2['system_recommendation']['panel_recommendation']['number_of_panels']}x "
              f"{recommendation_2['system_recommendation']['panel_recommendation']['individual_panel_wattage']}W panels")
        print(f"  - Inverter: {recommendation_2['system_recommendation']['inverter_recommendation']['inverter_rating_kw']} kW")
        print(f"  - Battery capacity: {recommendation_2['system_recommendation']['battery_recommendation']['total_battery_kwh_usable']:.1f} kWh usable")
