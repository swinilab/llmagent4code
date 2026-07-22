import os
import argparse
import ast
import pandas as pd
from datetime import datetime

class ASTFeatureExtractor(ast.NodeVisitor):
    def __init__(self):
        self.imports = set()
        self.calls = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name.split('.')[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module.split('.')[0])
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.add(node.func.attr)
        self.generic_visit(node)

def extract_features_from_code(code: str):
    try:
        tree = ast.parse(code)
    except Exception as e:
        # If parsing fails, return empty sets
        return set(), set()
    
    extractor = ASTFeatureExtractor()
    extractor.visit(tree)
    return extractor.imports, extractor.calls

def main():
    parser = argparse.ArgumentParser(description="Verify QA test tactics in generated code.")
    parser.add_argument("model", help="Name of the model folder (e.g. claude)")
    args = parser.parse_args()
    
    model_name = args.model
    # Assumes the script is inside the qa-test folder
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(project_root, "AIModelsEvaluation", model_name)
    tactics_file = os.path.join(project_root, "qa-test", "tactics.xlsx")
    
    if not os.path.exists(target_dir):
        print(f"Error: Target directory {target_dir} does not exist.")
        return
        
    if not os.path.exists(tactics_file):
        print(f"Error: Tactics file {tactics_file} does not exist.")
        return

    # Load tactics
    df = pd.read_excel(tactics_file)
    
    tactics = []
    for _, row in df.iterrows():
        code_sample = str(row.get('code_sample', ''))
        imports, calls = extract_features_from_code(code_sample)
        tactics.append({
            'nfr_id': row.get('nfr_id'),
            'nfr_name': row.get('nfr_name'),
            'architectural_mechanism': row.get('architectural_mechanism'),
            'module_component': row.get('module_component'),
            'library': row.get('library'),
            'expected_imports': imports,
            'expected_calls': calls
        })

    # Find .py files
    py_files = []
    for root, _, files in os.walk(target_dir):
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))
                
    results = []
    for py_file in py_files:
        with open(py_file, "r", encoding="utf-8") as f:
            code = f.read()
            
        gen_imports, gen_calls = extract_features_from_code(code)
        
        for tactic in tactics:
            # We ignore tactics that failed to parse (empty expected imports/calls)
            # or perhaps they don't have code samples.
            if not tactic['expected_imports'] and not tactic['expected_calls']:
                continue
                
            # Check if generated code has superset of expected imports and calls
            has_imports = tactic['expected_imports'].issubset(gen_imports)
            has_calls = tactic['expected_calls'].issubset(gen_calls)
            
            match_status = "Pass" if has_imports and has_calls else "Fail"
            
            results.append({
                'model': model_name,
                'file_path': os.path.relpath(py_file, project_root),
                'nfr_id': tactic['nfr_id'],
                'nfr_name': tactic['nfr_name'],
                'library': tactic['library'],
                'tactic': tactic['architectural_mechanism'],
                'match_status': match_status,
                'has_imports': has_imports,
                'has_calls': has_calls
            })
            
    if not results:
        print(f"No .py files found in {target_dir} or no tactics evaluated.")
        df_results = pd.DataFrame(columns=[
            'model', 'file_path', 'nfr_id', 'nfr_name', 'library', 'tactic', 'match_status', 'has_imports', 'has_calls'
        ])
    else:
        df_results = pd.DataFrame(results)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = os.path.join(project_root, "qa-test", f"evaluation_report_{model_name}_{timestamp}.csv")
    
    df_results.to_csv(out_csv, index=False)
    print(f"Report successfully saved to {out_csv}")

if __name__ == "__main__":
    main()
