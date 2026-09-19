"""Human-readable reporting for validation receipts."""

from __future__ import annotations

import html
import json
import xml.etree.ElementTree as ET

from .models import ProductRunResult, RepositoryRunResult, Verdict


def product_markdown(product: ProductRunResult) -> str:
    lines = [
        f"# Validation report: {product.product_id}",
        "",
        f"- Product path: `{product.product_path}`",
        f"- eCAD commit: `{product.source_commit}`",
        f"- Input SHA-256: `{product.input_sha256}`",
        f"- Overall verdict: **{product.overall_verdict.value}**",
        f"- Eligible for ebuild: **{'yes' if product.eligible_for_ebuild else 'no'}**",
        "",
        "## Gates",
        "",
        "| Gate | Verdict | Checks |",
        "|---|---|---:|",
    ]
    for gate in product.gates:
        lines.append(f"| {gate.gate.value} | {gate.verdict.value} | {len(gate.checks)} |")
    lines.extend(["", "## Findings", ""])
    for gate in product.gates:
        for check in gate.checks:
            lines.append(
                f"### {check.check_id} — {check.verdict.value}"
            )
            lines.append("")
            lines.append(f"{check.summary} (`{check.reason_code}`)")
            lines.append("")
            for finding in check.findings:
                lines.append(f"- {finding}")
            if check.findings:
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def product_html(product: ProductRunResult) -> str:
    rows = []
    for gate in product.gates:
        for check in gate.checks:
            findings = "<br>".join(html.escape(item) for item in check.findings) or "&mdash;"
            rows.append(
                "<tr>"
                f"<td>{html.escape(gate.gate.value)}</td>"
                f"<td>{html.escape(check.check_id)}</td>"
                f"<td>{html.escape(check.execution_status.value)}</td>"
                f"<td>{html.escape(check.verdict.value)}</td>"
                f"<td>{html.escape(check.reason_code)}</td>"
                f"<td>{findings}</td>"
                "</tr>"
            )
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>Validation report: {html.escape(product.product_id)}</title>"
        "<style>body{font-family:system-ui,sans-serif;margin:2rem;line-height:1.5}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #999;"
        "padding:.45rem;text-align:left;vertical-align:top}</style></head><body>"
        f"<h1>Validation report: {html.escape(product.product_id)}</h1>"
        f"<p>Commit: <code>{html.escape(product.source_commit)}</code><br>"
        f"Input SHA-256: <code>{html.escape(product.input_sha256)}</code><br>"
        f"Overall: <strong>{html.escape(product.overall_verdict.value)}</strong><br>"
        f"ebuild eligible: <strong>{'yes' if product.eligible_for_ebuild else 'no'}</strong></p>"
        "<table><thead><tr><th>Gate</th><th>Check</th><th>Execution</th>"
        "<th>Verdict</th><th>Reason</th><th>Findings</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></body></html>\n"
    )


def junit_xml(result: RepositoryRunResult) -> bytes:
    checks = [
        (product, gate, check)
        for product in result.products
        for gate in product.gates
        for check in gate.checks
    ]
    failures = sum(check.verdict is Verdict.FAIL for _, _, check in checks)
    skipped = sum(check.verdict is not Verdict.PASS and check.verdict is not Verdict.FAIL for _, _, check in checks)
    suite = ET.Element(
        "testsuite",
        {
            "name": "ecad-hardware-validation",
            "tests": str(len(checks)),
            "failures": str(failures),
            "errors": "0",
            "skipped": str(skipped),
        },
    )
    for product, gate, check in checks:
        case = ET.SubElement(
            suite,
            "testcase",
            {
                "classname": product.product_id,
                "name": f"{gate.gate.value}:{check.check_id}",
            },
        )
        message = f"{check.reason_code}: {check.summary}"
        if check.verdict is Verdict.FAIL:
            failure = ET.SubElement(case, "failure", {"message": message})
            failure.text = "\n".join(check.findings)
        elif check.verdict is not Verdict.PASS:
            ET.SubElement(case, "skipped", {"message": message})
        output = ET.SubElement(case, "system-out")
        output.text = json.dumps(check.metrics, sort_keys=True, allow_nan=False)
    return ET.tostring(suite, encoding="utf-8", xml_declaration=True) + b"\n"


def repository_markdown(result: RepositoryRunResult) -> str:
    summary = result.to_summary()
    lines = [
        "# eCAD hardware validation summary",
        "",
        f"- eCAD commit: `{result.source_commit}`",
        f"- Inventory SHA-256: `{result.inventory_sha256}`",
        f"- Products executed: **{summary['product_count']}**",
        f"- Complete V0–V4 execution: **{'yes' if result.all_products_executed else 'no'}**",
        f"- Eligible for ebuild: **{len(result.eligible_products)}**",
        "",
        "| Product | Overall | ebuild eligible |",
        "|---|---|---|",
    ]
    for product in result.products:
        lines.append(
            f"| {product.product_id} | {product.overall_verdict.value} | "
            f"{'yes' if product.eligible_for_ebuild else 'no'} |"
        )
    return "\n".join(lines) + "\n"
