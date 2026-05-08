import subprocess
import os

def create_database(project_path, codeql_lang, database_dir, db_name):

    db_path = os.path.join(database_dir, db_name)

    if os.path.exists(db_path):
        try:
            subprocess.run(['rm', '-rf', db_path], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to remove existing database at {db_path}: {e.stderr}") from e
    
    cmd = [
        'codeql', 'database', 'create',
        db_path,
        '--language=' + codeql_lang,
        '--source-root=' + project_path,
        '--build-mode=none'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        return db_path
    else:
        print(f"  Error creating db-{codeql_lang}: {result.stderr}")
        return None


def create_databases(project_path, languages, database_dir):
    databases = {}

    codeql_languages = {}
    for lang_name, data in languages.items():
        codeql_lang = data['codeql']
        if codeql_lang not in codeql_languages:
            codeql_languages[codeql_lang] = lang_name

    for codeql_lang, lang_name in codeql_languages.items():
        db_name = f"db-{codeql_lang}"
        db_path = create_database(project_path, codeql_lang, database_dir, db_name)
        
        if db_path:
            databases[codeql_lang] = db_path
    
    return databases