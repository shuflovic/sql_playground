import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog
import pyodbc
import json

SNIPPETS_FILE = "snippets.json"

# ------------------- Snippet Functions -------------------
def load_snippets():
    try:
        with open(SNIPPETS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        messagebox.showerror("Error", "Corrupted snippets file. Starting fresh.")
        return []

def save_snippets(snippets):
    with open(SNIPPETS_FILE, "w") as f:
        json.dump(snippets, f, indent=4)

def refresh_snippet_list():
    snippet_listbox.delete(0, tk.END)
    snippets = load_snippets()
    for snippet in snippets:
        snippet_listbox.insert(tk.END, snippet["name"])
    return snippets  # return for use in other functions

def load_selected_snippet(event=None):
    selected_idx = snippet_listbox.curselection()
    if selected_idx:
        snippets = load_snippets()
        sql = snippets[selected_idx[0]]["sql"]
        query_text.delete("1.0", tk.END)
        query_text.insert(tk.END, sql)

def add_snippet():
    name = simpledialog.askstring("Add Snippet", "Enter snippet name:")
    if name:
        sql = simpledialog.askstring("Add Snippet", "Enter SQL code:", parent=root)
        if sql is not None:  # None if canceled
            snippets = load_snippets()
            snippets.append({"name": name, "sql": sql})
            save_snippets(snippets)
            refresh_snippet_list()

def edit_snippet():
    selected_idx = snippet_listbox.curselection()
    if not selected_idx:
        messagebox.showwarning("Warning", "Select a snippet to edit.")
        return
    snippets = load_snippets()
    old = snippets[selected_idx[0]]
    new_name = simpledialog.askstring("Edit Snippet", "New name:", initialvalue=old["name"])
    if new_name:
        new_sql = simpledialog.askstring("Edit Snippet", "New SQL:", initialvalue=old["sql"])
        if new_sql is not None:
            snippets[selected_idx[0]] = {"name": new_name, "sql": new_sql}
            save_snippets(snippets)
            refresh_snippet_list()

def delete_snippet():
    selected_idx = snippet_listbox.curselection()
    if not selected_idx:
        messagebox.showwarning("Warning", "Select a snippet to delete.")
        return
    snippets = load_snippets()
    del snippets[selected_idx[0]]
    save_snippets(snippets)
    refresh_snippet_list()

def save_current_as_snippet():
    current_sql = query_text.get("1.0", tk.END).strip()
    if not current_sql:
        messagebox.showwarning("Warning", "Query input is empty — nothing to save!")
        return

    name = simpledialog.askstring("Save Snippet", "Enter snippet name:", parent=root)
    if not name:
        return  # Canceled

    snippets = load_snippets()

    # Check if name already exists → offer to overwrite
    for i, snippet in enumerate(snippets):
        if snippet["name"] == name:
            if not messagebox.askyesno("Overwrite?", f"A snippet named '{name}' already exists. Overwrite it?"):
                return
            snippets[i]["sql"] = current_sql
            break
    else:
        # New snippet
        snippets.append({"name": name, "sql": current_sql})

    save_snippets(snippets)
    refresh_snippet_list()
    messagebox.showinfo("Success", f"Snippet '{name}' saved!")

# ------------------- Query Execution -------------------
def run_query():
    query = query_text.get("1.0", tk.END).strip()
    if not query:
        messagebox.showwarning("Warning", "Enter a query first!")
        return

    output_text.config(state=tk.NORMAL)
    output_text.delete("1.0", tk.END)

    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=test;"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        cursor.execute(query)

        output_text.insert(tk.END, "Query executed successfully.\n\n")

        result_set_number = 1
        has_results = False

        while True:
            if cursor.description:  # This means there's a result set (from SELECT)
                has_results = True

                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()

                if rows:
                    # Prepare data
                    data = [[str(item) if item is not None else "NULL" for item in row] for row in rows]

                    # Calculate widths
                    col_widths = [len(col) for col in columns]
                    for row in data:
                        for i, val in enumerate(row):
                            col_widths[i] = max(col_widths[i], len(val))

                    # Header for this result set
                    output_text.insert(tk.END, f"--- Result Set {result_set_number} ({len(rows)} rows) ---\n")
                    header = "  ".join(f"{col:<{w}}" for col, w in zip(columns, col_widths))
                    output_text.insert(tk.END, header + "\n")
                    output_text.insert(tk.END, "-" * len(header) + "\n")

                    # Rows
                    for row in data:
                        line = "  ".join(f"{val:<{w}}" for val, w in zip(row, col_widths))
                        output_text.insert(tk.END, line + "\n")

                    output_text.insert(tk.END, "\n")  # Space between tables
                else:
                    output_text.insert(tk.END, f"--- Result Set {result_set_number} (0 rows) ---\n")
                    header = "  ".join(col.ljust(10) for col in columns)  # Minimal spacing
                    output_text.insert(tk.END, header + "\n")
                    output_text.insert(tk.END, "-" * len(header) + "\n\n")

                result_set_number += 1

            # Move to next result set (if any)
            if not cursor.nextset():
                break

        # If no SELECTs at all, show rowcount from the last statement
        if not has_results and cursor.rowcount >= 0:
            output_text.insert(tk.END, f"Rows affected: {cursor.rowcount}\n")

        cursor.close()
        conn.close()

    except pyodbc.Error as e:
        output_text.insert(tk.END, "Error:\n" + str(e) + "\n")
    except Exception as e:
        output_text.insert(tk.END, "Unexpected error:\n" + str(e) + "\n")

def clear_all():
    query_text.delete("1.0", tk.END)
    output_text.config(state=tk.NORMAL)
    output_text.delete("1.0", tk.END)
    output_text.config(state=tk.DISABLED)

# ------------------- GUI Setup -------------------
root = tk.Tk()
root.title("SQL Training App")
root.geometry("1200x700")  # Wider window to fit both sides
root.minsize(1000, 600)

# Main layout: two columns
root.grid_columnconfigure(0, weight=3)  # Left side bigger
root.grid_columnconfigure(1, weight=1)  # Right side smaller
root.grid_rowconfigure(0, weight=1)

# Left Frame - Query & Results
left_frame = tk.Frame(root)
left_frame.grid(row=0, column=0, sticky="nsew", padx=(10,5), pady=10)
left_frame.grid_columnconfigure(0, weight=1)
left_frame.grid_rowconfigure(2, weight=1)  # Results grow

tk.Label(left_frame, text="Enter SQL Query:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0,5))

query_text = scrolledtext.ScrolledText(left_frame, height=10, wrap=tk.WORD)
query_text.grid(row=1, column=0, sticky="nsew", pady=(0,10))
query_text.insert(tk.END, "SELECT TOP 20 * FROM flights")

# Buttons row
btn_frame = tk.Frame(left_frame)
btn_frame.grid(row=2, column=0, sticky="ew", pady=(0,10))
tk.Button(btn_frame, text="Run Query", command=run_query, width=15).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Clear", command=clear_all, width=15).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Save as Snippet", command=save_current_as_snippet, width=18).pack(side=tk.LEFT, padx=5)

tk.Label(left_frame, text="Query Results:", font=("Arial", 12, "bold")).grid(row=3, column=0, sticky="w", pady=(10,5))

output_text = scrolledtext.ScrolledText(left_frame, height=15, wrap=tk.NONE, state=tk.DISABLED)
output_text.grid(row=4, column=0, sticky="nsew")

# Right Frame - Snippets Panel
right_frame = tk.Frame(root, relief="sunken", bd=2)
right_frame.grid(row=0, column=1, sticky="nsew", padx=(5,10), pady=10)

tk.Label(right_frame, text="My Snippets", font=("Arial", 14, "bold")).pack(pady=(0,10))

snippet_listbox = tk.Listbox(right_frame, width=30, height=20)
snippet_listbox.pack(padx=10, pady=(0,10), fill=tk.BOTH, expand=True)
snippet_listbox.bind("<<ListboxSelect>>", load_selected_snippet)  # Single click loads
snippet_listbox.bind("<Double-Button-1>", load_selected_snippet)  # Double click too

# Snippet buttons
snippet_btn_frame = tk.Frame(right_frame)
snippet_btn_frame.pack(pady=5)
tk.Button(snippet_btn_frame, text="Add", command=add_snippet, width=8).pack(side=tk.LEFT, padx=3)
tk.Button(snippet_btn_frame, text="Edit", command=edit_snippet, width=8).pack(side=tk.LEFT, padx=3)
tk.Button(snippet_btn_frame, text="Delete", command=delete_snippet, width=8).pack(side=tk.LEFT, padx=3)

# Load snippets on startup
refresh_snippet_list()

root.mainloop()