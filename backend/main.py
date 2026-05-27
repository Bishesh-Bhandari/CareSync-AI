from backend.logs import add_log, get_logs

while True:

    symptom = input("Enter symptom (or type exit): ")

    if symptom.lower() == "exit":
        break

    add_log(symptom)

all_logs = get_logs()

print("\nPatient Logs:")

for log in all_logs:
    print("-", log)