import sys
import json

def main():
    # Načteme JSON ze stdin (může to být list nebo dict)
    data = json.load(sys.stdin)
    items = data if isinstance(data, list) else [data]

    output = []
    for item in items:
        new_item = {}
        for key, value in item.items():
            # Invertuj pouze boolean hodnoty, ignore int/float/str
            if isinstance(value, bool):
                new_item[key] = not value
        output.append(new_item)

    # Vypíšeme výsledný seznam jako JSON
    print(json.dumps(output))

if __name__ == '__main__':
    main()
