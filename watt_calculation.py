import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
DAYS_IN_MONTH = 30
SYSTEM_LOSS_FACTOR = 1.25 # Accounts for ~25% energy loss in the system (inverter, wiring, dirt, etc.)

def calculate_required_wattage(
    monthly_kwh_consumption: float,
    peak_sun_hours: float = 5.0
) -> float:
    """
    Calculates the required solar panel wattage based on energy consumption.

    Args:
        monthly_kwh_consumption (float): The user's total monthly electricity
                                         consumption in kilowatt-hours (kWh).
        peak_sun_hours (float): The average number of hours per day that the
                                sun's intensity is at its peak (1000 W/m^2).
                                Defaults to 5.0, a reasonable average for Nigeria.

    Returns:
        float: The total DC wattage required from the solar panel array.
    """
    if monthly_kwh_consumption <= 0:
        logging.warning("Monthly consumption must be a positive value.")
        return 0.0
    if peak_sun_hours <= 0:
        logging.warning("Peak sun hours must be a positive value.")
        return 0.0

    # 1. Calculate average daily energy consumption in kWh
    daily_kwh_consumption = monthly_kwh_consumption / DAYS_IN_MONTH
    logging.info(f"Average daily consumption: {daily_kwh_consumption:.2f} kWh")

    # 2. Account for system losses
    # The solar array needs to generate more power than consumed to make up for losses.
    required_daily_generation = daily_kwh_consumption * SYSTEM_LOSS_FACTOR
    logging.info(f"Required daily generation (after accounting for losses): {required_daily_generation:.2f} kWh")

    # 3. Calculate the required DC power of the solar array in kW
    # This is the amount of power the panels need to produce each hour during peak sun.
    required_kw_power = required_daily_generation / peak_sun_hours
    logging.info(f"Required solar array power: {required_kw_power:.2f} kW")

    # 4. Convert kW to Watts
    required_wattage = required_kw_power * 1000

    logging.info(f"Total required solar panel wattage: {required_wattage:.2f} W")

    return required_wattage

if __name__ == '__main__':
    # This is a simple demonstration of how to use the function.
    print("--- Solar Wattage Calculator ---")

    # Example 1: A household that consumes 450 kWh per month.
    print("\nExample 1: Calculating for a household with 450 kWh/month consumption.")
    monthly_consumption_1 = 450  # in kWh
    required_watts_1 = calculate_required_wattage(monthly_consumption_1)
    print(f"For a monthly consumption of {monthly_consumption_1} kWh, the recommended solar panel wattage is approximately {required_watts_1:.0f} W.")

    # Example 2: A small office that consumes 800 kWh per month with better sun exposure.
    print("\nExample 2: Calculating for an office with 800 kWh/month consumption and 6 PSH.")
    monthly_consumption_2 = 800  # in kWh
    peak_sun_hours_2 = 6.0
    required_watts_2 = calculate_required_wattage(monthly_consumption_2, peak_sun_hours=peak_sun_hours_2)
    print(f"For a monthly consumption of {monthly_consumption_2} kWh and {peak_sun_hours_2} peak sun hours, the recommended solar panel wattage is approximately {required_watts_2:.0f} W.")
