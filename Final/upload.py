import pandas as pd
from sqlalchemy import create_engine

# 1. Load the data
csv_path = r"C:\Users\charc\.vscode\Python\PANDAS BASIS\Final\data\shopping_trends.csv"
df = pd.read_csv(csv_path)

# 2. Clean up column names so MySQL doesn't break on spaces/parentheses
df.columns = df.columns.str.replace(' ', '_').str.replace('(', '').str.replace(')', '')

# 3. Connection Setup (Paste your actual Railway root password inside the quotes)
RAILWAY_PASSWORD = "AgCcmzSFAvWAJhdqZaMTSDhNYylBWhwU" 

connection_string = f"mysql+pymysql://root:{RAILWAY_PASSWORD}@centerbeam.proxy.rlwy.net:32321/railway"

print("Uploading rows to Railway cloud...")
engine = create_engine(connection_string)

# 4. Push data to a new table named 'shopping_trends'
df.to_sql(name="shopping_trends", con=engine, if_exists="replace", index=False)
print("Success! Your data is fully loaded into your Railway MySQL instance.")