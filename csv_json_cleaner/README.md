# CSV-to-JSON Data Cleaner

## About the Project
This is a simple Python project that reads data from a CSV file, cleans it, removes duplicate records, and saves the cleaned data as a JSON file.

## Features
- Reads data from a CSV file.
- Removes extra spaces from text.
- Converts emails to lowercase.
- Converts valid ages into integers.
- Handles missing or invalid ages.
- Removes duplicate records.
- Saves cleaned data in JSON format.

## Technologies Used
- Python
- CSV module
- JSON module
- pathlib module

## Project Structure
```text
csv_json_cleaner/
├── main.py
├── people.csv
├── cleaned.json
└── README.md
```

## How to Run

1. Install Python 3.
2. Place `people.csv` in the project folder.
3. Open a terminal in the project folder.
4. Run the following command:

```bash
python main.py
```

## Output
The program creates a `cleaned.json` file containing the cleaned records and displays the number of records kept and skipped.

## Duplicate Rule
Records with the same name and email are treated as duplicates, ignoring uppercase and lowercase differences.

## Handling Missing Data
- Records without a name are skipped.
- Missing or invalid ages are stored as `null`.
- Missing emails are stored as `null`.
- Duplicate records are skipped.

## Learning Objectives
This project demonstrates Python functions, collections, exception handling, file handling, CSV processing, JSON conversion, and modular programming basics.

## Future Improvements
- Validate email formats.
- Generate a report of invalid records.
- Allow users to specify input and output file paths.

