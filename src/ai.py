from pathlib import Path
import subprocess

def analyze_logs_ollama_chunk(log_chunk: str, prompt_path: str, model="mistral:7b-instruct"):
    """
    Analyze a chunk of logs directly using a local Ollama model.
    Returns the AI output (line-by-line classification).
    """
    base_prompt = Path(prompt_path).read_text()
    full_prompt = f"{base_prompt}\n\n### TASK ###\nAnalyze the following logs:\n{log_chunk}\n"

    result = subprocess.run(
        ["ollama", "run", model],
        input=full_prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        raise RuntimeError(f"Ollama failed: {result.stderr.decode()}")

    return result.stdout.decode().strip()


def chunk_log_file(log_path: str, chunk_size=50):
    """
    Yield chunks of log lines as strings from a log file.
    """
    lines = Path(log_path).read_text().splitlines()
    for i in range(0, len(lines), chunk_size):
        yield "\n".join(lines[i:i+chunk_size])


# from pathlib import Path
# import subprocess
#
# def analyze_logs_ollama(logs_path: str, prompt_path: str, model="mistral:7b-instruct"):
#     """
#     Uses a local Ollama model to analyze logs and detect anomalies.
#     """
#     # Convert strings to Path objects
#     prompt_path = Path(prompt_path)
#     logs_path = Path(logs_path)
#
#     # Read paths that were passed ase function input
#     base_prompt = prompt_path.read_text()
#     logs = logs_path.read_text()
#
#     # Combine static instructions + dynamic logs
#     full_prompt = f"{base_prompt}\n\n### TASK ###\nAnalyze the following logs:\n{logs}\n"
#
#     # Call the Ollama model locally
#     result = subprocess.run(
#         ["ollama", "run", model],
#         input=full_prompt.encode("utf-8"),
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE
#     )
#
#     if result.returncode != 0:
#         raise RuntimeError(f"Ollama failed: {result.stderr.decode()}")
#
#     return result.stdout.decode().strip()
#
