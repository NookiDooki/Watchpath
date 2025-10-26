from pathlib import Path
from datetime import datetime

from ai import analyze_logs_ollama_chunk, chunk_log_file
from log_analysis import (
    aggregate_metrics,
    build_chart_context,
    build_summary_context,
    generate_charts,
    parse_apache_logs,
)
from report_builder import parse_json_payload, render_markdown_from_json

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

# --- Parse logs and generate analytics ---
log_path = Path(log_file)
entries = parse_apache_logs(log_path)
aggregates = aggregate_metrics(entries)

chart_dir = report_file.parent / f"{report_file.stem}_charts"
chart_metadata = generate_charts(aggregates, chart_dir)

summary_context = build_summary_context(aggregates)
chart_context = build_chart_context(chart_metadata)

report_lines = [
    "# Watchpath Apache Access Log Analysis",
    f"**Log File:** `{log_file}`",
    f"**Generated:** {datetime.now().isoformat(timespec='seconds')}",
    "",
    "## Dataset Snapshot",
]
for line in summary_context.splitlines():
    report_lines.append(f"- {line}")

report_lines.append("")
report_lines.append("## Chart Inventory")
chart_rel_dir = Path(chart_dir.name)
if chart_metadata:
    for chart in chart_metadata:
        chart_path = (chart_rel_dir / chart.filename).as_posix()
        report_lines.append(f"![{chart.description}]({chart_path})")
        report_lines.append(f"<small>{chart.description}</small>")
        report_lines.append("")
else:
    report_lines.append("No charts were generated.")
    report_lines.append("")

# --- Process log in chunks ---
report_content = []
chunks = list(chunk_log_file(log_file, chunk_size=50))
total_chunks = len(chunks)

if total_chunks == 0:
    print("No log data found to analyze.")

for index, chunk in enumerate(chunks, start=1):
    print(f"Processing chunk {index}/{total_chunks}...")
    section_title = f"Chunk {index} Analysis"
    try:
        analysis_raw = analyze_logs_ollama_chunk(
            chunk,
            prompt_file,
            chart_context=chart_context,
            summary_context=summary_context,
        )
        payload = parse_json_payload(analysis_raw)
        section_markdown = render_markdown_from_json(
            payload,
            chart_rel_dir=chart_rel_dir,
            section_title=section_title,
        )
        report_content.append(section_markdown)
        print(f"Completed chunk {index}/{total_chunks}.")
    except Exception as e:
        error_block = (
            f"## {section_title}\n[ERROR] Failed to process chunk: {e}"
        )
        report_content.append(error_block)
        print(f"Chunk {index}/{total_chunks} failed: {e}")

# --- Save report ---
full_report = "\n".join(report_lines + report_content)
report_file.write_text(full_report)
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
