import sys
from typing import Optional, Dict, Any

# Import the main engine
from recommendation import generate_recommendation

def get_user_input_float(prompt: str, is_optional: bool = False) -> Optional[float]:
    """Helper to get a valid float from the user."""
    while True:
        try:
            response = input(prompt).strip()
            if is_optional and not response:
                return None
            return float(response)
        except ValueError:
            print("Invalid input. Please enter a valid number.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting application.")
            sys.exit(0)

def get_user_input_int(prompt: str, default: int) -> int:
    """Helper to get a valid integer from the user, with a default."""
    while True:
        try:
            response = input(prompt).strip()
            if not response:
                return default
            return int(response)
        except ValueError:
            print("Invalid input. Please enter a valid whole number.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting application.")
            sys.exit(0)

def display_recommendation(rec: Dict[str, Any]):
    """Formats and prints the final recommendation to the console."""
    if not rec:
        print("\nSorry, we could not generate a recommendation based on your inputs.")
        return

    print("\n" + "="*50)
    print("      Solar System Recommendation Report")
    print("="*50)

    # --- System Requirements ---
    reqs = rec['user_requirements']
    print("\n[+] Your Requirements:")
    print(f"  - Monthly Energy Consumption: {reqs['monthly_kwh_consumption']} kWh")
    if reqs['budget_ngn']:
        print(f"  - Your Budget: {reqs['budget_ngn']:,.0f} NGN")
    print(f"  - Desired Battery Autonomy: {reqs['days_of_autonomy']} day(s)")

    # --- Panel Recommendation ---
    panel_rec = rec['system_recommendation']['panel_recommendation']
    print("\n[+] Panel Recommendation:")
    print(f"  - Component: {panel_rec['number_of_panels']} x {panel_rec['panel_brand'].title()} {panel_rec['panel_model'].upper()} panels")
    print(f"  - Power per Panel: {panel_rec['individual_panel_wattage']}W")
    print(f"  - Total Array Power: {panel_rec['total_panel_wattage']}W")

    # --- Inverter Recommendation ---
    inverter_rec = rec['system_recommendation']['inverter_recommendation']
    print("\n[+] Inverter Recommendation:")
    print(f"  - Component: {inverter_rec['inverter_brand'].title()} {inverter_rec['inverter_model'].upper()}")
    print(f"  - Inverter Rating: {inverter_rec['inverter_rating_kw']} kW")

    # --- Battery Recommendation ---
    battery_rec = rec['system_recommendation']['battery_recommendation']
    print("\n[+] Battery Recommendation:")
    print(f"  - Component: {battery_rec['number_of_batteries']} x {battery_rec['battery_brand'].title()} {battery_rec['battery_model'].upper()} batteries")
    print(f"  - Total Usable Capacity: {battery_rec['total_battery_kwh_usable']:.1f} kWh")

    # --- Cost Analysis ---
    cost = rec['cost_analysis']
    print("\n[+] Estimated Cost Analysis:")
    print(f"  - Panels Cost: {cost['panel_cost']:,.0f} NGN")
    print(f"  - Inverter Cost: {cost['inverter_cost']:,.0f} NGN")
    print(f"  - Batteries Cost: {cost['battery_cost']:,.0f} NGN")
    print("  " + "-"*25)
    print(f"  - Total Equipment Cost: {cost['total_equipment_cost']:,.0f} NGN")
    print(f"  - Estimated Installation: {cost['estimated_installation_cost']:,.0f} NGN")
    print("  " + "="*25)
    print(f"  - TOTAL ESTIMATED SYSTEM COST: {cost['total_system_cost']:,.0f} NGN")

    # --- Budget Verdict ---
    budget = rec['budget_analysis']
    if budget['is_within_budget'] is not None:
        if budget['is_within_budget']:
            print("\n[+] Budget Verdict: ✅ This system is within your budget!")
        else:
            print("\n[+] Budget Verdict: ❌ This system is over your budget.")
            over_by = cost['total_system_cost'] - reqs['budget_ngn']
            print(f"     It is approximately {over_by:,.0f} NGN over.")

    print("\n" + "="*50)
    print("Disclaimer: All costs are estimates based on available data.")
    print("="*50)


def main():
    """Main function to run the CLI application."""
    print("--- Welcome to the Solar System Recommender ---")
    print("Please provide some details about your energy needs.")

    # Get user inputs
    kwh = get_user_input_float("Enter your average monthly electricity consumption in kWh: ")
    budget = get_user_input_float("Enter your budget in NGN (optional, press Enter to skip): ", is_optional=True)
    autonomy = get_user_input_int("Enter desired days of battery backup (default: 2): ", default=2)

    print("\nThank you! Generating your recommendation, please wait...")

    # Run the recommendation engine
    final_recommendation = generate_recommendation(
        monthly_kwh_consumption=kwh,
        budget_ngn=budget,
        days_of_autonomy=autonomy
    )

    # Display the formatted results
    display_recommendation(final_recommendation)


if __name__ == '__main__':
    main()
