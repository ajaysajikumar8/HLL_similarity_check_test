##### test the token sort ratio vs token set ratio

# from fuzzywuzzy import fuzz

# # Define the compositions
# composition1 = "calcitonin salmon 2200iu"
# composition2 = "calcitonin (2200iu)"

# # Compute token set ratio
# similarity_score = fuzz.token_sort_ratio(composition1, composition2)

# print("Similarity Score:", similarity_score)


### testing the parsing composition
import re


def parse_composition(composition):
    regex = r"(\b[\w\s]+\b)\s*(?:\(?(\d+\.?\d*%?)\s*([a-zA-Z\/]+)\)?|(\d+\.?\d*%?)\s*([a-zA-Z\/]+)?)?\s*(tablet|capsule|caplet|syrup|injection|cream|ointment|gel|solution|suspension)?"
    # "(\b[\w\s]+\b)\s*\(?(\d+\.?\d*)?\s*([a-zA-Z]+)?\)?\s*(tablet|capsule|caplet|syrup|injection|cream|ointment|gel|solution|suspension)?"
    matches = re.findall(regex, composition, re.IGNORECASE)

    parsed = []
    for match in matches:
        molecule = match[0].strip()
        amount = match[1] if match[1] else match[3]
        amount = (amount) if amount else None
        unit = match[2] if match[2] else match[4]
        unit = unit.strip() if unit else None
        dosage_form = match[5].strip() if match[5] else None
        parsed.append((molecule, amount, unit, dosage_form))

    return parsed


while True:
    user_input = input("Enter the composition: ")
    parsed_composition = parse_composition(user_input)
    print(f"Original string: {user_input}")
    print(f"Parsed String: {parsed_composition}\n")
