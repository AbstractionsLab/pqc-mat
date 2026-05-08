import subprocess
import os



def generate_cbom_from_sarif(sarif_path, output_path, app_name):
    if not os.path.isfile(sarif_path):
        raise RuntimeError(f"SARIF file not found: {sarif_path}")

    cmd = [
        'cryptobom',
        'generate',
        sarif_path,
        '--application-name', app_name,
        '--output-file', output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Error generating CBOM from {os.path.basename(sarif_path)}:")
        print(f"    Command: {' '.join(cmd)}")
        print(f"    Error: {e.stderr}")
        return False


def generate_cbom(sarif_files, output_dir, app_name):
    cbom_files = []
    
    if not sarif_files:
        return cbom_files
    
    for sarif_path in sarif_files:
        sarif_name = os.path.basename(sarif_path).replace('.sarif', '')
        cbom_path = os.path.join(output_dir, f"{sarif_name}-cbom.json")
        
        if generate_cbom_from_sarif(sarif_path, cbom_path, app_name):
            cbom_files.append(cbom_path)
    
    return cbom_files