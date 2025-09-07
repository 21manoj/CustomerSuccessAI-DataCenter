import pandas as pd

def analyze_excel(file_path):
    # Load the Excel file
    xls = pd.ExcelFile(file_path)
    print(f"Found sheets: {xls.sheet_names}\n")

    for sheet in xls.sheet_names:
        print(f"--- Sheet: {sheet} ---")
        df = pd.read_excel(xls, sheet)
        print("Columns:", list(df.columns))
        print("First 5 rows:")
        print(df.head())
        print("\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python3 analyze_excel.py <your_excel_file.xlsx>")
    else:
        analyze_excel(sys.argv[1])
