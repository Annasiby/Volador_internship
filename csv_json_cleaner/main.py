"""
CSV-to-JSON Data Cleaner

"""

import csv
import json
from pathlib import Path


def clean_text(value):
    """Remove spaces around text, turn empty text into None"""
    if value is None:
        return None

    value = value.strip()
    return value if value else None


def clean_age(value):
    """Convert an age to an integer or None if it is invalid."""
    value = clean_text(value)

    if value is None:
        return None

    try:
        age = int(value)
    except ValueError:
        return None

    # An age should not be negative.
    if age < 0:
        return None

    return age


def clean_email(value):
    """Trim an email and make it lowercase; blank values become None."""
    value = clean_text(value)

    if value is None:
        return None

    return value.lower()


def clean_csv_to_json(input_file, output_file):
    """
    Read a CSV file, clean its rows, remove duplicates, and write JSON.
    
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV file was not found: {input_path}")

    cleaned_people = []
    seen = set()
    skipped_rows = 0

    with input_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)

        required_columns = {"name", "age", "email"}
        actual_columns = set(reader.fieldnames or [])

        if not required_columns.issubset(actual_columns):
            missing = required_columns - actual_columns
            raise ValueError(
                "CSV is missing required column(s): " + ", ".join(sorted(missing))
            )

        for row in reader:
            name = clean_text(row.get("name"))
            age = clean_age(row.get("age"))
            email = clean_email(row.get("email"))

            
            if name is None:
                skipped_rows += 1
                continue

            person = {
                "name": name,
                "age": age,
                "email": email,
            }

            # matching name + email as a duplicate
            duplicate_key = (
                person["name"].casefold(),
                person["email"].casefold() if person["email"] else None,
            )

            if duplicate_key in seen:
                skipped_rows += 1
                continue

            seen.add(duplicate_key)
            cleaned_people.append(person)

    # Create the output folder if it does not already exist.
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as json_file:
        json.dump(cleaned_people, json_file, indent=2, ensure_ascii=False)
        json_file.write("\n")

    return len(cleaned_people), skipped_rows


def main():
    """ starting point"""
    input_file = Path("people.csv")
    output_file = Path("cleaned.json")

    try:
        kept, skipped = clean_csv_to_json(input_file, output_file)
    except (FileNotFoundError, ValueError, csv.Error) as error:
        print(f"Could not clean the CSV: {error}")
        return

    print("Cleaning complete!")
    print(f"Clean records: {kept}")
    print(f"Skipped rows (missing name or duplicate): {skipped}")
    print(f"JSON saved to: {output_file.resolve()}")


if __name__ == "__main__":
    main()
