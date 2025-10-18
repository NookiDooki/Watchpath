from ai import analyze_logs_ollama

log_file = "../logs/apache_access_20250302.log"
prompt_file = "../prompts/anomaly_prompt.txt"

try:
    analysis = analyze_logs_ollama(log_file, prompt_file)
    print("=== AI Log Analysis ===\n")
    print(analysis)
except Exception as e:
    print("Error:", e)

