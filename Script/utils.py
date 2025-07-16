import json
from configparser import ConfigParser

def load_settings():
    with open("config/settings.json") as f:
        return json.load(f)

def save_to_csv(data, filename):
    import pandas as pd
    pd.DataFrame(data).to_csv(f"data/{filename}", index=False)