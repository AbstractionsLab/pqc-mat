import subprocess
import os

QUERIES_PATHS = {
    'python': '/home/vector/tools/codeql-queries/python/ql/src/experimental/cryptography/inventory',
    'cpp': '/home/vector/tools/codeql-queries/cpp/ql/src/experimental/cryptography/inventory',
}


def run_query_sarif(database_path, query_path, output_path, codeql_lang):
    cmd = [
        'codeql', 'database', 'analyze',
        database_path,
        '--format=sarif-latest',
        '--output=' + output_path,
        '--sarif-add-snippets',
        '--sarif-category=' + codeql_lang,
        query_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Error running CodeQL query for {codeql_lang}:")
        print(f"    Command: {' '.join(cmd)}")
        print(f"    Error: {e.stderr}")
        return False
    except FileNotFoundError:
        raise RuntimeError(
            "CodeQL CLI not found. Please install it:\n"
            "https://docs.github.com/en/code-security/codeql-cli/getting-started-with-the-codeql-cli/setting-up-the-codeql-cli\n"
            "Make sure 'codeql' is in your PATH"
        )


def run_queries(databases, output_dir):
    sarif_files = []
    
    if not databases:
        return sarif_files
    
    for codeql_lang, db_path in databases.items():
        if codeql_lang not in QUERIES_PATHS:
            print(f"  Queries not found for {codeql_lang}")
            continue
        
        query_path = QUERIES_PATHS[codeql_lang]
        
        if not os.path.exists(query_path):
            print(f"  Queries path does not exist: {query_path}")
            continue
        
        sarif_path = os.path.join(output_dir, f"crypto-{codeql_lang}.sarif")
        
        if run_query_sarif(db_path, query_path, sarif_path, codeql_lang):
            sarif_files.append(sarif_path)
    
    return sarif_files