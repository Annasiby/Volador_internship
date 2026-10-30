# Python API Client and Data Parser

## Overview
A simple Python project that fetches data from a REST API, validates JSON responses, and converts valid records into a pandas DataFrame.

## Technologies Used
- Python
- Requests – HTTP API requests
- Pandas – Data processing
- Unittest – Automated testing

## Project Structure
```text
api_data_project/
├── api_client.py
├── data_parser.py
├── main.py
├── test_project.py
└── requirements.txt
```

## How to Run

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the project:
```bash
python main.py
```

3. Run unit tests:
```bash
python -m unittest -v
```

## Features
- Fetches posts from a REST API.
- Parses JSON responses.
- Validates required fields and data types.
- Converts valid records into a pandas DataFrame.
- Tests API responses and data validation.




