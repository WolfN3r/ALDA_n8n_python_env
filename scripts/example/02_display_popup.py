import sys
import json
import tkinter as tk
from tkinter import ttk


def main():
    # Načteme JSON ze stdin (seznam nebo dict)
    data = json.load(sys.stdin)
    items = data if isinstance(data, list) else [data]

    # Sloučíme všechny klíče do jedné dict (mergnuté)
    merged = {}
    for item in items:
        merged.update(item)

    # Roztřídíme podle typu
    numbers = {}
    strings = {}
    bools = {}
    for key, value in merged.items():
        if isinstance(value, bool):
            bools[key] = value
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            numbers[key] = value
        elif isinstance(value, str):
            strings[key] = value

    # Vytvoření okna
    root = tk.Tk()
    root.title("Data Overview")

    container = ttk.Frame(root, padding=10)
    container.pack(fill="both", expand=True)

    def add_section(title, data_dict):
        if not data_dict:
            return
        # Sekce nadpis
        lbl = ttk.Label(container, text=title, font=(None, 14, 'bold'))
        lbl.pack(anchor='w', pady=(10, 0))
        # Tabulka se jménem a hodnotou
        tree = ttk.Treeview(container, columns=("key","value"), show='headings', height=len(data_dict))
        tree.heading("key", text="Key")
        tree.heading("value", text="Value")
        tree.column("key", anchor='w')
        tree.column("value", anchor='center')
        tree.pack(fill='x', pady=(0, 5))
        for k, v in data_dict.items():
            tree.insert('', 'end', values=(k, v))

    # Přidáme sekce pro každý typ
    add_section("Number", numbers)
    add_section("String", strings)
    add_section("Bool", bools)

    root.mainloop()

if __name__ == '__main__':
    main()