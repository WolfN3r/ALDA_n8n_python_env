import sys
import json

def main():
    data = json.load(sys.stdin)
    items = data if isinstance(data, list) else [data]

    output = []
    for item in items:
        new_item = {}
        for key, value in item.items():
            # Zpracujeme pouze čísla, ale vyloučíme bool
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                new_item[f"{key}_2"] = value ** 2
        output.append(new_item)

    print(json.dumps(output))

if __name__ == "__main__":
    main()
