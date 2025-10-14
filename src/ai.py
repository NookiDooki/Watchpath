def analyze_logs_ollama(logs_path: str, prompt_path: str, model="mistral:7b-instruct"):
    """
    Uses a local Ollama model to analyze logs and detect anomalies.
    """
    # Define prompt and log location
    base_prompt = Path(prompt_path).read_text()
    logs = Path(logs_path).read_text()

    # Combine static instructions + dynamic logs
    full_prompt = f"{base_prompt}\n\n### TASK ###\nAnalyze the following logs:\n{logs}\n"
    
    result = subprocess.run(
        ["ollama", "run", model],
        input=full_prompt.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    return result.stdout.decode().strip()

