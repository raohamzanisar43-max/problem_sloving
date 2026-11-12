from apps.sources.models import SearchTerm

new_terms = {
    "AML & compliance services": [
        "looking for an outsourced MLRO",
        "need an external MLRO",
        "looking for MLRO services",
        "need a fractional compliance officer",
        "looking for an outsourced compliance officer",
        "need compliance outsourcing services",
        "looking for a compliance retainer",
        "need an AML consultant",
        "looking for an AML policy consultant",
        "need an AML compliance program",
        "looking for AML risk assessment services",
        "need an enterprise wide risk assessment",
        "looking for KYC policy development",
        "need KYB policy development",
        "looking for sanctions policy development",
        "need a transaction monitoring policy",
        "looking for compliance manual preparation",
        "need an independent AML review",
        "looking for AML audit services",
        "need a compliance health check",
        "looking for an AML gap assessment",
        "need compliance remediation support",
    ],
    "Governance & audit services": [
        "looking for a corporate governance consultant",
        "need board advisory services",
        "looking for an enterprise risk management consultant",
        "need an internal controls review",
        "looking for SOP development services",
        "need a policy development consultant",
        "looking for outsourced internal audit",
        "need an internal audit consultant",
        "looking for operational audit services",
        "need a process audit",
        "looking for audit readiness support",
    ],
    "Accounting & tax services": [
        "need outsourced bookkeeping",
        "looking for accounting services",
        "need management accounts preparation",
        "looking for financial reporting support",
        "need an outsourced CFO",
        "looking for financial modelling services",
        "need a corporate tax consultant",
        "looking for a VAT consultant",
        "need tax filing support",
        "looking for tax compliance services",
        "need a cybersecurity risk assessment",
    ],
    "Roman Urdu": [
        "website banwani hai",
        "website bananay wala chahiye",
        "application banwani hai",
        "software banwana hai",
        "school software chahiye",
        "school management system chahiye",
        "developer chahiye",
        "koi developer recommend kar dein",
        "website developer chahiye",
        "payroll software chahiye",
        "accounting software chahiye",
        "CRM chahiye",
        "chatbot banwana hai",
        "business automate karna hai",
        "accountant chahiye",
        "tax consultant chahiye",
        "AML consultant chahiye",
        "company register karwani hai",
    ],
}

created = 0
skipped = 0
for group, queries in new_terms.items():
    for q in queries:
        quoted = f'"{q}"'
        obj, was_created = SearchTerm.objects.get_or_create(
            query=quoted,
            market="PK",
            defaults={"group_name": group, "language": "en", "enabled": True},
        )
        if was_created:
            created += 1
        else:
            skipped += 1

print(f"Created: {created}, Skipped (already existed): {skipped}")
