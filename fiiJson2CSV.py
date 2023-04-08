import json
import csv

# Open the JSON file for reading
with open('b3FIIs.json', 'r') as file:
    # Load the contents of the file into a list of dictionaries
    data = json.load(file)

# Open the CSV file for writing
with open('b3FIIs.csv', 'w', newline='') as csvfile:
    # Create a CSV writer object
    writer = csv.writer(csvfile)

    # Write the header row with the attribute names
    writer.writerow(data[0].keys())

    # Write the data rows
    for obj in data:
        writer.writerow(obj.values())
