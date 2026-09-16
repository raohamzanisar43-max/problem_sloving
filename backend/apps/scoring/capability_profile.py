"""
Novu Labs capability profile — used as system context for LLM draft writer.
Edit this dict to reflect the actual company's services, experience and references.
"""

CAPABILITY_PROFILE = {
    'company': 'Novu Labs',
    'tagline': 'End-to-end software & IT services partner',
    'headquarters': 'Pakistan (serving GCC, UK, US)',
    'team_size': '50–200 engineers',
    'services': [
        'Custom software development (web, mobile, enterprise)',
        'ERP implementation and customisation (Odoo, SAP, Oracle)',
        'Mobile application development (iOS, Android, Flutter, React Native)',
        'CRM and LMS platforms',
        'AI / ML automation and data pipelines',
        'Staff augmentation and dedicated development teams',
        'Managed IT services and cloud operations (AWS, Azure, GCP)',
        'DevOps, CI/CD, infrastructure as code',
        'Cybersecurity assessments and managed security',
    ],
    'technologies': [
        'Python / Django / FastAPI', 'JavaScript / TypeScript / React / Next.js',
        'Node.js', 'Flutter', 'React Native',
        '.NET / C#', 'Java / Spring Boot',
        'PostgreSQL / MySQL / MongoDB', 'Redis',
        'AWS / Azure / GCP', 'Docker / Kubernetes',
        'Odoo ERP', 'Salesforce', 'HubSpot',
    ],
    'engagement_models': [
        'Fixed-price project delivery',
        'Time-and-materials retainer',
        'Dedicated team / staff augmentation',
        'Managed service with SLA',
    ],
    'markets': ['Pakistan', 'UAE', 'Saudi Arabia', 'Qatar', 'United Kingdom', 'United States'],
    'certifications': ['ISO 9001 (quality)', 'AWS Partner'],
    'contact': {
        'email': 'sales@novulabs.com',
        'phone': '+92-xxx-xxxxxxx',
        'website': 'https://novulabs.com',
    },
}


def profile_summary() -> str:
    """Return a compact text summary for injection into prompts."""
    p = CAPABILITY_PROFILE
    svc = ', '.join(p['services'][:5]) + ', and more.'
    tech = ', '.join(p['technologies'][:8])
    return (
        f"{p['company']} — {p['tagline']}.\n"
        f"HQ: {p['headquarters']} | Team: {p['team_size']}\n"
        f"Key services: {svc}\n"
        f"Core technologies: {tech}\n"
        f"Markets served: {', '.join(p['markets'])}\n"
        f"Contact: {p['contact']['email']} | {p['contact']['website']}"
    )

