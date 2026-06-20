import pandas as pd
import glob
import os

def find_gujarat():
    files = glob.glob('../data/rbi/**/*.xls', recursive=True)
    print(f"Searching {len(files)} files...")
    for f in files:
        try:
            # We don't need to load the whole file if we just want to check text
            # but for XLS, we kind of do. We can use xlrd directly if needed.
            df = pd.read_excel(f, header=None)
            # Search all cells for 'Gujarat'
            mask = df.apply(lambda r: r.astype(str).str.contains('Gujarat', case=False).any(), axis=1)
            if mask.any():
                print(f"Found Gujarat in: {f}")
                # Print the row for context
                # print(df[mask].iloc[0, 0:5].values)
        except Exception as e:
            # print(f"Error reading {f}: {e}")
            pass

if __name__ == "__main__":
    find_gujarat()
