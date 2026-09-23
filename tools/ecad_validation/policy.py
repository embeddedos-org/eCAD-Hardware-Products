"""Validation policy constants shared by the engine, schemas, and reports."""

CONTRACT_VERSION = "1.0.0"
REQUIRED_GATES = ("V0", "V1", "V2", "V3", "V4")
DOMAINS = (
    "eda_circuit",
    "physical_design",
    "system_design",
    "device_modeling",
    "data_management",
    "integrated_physics",
)
LAYERS = ("design", "model", "simulation", "validation")

# A required check must be PASS. These states always deny release eligibility.
DENYING_VERDICTS = (
    "FAIL",
    "WARNING",
    "NOT_RUN",
    "BLOCKED",
    "INCONCLUSIVE",
)
