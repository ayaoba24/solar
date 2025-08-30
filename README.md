# Solar Power System Recommender

A command-line interface (CLI) tool to generate solar power system recommendations based on user energy needs and budget. The system sizes a complete setup (panels, inverter, batteries), estimates the cost, and provides a detailed breakdown for users in Nigeria.

## Features

- **Energy-Based Sizing**: Calculates required system size from monthly electricity consumption (kWh).
- **Component Recommendation**: Recommends specific numbers of panels and batteries, and a suitable inverter from a component dataset.
- **Cost Estimation**: Provides a detailed cost breakdown, including equipment and estimated installation fees, in Nigerian Naira (NGN).
- **Budget-Aware**: Checks if the estimated system cost is within a user-specified budget.
- **Interactive CLI**: A user-friendly command-line interface for easy interaction.

## File Structure

This project is broken down into several modules, each handling a specific step of the recommendation process.

- `data_preprocessing.py`: A script to clean and prepare the raw solar component data. It handles missing values, removes duplicates, and saves a clean `cleaned_solar_data.csv` file for the other modules to use.
- `watt_calculation.py`: A module to calculate the required solar array wattage based on the user's monthly energy consumption.
- `system_sizing.py`: This module contains the logic to recommend a complete system configuration. It selects an appropriate number of panels, a suitable inverter, and a correctly sized battery bank from the cleaned data.
- `cost_estimation.py`: This module takes a system configuration and estimates the total cost by looking up component prices in the dataset.
- `recommendation.py`: The core recommendation engine that integrates all the other modules. It takes user requirements, orchestrates the sizing and costing, and produces a final, complete recommendation object.
- `app.py`: The main entry point for the user. It provides a simple CLI to interact with the recommendation engine and displays the results in a human-readable format.
- `nigeria_solar_scraper.py`: (Original file) A script to scrape solar component data from Nigerian e-commerce websites.
- `Solar_Data_Cleaning.ipynb`: (Original file) A Jupyter Notebook for initial exploratory data analysis and cleaning, the logic of which was ported to `data_preprocessing.py`.
- `ng_solar_dataset_10000 - Copy.xlsx`: (Original file) The raw dataset used for this project.

## Setup and Installation

1.  **Prerequisites**: Ensure you have Python 3.7+ installed.
2.  **Clone the repository** (if applicable).
3.  **Install dependencies**: This project uses several Python libraries, such as `pandas` and `numpy`. Install them using the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Prepare Data**: The application relies on the cleaned data file. Run the preprocessing script once to generate it:
    ```bash
    python data_preprocessing.py
    ```

## Usage

To run the application, execute the `app.py` script from your terminal:

```bash
python app.py
```

The application will then guide you through a series of prompts to get your system requirements.

### Example Session

```
--- Welcome to the Solar System Recommender ---
Please provide some details about your energy needs.
Enter your average monthly electricity consumption in kWh: 450
Enter your budget in NGN (optional, press Enter to skip): 210000000
Enter desired days of battery backup (default: 2): 2

Thank you! Generating your recommendation, please wait...

==================================================
      Solar System Recommendation Report
==================================================

[+] Your Requirements:
  - Monthly Energy Consumption: 450.0 kWh
  - Your Budget: 210,000,000 NGN
  - Desired Battery Autonomy: 2 day(s)

[+] Panel Recommendation:
  - Component: 10 x Trina Solar TSM-400DE19 panels
  - Power per Panel: 400W
  - Total Array Power: 4000W

[+] Inverter Recommendation:
  - Component: Prag HYBRID 5KVA/48V
  - Inverter Rating: 4.0 kW

[+] Battery Recommendation:
  - Component: 25 x Rocket ESC200-12 batteries
  - Total Usable Capacity: 30.0 kWh

[+] Estimated Cost Analysis:
  - Panels Cost: 50,308,200 NGN
  - Inverter Cost: 4,198,905 NGN
  - Batteries Cost: 125,770,500 NGN
  -------------------------
  - Total Equipment Cost: 180,277,605 NGN
  - Estimated Installation: 27,041,641 NGN
  =========================
  - TOTAL ESTIMATED SYSTEM COST: 207,319,246 NGN

[+] Budget Verdict: ✅ This system is within your budget!

==================================================
Disclaimer: All costs are estimates based on available data.
==================================================
```
