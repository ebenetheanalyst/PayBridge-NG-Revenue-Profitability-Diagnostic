"""
config.py  |  PayBridge NG synthetic data generator
Every number that shapes the story lives here. Change a value, rerun generate.py,
and the planted effect gets stronger, weaker or disappears.
"""
from datetime import date
from pathlib import Path

# ----------------------------------------------------------------- basics
SEED = 42
START_DATE = date(2024, 1, 1)
END_DATE = date(2025, 12, 31)
DATE_TABLE_END = date(2026, 1, 15)          # settlement dates can spill past END_DATE
OUT_DIR = Path(__file__).resolve().parent.parent / "output"

N_MERCHANTS = 400
TARGET_DAILY_TXNS = 1300                    # approx. daily attempts when every merchant is active
SIZE_SIGMA = 1.70                           # higher = a few merchants dominate (power-law feel)

# ---------------------------------------------------------- lookup content
CHANNELS = {1: ("POS", "Physical"), 2: ("Web Checkout", "Digital"), 3: ("Mobile App", "Digital"),
            4: ("USSD", "Digital"), 5: ("QR Payment", "Physical")}
PRODUCTS = {1: ("POS Acquiring", "Acquiring", date(2022, 1, 1)),
            2: ("Bank Transfer", "Transfers", date(2022, 1, 1)),
            3: ("Bill Payment", "Payments", date(2023, 6, 1)),
            4: ("Web Checkout", "Acquiring", date(2022, 6, 1))}
CHANNEL_PRODUCT = {1: {1: 1.0}, 2: {4: 0.85, 3: 0.15}, 3: {2: 0.6, 3: 0.4},
                   4: {2: 0.5, 3: 0.5}, 5: {2: 1.0}}

# city: (state, zone, lat, lon, market_type, launch_date, merchant_weight)
LOCATIONS = [
    ("Lagos", "Lagos", "South-West", 6.5244, 3.3792, "Core", date(2021, 1, 1), 0.30),
    ("Abuja", "FCT", "North-Central", 9.0765, 7.3986, "Core", date(2021, 1, 1), 0.14),
    ("Port Harcourt", "Rivers", "South-South", 4.8156, 7.0498, "Core", date(2021, 1, 1), 0.10),
    ("Ibadan", "Oyo", "South-West", 7.3775, 3.9470, "Core", date(2021, 1, 1), 0.08),
    ("Kano", "Kano", "North-West", 12.0022, 8.5920, "Core", date(2021, 6, 1), 0.07),
    ("Kaduna", "Kaduna", "North-West", 10.5105, 7.4165, "Growth", date(2023, 6, 1), 0.04),
    ("Enugu", "Enugu", "South-East", 6.4584, 7.5464, "Growth", date(2023, 6, 1), 0.05),
    ("Benin City", "Edo", "South-South", 6.3350, 5.6037, "Growth", date(2023, 6, 1), 0.04),
    ("Abeokuta", "Ogun", "South-West", 7.1475, 3.3619, "Growth", date(2023, 6, 1), 0.04),
    ("Warri", "Delta", "South-South", 5.5160, 5.7500, "Growth", date(2023, 6, 1), 0.03),
    ("Jos", "Plateau", "North-Central", 9.8965, 8.8583, "New market", date(2025, 2, 1), 0.025),
    ("Owerri", "Imo", "South-East", 5.4836, 7.0333, "New market", date(2025, 3, 1), 0.025),
    ("Ilorin", "Kwara", "North-Central", 8.4966, 4.5421, "New market", date(2025, 4, 1), 0.025),
    ("Uyo", "Akwa Ibom", "South-South", 5.0377, 7.9128, "New market", date(2025, 6, 1), 0.025),
]

# bank: (name, type, market_weight, failure_multiplier)  -- all names are fictional
BANKS = [
    ("Savanna Bank", "Commercial", 0.14, 1.00), ("Delta Trust Bank", "Commercial", 0.12, 0.95),
    ("Crown Merchant Bank", "Commercial", 0.10, 1.00), ("Heritage Union Bank", "Commercial", 0.10, 1.05),
    ("Pinnacle Commercial Bank", "Commercial", 0.08, 1.00), ("Lagoon Savings Bank", "Commercial", 0.07, 1.15),
    ("Harmattan Bank", "Commercial", 0.06, 0.90), ("Eagle Standard Bank", "Commercial", 0.05, 1.00),
    ("Sunrise Microfinance", "Microfinance", 0.04, 1.35), ("Unity Microfinance", "Microfinance", 0.03, 1.30),
    ("Oak Community MFB", "Microfinance", 0.02, 1.40), ("Swift Wallet", "Fintech", 0.09, 0.85),
    ("Metro Pay", "Fintech", 0.06, 0.90), ("Zeal Money", "Fintech", 0.04, 1.00),
]

# code: (description, failure_category, is_platform_fault, is_retryable)
RESPONSE_CODES = {
    "00": ("Approved", "None", 0, 0),
    "RV": ("Approved then reversed", "None", 0, 0),
    "05": ("Do not honour", "Issuer bank", 0, 0),
    "51": ("Insufficient funds", "Customer", 0, 1),
    "55": ("Incorrect PIN", "Customer", 0, 1),
    "68": ("Response received too late (timeout)", "Network", 0, 1),
    "91": ("Issuer or switch inoperative", "Issuer bank", 0, 1),
    "96": ("System malfunction", "Platform", 1, 1),
    "59": ("Suspected fraud", "Fraud", 0, 0),
}
FAIL_CODE_WEIGHTS = {   # per channel, codes: 05, 51, 55, 68, 91, 96, 59
    1: {"05": .15, "51": .30, "55": .18, "68": .09, "91": .15, "96": .10, "59": .03},
    2: {"05": .20, "51": .28, "55": .00, "68": .15, "91": .14, "96": .18, "59": .05},
    3: {"05": .14, "51": .30, "55": .00, "68": .18, "91": .16, "96": .18, "59": .04},
    4: {"05": .06, "51": .20, "55": .00, "68": .38, "91": .20, "96": .14, "59": .02},
    5: {"05": .12, "51": .30, "55": .00, "68": .20, "91": .16, "96": .18, "59": .04},
}

SALES_REPS = [  # id, name, team, region
    ("SR01", "Tunde Adeyemi", "Enterprise", "Lagos & South-West"), ("SR02", "Amina Bello", "Enterprise", "Abuja & North"),
    ("SR03", "Emeka Obi", "Enterprise", "South-East & South-South"), ("SR04", "Ngozi Eze", "Mid-market", "Lagos & South-West"),
    ("SR05", "Ibrahim Musa", "Mid-market", "Abuja & North"), ("SR06", "Funke Alade", "Mid-market", "South-East & South-South"),
    ("SR07", "Chidi Nwosu", "SME & Micro", "Lagos & South-West"), ("SR08", "Hauwa Sani", "SME & Micro", "Abuja & North"),
    ("SR09", "Kelechi Udo", "SME & Micro", "South-East & South-South"), ("SR10", "Bola Ogunleye", "SME & Micro", "Lagos & South-West"),
]
REP_TEAM = {"Enterprise": "Enterprise", "Mid-market": "Mid-market", "SME": "SME & Micro", "Micro": "SME & Micro"}

INDUSTRIES = {  # industry: (weight, name suffixes)
    "Retail": (0.20, ["Supermarket", "Stores", "Mart"]), "Food & Beverage": (0.20, ["Kitchen", "Restaurant", "Bakery"]),
    "Fuel & Energy": (0.07, ["Filling Station", "Energy"]), "Education": (0.08, ["Schools", "Academy"]),
    "Health & Pharmacy": (0.10, ["Pharmacy", "Clinic"]), "Telecom & Utilities": (0.07, ["Telecom Hub", "Utilities"]),
    "Logistics": (0.08, ["Logistics", "Freight"]), "Hospitality": (0.08, ["Hotel", "Suites"]),
    "Fashion": (0.06, ["Fashion House", "Boutique"]), "Electronics": (0.06, ["Electronics", "Gadgets"]),
}
NAME_PREFIXES = ["Sunrise", "Greenfield", "Royal", "Unity", "Delta", "Crown", "Eagle", "Prime", "Oak", "Metro",
                 "Heritage", "Pinnacle", "Savanna", "Harmattan", "Lagoon", "Golden", "Bright", "Anchor", "Summit",
                 "Zenith Point", "Palm", "Coral", "Ivory", "Emerald", "Phoenix", "Horizon", "Victory", "Grace",
                 "Alpha", "Noble", "Liberty", "Cedar", "Baobab", "Rivers", "Harvest", "Pearl", "Titan", "Vista"]
ACQUISITION_CHANNELS = ["Direct sales", "Agent", "Referral", "Partnership"]

# ------------------------------------------------------------ pricing plans
# id: (name, fee_model, fee_pct as fraction, flat_fee, cap, standard_discount_pct)
PLANS = {
    1: ("Micro Flat", "Flat", None, 60.0, 60.0, 0),
    2: ("SME Standard", "Percentage", 0.0150, None, 2000.0, 0),
    3: ("Mid-market Volume", "Tiered", 0.0130, None, 1800.0, 5),
    4: ("Enterprise Standard", "Percentage", 0.0110, None, 1500.0, 10),
    5: ("Enterprise Negotiated", "Percentage", 0.0110, None, 1500.0, 30),   # H3: deeper discount
}
SEGMENT_PLAN = {"Micro": 1, "SME": 2, "Mid-market": 3, "Enterprise": 4}

# ------------------------------------------------------------- cost rates
# per channel: cost type -> (rate as fraction of amount, flat NGN, cap NGN)   [2024 rates]
COSTS = {
    1: {"Processing": (0.00336, 0, 672), "Switching": (0.00096, 0, 144), "Bank charge": (0.00048, 0, 96), "Scheme": (0.00072, 0, 120)},
    2: {"Processing": (0.00408, 0, 840), "Switching": (0.00096, 0, 144), "Bank charge": (0.00084, 0, 144), "Scheme": (0.00072, 0, 120)},
    3: {"Processing": (0.0012, 12, 420), "Switching": (0.00024, 9.6, 120), "Bank charge": (0.0012, 0, 144), "Scheme": (0, 4.8, 5)},
    4: {"Processing": (0.0018, 14.4, 360), "Switching": (0.00024, 9.6, 120), "Bank charge": (0.0018, 0, 180), "Scheme": (0, 14.4, 14)},
    5: {"Processing": (0.00192, 7.2, 300), "Switching": (0.00048, 9.6, 120), "Bank charge": (0.00096, 0, 120), "Scheme": (0.00048, 0, 60)},
}
COST_TYPES = ["Processing", "Switching", "Bank charge", "Scheme"]
# H2: cost inflation. New rates from COST_CHANGE_DATE (multiplier on rate and flat parts)
COST_CHANGE_DATE = date(2025, 1, 1)
COST_INFLATION = {"Processing": 1.08, "Switching": 1.06, "Bank charge": 1.02, "Scheme": 1.01}

# ----------------------------------------------------- volume & seasonality
DOW_FACTOR = [1.00, 1.00, 1.00, 1.02, 1.15, 1.10, 0.78]        # Mon..Sun
MONTH_END_FACTOR = 1.12                                          # days 26 to 1 (salary period)
MONTH_FACTOR = {11: 1.10, 12: 1.25}                              # festive season (H6)
HOLIDAY_FACTOR = 0.90
MERCHANT_GROWTH_MEAN, MERCHANT_GROWTH_SD = 0.07, 0.06           # organic yearly volume growth
AMOUNT_INFLATION = 0.10                                          # yearly rise in ticket size (naira inflation)
AMOUNT_MEDIAN = {1: 9000, 2: 18000, 3: 7000, 4: 3000, 5: 4500}  # NGN, by channel
SEGMENT_AMT_MULT = {"Micro": 0.5, "SME": 0.9, "Mid-market": 1.5, "Enterprise": 2.2}
AMOUNT_SIGMA = 1.0

# H1: channel mix drifts from CHANNEL_SHARE_START (Jan 2024) to CHANNEL_SHARE_END (Dec 2025)
CHANNEL_SHARE_START = {1: 0.50, 2: 0.18, 3: 0.13, 4: 0.08, 5: 0.11}
CHANNEL_SHARE_END = {1: 0.36, 2: 0.17, 3: 0.18, 4: 0.20, 5: 0.09}

# H3: this many Enterprise merchants move to the discounted plan during the window
N_ENTERPRISE_REPRICED = 10
REPRICE_WINDOW = (date(2024, 7, 1), date(2025, 6, 30))

# H4: failures
FAIL_BASE = {1: 0.030, 2: 0.045, 3: 0.040, 4: 0.085, 5: 0.040}
FAIL_PEAK_HOUR_MULT = 1.25            # hours 12-14 and 18-20
FAIL_FESTIVE_MULT = 1.20              # Nov-Dec
FAIL_YEARLY_DRIFT = 0.10              # failure rate creeps up 10% per year
REVERSAL_RATE = 0.008
RETRY_RATE = 0.35                     # share of retryable failures that are retried
RETRY_SUCCESS_RATE = 0.75

# H5 / H6 (kept weak on purpose)
NEW_MARKET_VOLUME_MULT = 0.60
NEW_MARKET_COST_UPLIFT = 0.12         # processing & switching cost uplift in new markets
PEAK_COST_UPLIFT = 0.03               # Nov-Dec processing & switching surcharge
COST_NOISE_SD = 0.03

# ------------------------------------------------------------- merchants
SEGMENT_SPLIT = (0.05, 0.20, 0.55)    # cumulative rank cut-offs: Enterprise, Mid-market, SME, rest Micro
POS_PROB = {"Micro": 0.35, "SME": 0.70, "Mid-market": 0.90, "Enterprise": 1.0}
TERMINALS = {"Micro": (1, 1), "SME": (1, 3), "Mid-market": (3, 8), "Enterprise": (8, 25)}
TERMINAL_TYPES = {"Countertop": 3500, "Mobile": 4500, "Smart POS": 6000}
EXISTING_SHARE = 0.72                 # merchants onboarded before START_DATE (set 0 for all to join in 2024-25)
NEW_ONBOARDING_END = date(2025, 9, 30)  # new merchants join on a random date between START_DATE and this date
CHURN_SHARE, DORMANT_SHARE = 0.10, 0.05

# Nigerian public holidays (Islamic dates are approximate)
HOLIDAYS = {
    date(2024, 1, 1): "New Year's Day", date(2024, 3, 29): "Good Friday", date(2024, 4, 1): "Easter Monday",
    date(2024, 4, 10): "Eid al-Fitr", date(2024, 4, 11): "Eid al-Fitr Holiday", date(2024, 5, 1): "Workers' Day",
    date(2024, 6, 12): "Democracy Day", date(2024, 6, 17): "Eid al-Adha", date(2024, 6, 18): "Eid al-Adha Holiday",
    date(2024, 9, 16): "Eid-el-Maulud", date(2024, 10, 1): "Independence Day", date(2024, 12, 25): "Christmas Day",
    date(2024, 12, 26): "Boxing Day", date(2025, 1, 1): "New Year's Day", date(2025, 3, 31): "Eid al-Fitr",
    date(2025, 4, 1): "Eid al-Fitr Holiday", date(2025, 4, 18): "Good Friday", date(2025, 4, 21): "Easter Monday",
    date(2025, 5, 1): "Workers' Day", date(2025, 6, 6): "Eid al-Adha", date(2025, 6, 9): "Eid al-Adha Holiday",
    date(2025, 6, 12): "Democracy Day", date(2025, 9, 5): "Eid-el-Maulud", date(2025, 10, 1): "Independence Day",
    date(2025, 12, 25): "Christmas Day", date(2025, 12, 26): "Boxing Day", date(2026, 1, 1): "New Year's Day",
}