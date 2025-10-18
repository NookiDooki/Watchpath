from pathlib import Path
from ai import analyze_logs_ollama_chunk, chunk_log_file

# --- Paths ---
log_file = "logs/apache_access_20250302.log"
prompt_file = "prompts/anomaly_prompt.txt"
report_file = Path("reports/apache_access_analysis.md")

# --- Ensure reports folder exists ---
report_file.parent.mkdir(exist_ok=True)

# --- Process log in chunks ---
report_content = []

for chunk in chunk_log_file(log_file, chunk_size=50):
    try:
        analysis = analyze_logs_ollama_chunk(chunk, prompt_file)
        report_content.append(analysis)
    except Exception as e:
        report_content.append(f"[ERROR] Failed to process chunk: {e}")

# --- Save report ---
report_file.write_text("\n".join(report_content))
print(f"Analysis saved to {report_file}")


# from ai import analyze_logs_ollama
#
# log_file = "../logs/apache_access_20250302.log"
# prompt_file = "../prompts/anomaly_prompt.txt"
#
# try:
#     analysis = analyze_logs_ollama(log_file, prompt_file)
#     print("=== AI Log Analysis ===\n")
#     print(analysis)
# except Exception as e:
#     print("Error:", e)
#
