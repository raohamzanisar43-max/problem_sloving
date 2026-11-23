"""
NovuLabs company profile — the only facts proposals and drafts may state about
the company. Taken from novulabs.net; edit here when the company details change.
"""

CAPABILITY_PROFILE = {
    'company': 'NovuLabs',
    'legal_name': 'NovuLabs Technology Pvt Ltd',
    'tagline': 'Enterprise software house engineering mission-critical platforms',
    'headquarters': 'I-10/3, Islamabad, Pakistan',
    'intro': (
        'NovuLabs is an enterprise software house headquartered in Islamabad, Pakistan. We engineer '
        'dependable web, mobile, AI and enterprise platforms for businesses worldwide, with products '
        'that serve over 1M active users and 24/7 support.'
    ),
    'services': [
        'Custom web platforms and SaaS development',
        'Mobile app development (Flutter, iOS, Android)',
        'Enterprise systems: ERP, CRM, inventory and business software',
        'Cloud, AI and automation',
        'Fintech and payments, AML/CFT compliance',
        'Healthcare IT (EHR, telemedicine, HIPAA / HL7 FHIR)',
        'EdTech: LMS, school management and virtual classrooms',
    ],
    'technologies': [
        'React', 'Node.js', 'Python', 'Java', '.NET Core', 'Flutter',
        'AWS', 'Azure', 'Docker', 'Kubernetes', 'PostgreSQL', 'TensorFlow',
    ],
    # Live products on novulabs.net that a proposal may cite as relevant work.
    'live_products': [
        'NovuLabs EduCore — AI-driven school management and LMS with admin, teacher, student and parent '
        'portals, AI smart exams and face attendance',
        'MarketingOS — multi-brand platform for drafting social posts with AI, approvals and scheduling',
        'Amanah Pool OS — Islamic finance pool management with maker-checker approvals and a full audit trail',
        'Inventory Management — SKUs, sales and purchase orders, warehouses, stock alerts and audit trail',
    ],
    'sectors': [
        'Banking & Fintech', 'Healthcare & MedTech', 'Government & Public Sector',
        'E-Commerce & Retail', 'Manufacturing & Logistics', 'Education & EdTech',
    ],
    'process': ['Consultation', 'Strategy', 'Implementation', 'Final result and support'],
    'promises': [
        'You work directly with an engineer who has built similar projects',
        'NDA signed upfront',
        'Post-launch support and maintenance',
    ],
    'engagement_models': [
        'Fixed-price project delivery',
        'Time-and-materials',
        'Dedicated team working alongside your existing team',
    ],
    'contact': {
        'email': 'info@novulabs.net',
        'phone': '+92 326 8292154',
        'website': 'https://novulabs.net',
    },
}


def profile_summary() -> str:
    """Return a compact text summary for injection into prompts."""
    p = CAPABILITY_PROFILE
    svc = ', '.join(p['services'][:5]) + ', and more.'
    tech = ', '.join(p['technologies'][:8])
    return (
        f"{p['company']} — {p['tagline']}.\n"
        f"HQ: {p['headquarters']}\n"
        f"Key services: {svc}\n"
        f"Core technologies: {tech}\n"
        f"Sectors: {', '.join(p['sectors'])}\n"
        f"Contact: {p['contact']['email']} | {p['contact']['phone']}"
    )
