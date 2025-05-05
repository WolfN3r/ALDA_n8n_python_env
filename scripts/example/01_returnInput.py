import sys
import json

def main():
    # Načti JSON ze stdin a vrať beze změny
    data = json.load(sys.stdin)
    print(json.dumps(data))

if __name__ == '__main__':
    main()