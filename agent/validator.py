"""
validator.py — Core orchestrator for the Data Validation Agent.

The DataValidator class loads configuration, runs all 4 validation rule
modules in sequence, aggregates findings, and produces a structured
validation summary. It also triggers escalation logging if critical
issues are found.
"""

import yaml
import pandas as pd
from datetime import datetime

from agent.rules.missing_value import check_missing_values
from agent.rules.threshold import check_thresholds
from agent.rules.anomaly import check_anomalies
from agent.rules.cross_field import check_cross_fields
import logger as log_module


class DataValidator:
    """
    Orchestrates all data validation checks against the compliance dataset.

    Loads configuration from config.yaml and runs four rule modules in order:
    1. Missing Value Detection
    2. Threshold Validation
    3. Statistical Anomaly Detection
    4. Cross-Field Validation

    Attributes:
        config (dict): Parsed YAML configuration.
        config_path (str): Path to the config file.
    """

    def __init__(self, config_path=None, config_dict=None) -> None:
        """
        Initialise the DataValidator by loading configuration.

        Args:
            config_path: Path to the config.yaml file.
            config_dict: Parsed config dict (used by web layer).

        Raises:
            ValueError: If neither config_path nor config_dict is provided.
            FileNotFoundError: If the config file cannot be found.
            yaml.YAMLError: If the config file is malformed.
        """
        if config_dict:
            self.config = config_dict
            self.config_path = None
            log_module.logger.info("Configuration loaded from dict (web layer)")
        elif config_path:
            self.config_path = config_path
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)
            log_module.logger.info(f"Configuration loaded from: {config_path}")
        else:
            raise ValueError("Either config_path or config_dict must be provided")

    def validate(self, df: pd.DataFrame) -> dict:
        """
        Run all 4 validation rule modules against the dataset.

        Executes modules in order, collects all findings, and returns a
        structured summary dict. Triggers escalation via logger if any
        critical findings are found.

        Args:
            df: The compliance dataset as a pandas DataFrame.

        Returns:
            A validation summary dict with keys:
                total_records, total_findings, critical_count,
                warning_count, pass_count, escalation_required,
                findings, timestamp.
        """
        all_findings: list[dict] = []

        # Rule 1: Missing values
        required_fields = self.config.get("required_fields", [])
        missing_findings = check_missing_values(df, required_fields)
        all_findings.extend(missing_findings)
        log_module.logger.info(
            f"Missing value check: {len(missing_findings)} finding(s)"
        )
        print("  [✓] Missing value check complete")

        # Rule 2: Threshold violations
        thresholds = self.config.get("thresholds", {})
        threshold_findings = check_thresholds(df, thresholds)
        all_findings.extend(threshold_findings)
        log_module.logger.info(
            f"Threshold validation: {len(threshold_findings)} finding(s)"
        )
        print("  [✓] Threshold validation complete")

        # Rule 3: Anomaly detection
        anomaly_config = self.config.get("anomaly_detection", {})
        anomaly_findings = check_anomalies(df, anomaly_config)
        all_findings.extend(anomaly_findings)
        log_module.logger.info(
            f"Anomaly detection: {len(anomaly_findings)} finding(s)"
        )
        print("  [✓] Anomaly detection complete")

        # Rule 4: Cross-field validation
        cross_field_rules = self.config.get("cross_field_rules", [])
        cross_findings = check_cross_fields(df, cross_field_rules)
        all_findings.extend(cross_findings)
        log_module.logger.info(
            f"Cross-field validation: {len(cross_findings)} finding(s)"
        )
        print("  [✓] Cross-field validation complete")

        # Aggregate counts
        total_records = len(df)
        total_findings = len(all_findings)
        critical_count = sum(
            1 for f in all_findings if f.get("severity") == "CRITICAL"
        )
        warning_count = sum(
            1 for f in all_findings if f.get("severity") == "WARNING"
        )

        # "Pass" metric is based on critical findings only:
        # each critical finding is treated as one failed record unit.
        # Warnings are informational and do not reduce pass_count.
        pass_count = max(total_records - critical_count, 0)

        # Escalation logic
        critical_threshold = self.config.get("escalation", {}).get(
            "critical_threshold", 1
        )
        escalation_required = critical_count >= critical_threshold

        summary = {
            "total_records": total_records,
            "total_findings": total_findings,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "pass_count": pass_count,
            "escalation_required": escalation_required,
            "findings": all_findings,
            "timestamp": datetime.now().isoformat(),
        }

        # Log summary
        log_module.logger.info(
            f"Validation complete — {total_records} records, "
            f"{total_findings} findings "
            f"({critical_count} critical, {warning_count} warnings)"
        )

        # Trigger escalation if needed
        if escalation_required:
            log_module.escalate(
                f"{critical_count} critical finding(s) require immediate attention"
            )

        return summary
