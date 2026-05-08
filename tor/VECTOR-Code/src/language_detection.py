import subprocess
import json

LANGUAGE_MAPPING = {
    'Python': 'python',
    'C': 'cpp',
    'C++': 'cpp',
    'Java': 'java',
}

def run_cloc(project_path):
    cmd = ['cloc', '--json', project_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"cloc command failed: {e.stderr}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse cloc output as JSON: {e}") from e
    except FileNotFoundError:
        raise RuntimeError("cloc is not installed. Install with: sudo apt install cloc")


def check_language(cloc_data, lang_name, total_lines, threshold):
    if lang_name not in cloc_data:
        return None
    
    lines = cloc_data[lang_name]['code']
    percentage = (lines / total_lines) * 100
    
    if percentage >= threshold:
        return {
            'code': lines,
            'percentage': percentage,
            'codeql': LANGUAGE_MAPPING[lang_name]
        }
    return None


def detect_languages(project_path, threshold=5):
    cloc_data = run_cloc(project_path)

    if 'SUM' not in cloc_data:
        raise RuntimeError("Invalid cloc output: missing 'SUM' key")

    if 'code' not in cloc_data['SUM']:
        raise RuntimeError("Invalid cloc output: missing 'code' in 'SUM'")

    total_lines = cloc_data['SUM']['code']

    if total_lines == 0:
        raise RuntimeError(f"No code lines detected in project: {project_path}")

    languages = {}

    for lang_name in LANGUAGE_MAPPING.keys():
        result = check_language(cloc_data, lang_name, total_lines, threshold)
        if result:
            languages[lang_name] = result

    return languages