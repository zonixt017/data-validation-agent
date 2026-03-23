"""
report_generator.py — HTML report generator for the Data Validation Agent.

Loads the Jinja2 report template, enriches the summary data with grouped
views, and renders the final HTML report to the output directory.
"""

import os
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader, select_autoescape
import sys

# Ensure logger is importable from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import logger as log_module


def generate_report(summary: dict, output_path: str) -> None:
    """
    Render the Jinja2 HTML report and write it to the output path.

    Enriches the summary dict with:
    - findings grouped by severity (for template access)
    - findings grouped by entity_id (for per-record breakdown section)

    Args:
        summary: Validation summary dict returned by DataValidator.validate().
            Must contain keys: total_records, total_findings, critical_count,
            warning_count, pass_count, escalation_required, findings, timestamp.
        output_path: Absolute or relative path where the HTML file is written.

    Raises:
        FileNotFoundError: If the template file cannot be located.
        jinja2.TemplateNotFound: If template.html is missing from report/.
    """
    # Locate the template directory relative to this file
    template_dir = os.path.dirname(os.path.abspath(__file__))

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html"]),
    )

    template = env.get_template("template.html")

    # Group findings by severity
    by_severity: dict[str, list[dict]] = defaultdict(list)
    for finding in summary.get("findings", []):
        by_severity[finding.get("severity", "UNKNOWN")].append(finding)

    # Group findings by entity_id for the per-record breakdown section
    records_with_issues: dict[str, list[dict]] = defaultdict(list)
    for finding in summary.get("findings", []):
        key = finding.get("entity_id", "UNKNOWN")
        records_with_issues[key].append(finding)

    # Sort each record's issues: CRITICAL first, then WARNING
    severity_order = {"CRITICAL": 0, "WARNING": 1}
    for key in records_with_issues:
        records_with_issues[key].sort(
            key=lambda f: severity_order.get(f.get("severity", "WARNING"), 99)
        )

    # Render the template
    html_content = template.render(
        summary=summary,
        by_severity=dict(by_severity),
        records_with_issues=dict(records_with_issues),
    )

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    log_module.logger.info(f"Validation report written to: {output_path}")
    print(f"Report saved to: {output_path}")
