from flask import Flask, render_template, request, redirect, url_for, send_file
import pandas as pd
import io
import re
from collections import defaultdict, OrderedDict

app = Flask(__name__)

# regex to parse header like:
# "Assessment - 1.1.6 Network Topologies"
# "Lab - B.2.7 Lab: Create Network Topologies"
HEADER_RE = re.compile(r'^\s*(?P<type>\w+)\s*-\s*(?P<code>[\w\.]+)\s*(?P<rest>.*)$', re.IGNORECASE)

def parse_columns(df):
    """
    Parse dataframe columns to determine:
      - column index -> (type, module)
    type will be lower-cased 'assessment' or 'lab' (or the raw type if others)
    module is the token before the first dot in the code (string).
    """
    col_map = {}  # column name -> (type, module)
    modules_set = []  # keep insertion order
    for col in df.columns:
        if col.strip().lower().startswith('student'):
            col_map[col] = ('student', None)
            continue
        m = HEADER_RE.match(col)
        if m:
            typ = m.group('type').strip().lower()  # e.g., 'assessment' or 'lab'
            code = m.group('code').strip()         # e.g., '1.1.6' or 'B.2.7'
            # module is the first token before '.'
            module_token = code.split('.')[0]
            # canonicalize module as string (keep letters intact)
            module = str(module_token)
            col_map[col] = (typ, module)
            if module not in modules_set:
                modules_set.append(module)
        else:
            # If no match, mark as unknown (we will ignore when grouping)
            col_map[col] = (None, None)
    return col_map, modules_set

def pct_to_float(val):
    """Convert a percent string like '91%' or 91 to float 91.0. Return NaN for blanks."""
    if pd.isna(val):
        return float('nan')
    if isinstance(val, str):
        s = val.strip().replace('%','')
        if s == '':
            return float('nan')
        try:
            return float(s)
        except ValueError:
            # If there are stray characters, attempt to pull numbers
            nums = re.findall(r'[-+]?\d*\.?\d+', s)
            if nums:
                return float(nums[0])
            return float('nan')
    try:
        return float(val)
    except Exception:
        return float('nan')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('csvfile')
        if not file:
            return redirect(request.url)
        # Read CSV into pandas DataFrame
        stream = io.StringIO(file.stream.read().decode('utf-8', errors='ignore'))
        df = pd.read_csv(stream, dtype=str)  # read everything as string first
        
        # Ensure columns trimmed
        df.columns = [c.strip() for c in df.columns]
        # Identify student column (first col that starts with 'Student' or assume first column)
        student_col = None
        for col in df.columns:
            if col.lower().startswith('student'):
                student_col = col
                break
        if student_col is None:
            # fallback to first column
            student_col = df.columns[0]
        
        # Parse header columns
        col_map, modules_order = parse_columns(df)
        
        # Convert all grade columns to floats (percent numbers)
        # We'll create a new dataframe copy with numeric conversions
        numeric_df = df.copy()
        for col in numeric_df.columns:
            if col == student_col:
                continue
            numeric_df[col] = numeric_df[col].apply(pct_to_float)
        
        # Build result table: student name + for each module: assignments avg, labs avg
        # Want modules in a stable order
        # Build mapping: module -> list of assignment columns, list of lab columns
        module_cols = OrderedDict()
        for module in modules_order:
            module_cols[module] = {'assessment': [], 'lab': []}
        # iterate columns to fill module lists
        for col, (typ, module) in col_map.items():
            if module is None or typ is None:
                continue
            if module not in module_cols:
                # include new module discovered beyond initial order
                module_cols[module] = {'assessment': [], 'lab': []}
            t = typ.lower()
            if 'assess' in t or t.startswith('assessment'):
                module_cols[module]['assessment'].append(col)
            elif 'lab' in t or t.startswith('lab'):
                module_cols[module]['lab'].append(col)
            else:
                # treat other types as 'assessment' by default
                module_cols[module]['assessment'].append(col)
        
        # Build output rows
        output_rows = []
        for idx, row in numeric_df.iterrows():
            student = row[student_col]
            out_row = {'Student': student}
            for module, lists in module_cols.items():
                # assignments average
                a_cols = lists['assessment']
                l_cols = lists['lab']
                if len(a_cols) > 0:
                    a_vals = row[a_cols].values.astype(float)
                    # Use pandas to compute mean ignoring NaN
                    a_mean = pd.to_numeric(pd.Series(a_vals)).dropna().mean()
                else:
                    a_mean = float('nan')
                if len(l_cols) > 0:
                    l_vals = row[l_cols].values.astype(float)
                    l_mean = pd.to_numeric(pd.Series(l_vals)).dropna().mean()
                else:
                    l_mean = float('nan')
                # format with percent sign if not NaN, else blank
                out_row[f'Module {module} Assignments'] = f"{a_mean:.2f}%" if pd.notna(a_mean) else ''
                out_row[f'Module {module} Labs'] = f"{l_mean:.2f}%" if pd.notna(l_mean) else ''
            output_rows.append(out_row)
        
        # Build columns in the desired order:
        # 1. All Assignment columns (in module order)
        # 2. All Lab columns (in module order)

        table_columns = ['Student']

        # First: all assignments
        for module in module_cols.keys():
            table_columns.append(f'Module {module} Assignments')

        # Second: all labs
        for module in module_cols.keys():
            table_columns.append(f'Module {module} Labs')

        
        # Convert to DataFrame for nicer display
        out_df = pd.DataFrame(output_rows, columns=table_columns)
        
        # Render HTML table
        return render_template('results.html', tables=out_df.to_html(classes='table table-striped table-sm', index=False, justify='center', border=0, escape=False).strip(), titles=table_columns)
    return render_template('index.html')
    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)
