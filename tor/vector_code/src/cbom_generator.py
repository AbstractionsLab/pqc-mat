import subprocess
import os
from .cbom_normaliser import normalise_file


def generate_cbom(sarif_dir: str, output_dir: str, app_name: str) -> str | None:
    """Generate a CBOM from SARIF files in sarif_dir using the cryptobom CLI.

    Runs the cryptobom tool against all .sarif files in the given directory,
    writes the output to output_dir, and normalizes the result in place.
    Note: Files with extension different to '.sarif' or '.json' (expected to be 
    a valid sarif format) are excluded

    Args:
        sarif_dir: Directory containing one or more .sarif input files.
        output_dir: Directory where the generated CBOM file will be written.
        app_name: Application name passed to the cryptobom --application-name flag.

    Returns:
        The absolute path to the generated CBOM JSON file, or None if the
        cryptobom command fails.
    """
    dir_files = os.listdir(sarif_dir)
    if len(dir_files) == 1:
        sarif_file = dir_files[0]
        if sarif_file.endswith('.sarif'):
            cbom_name = sarif_file.replace('.sarif', '-cbom.json')
        # SARIF files in JSON format are accepted too
        elif sarif_file.endswith('.json'):
            cbom_name = sarif_file.replace('.json', '-cbom.json')
        else:
            print("No SARIF files to process")
            return None
    else:
        cbom_name = 'crypto-combined-cbom.json'
    output_path = os.path.join(output_dir, cbom_name)

    cmd = [
        'cryptobom',
        'generate',
        sarif_dir,
        '--application-name', app_name,
        '--output-file', output_path
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"  Error generating CBOM from {sarif_dir}:")
        print(f"    Command: {' '.join(cmd)}")
        print(f"    Error: {e.stderr}")
        return None

    if not os.path.exists(output_path):
        print(f"  Error generating CBOM from '{sarif_dir}'.",
              "Ensure that the folder contains '.sarif' files and",
               "that all '.json' files are valid SARIF files.")
        return None

    try:
        normalise_file(output_path)
    except Exception as e:
        print(f"  Warning: CBOM normalization failed: {e}")
        return None

    return output_path
