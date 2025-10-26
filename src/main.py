from pathlib import Path
from datetime import datetime
from ai import analyze_logs_ollama_chunk, chunk_log_file

# --- Paths ---
log_file = "logs/apache_access_20250302.log"
prompt_file = "prompts/IlyesTestPrompt.txt"

# --- Generate dynamic report name ---
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_name = Path(log_file).stem  # e.g., 'apache_access_20250302'
report_name = f"{log_name}_analysis_{timestamp}.md"
report_file = Path("reports") / report_name

# --- Ensure reports folder exists ---
report_file.parent.mkdir(exist_ok=True)

# --- Process log in chunks ---
report_content = []

chunks = list(chunk_log_file(log_file, chunk_size=50))
total_chunks = len(chunks)

if total_chunks == 0:
    print("No log data found to analyze.")

for index, chunk in enumerate(chunks, start=1):
    print(f"Processing chunk {index}/{total_chunks}...")
    try:
        analysis = analyze_logs_ollama_chunk(chunk, prompt_file)
        report_content.append(analysis)
        print(f"Completed chunk {index}/{total_chunks}.")
    except Exception as e:
        report_content.append(f"[ERROR] Failed to process chunk: {e}")
        print(f"Chunk {index}/{total_chunks} failed: {e}")

# --- Save report ---
report_file.write_text("\n".join(report_content))
print(f"Analysis saved to {report_file}")











# from pathlib import Path
# from ai import analyze_logs_ollama_chunk, chunk_log_file
#
# # --- Paths ---
# log_file = "logs/apache_access_20250302.log"
# prompt_file = "prompts/anomaly_prompt.txt"
# report_file = Path("reports/apache_access_analysis.md")
#
# # --- Ensure reports folder exists ---
# report_file.parent.mkdir(exist_ok=True)
#
# # --- Process log in chunks ---
# report_content = []
#
# for chunk in chunk_log_file(log_file, chunk_size=50):
#     try:
#         analysis = analyze_logs_ollama_chunk(chunk, prompt_file)
#         report_content.append(analysis)
#     except Exception as e:
#         report_content.append(f"[ERROR] Failed to process chunk: {e}")
#
# # --- Save report ---
# report_file.write_text("\n".join(report_content))
# print(f"Analysis saved to {report_file}")







# NOOOOOOOOOO
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
