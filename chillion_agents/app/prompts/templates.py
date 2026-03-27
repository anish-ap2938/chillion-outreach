"""Email and LinkedIn message templates for Chillion outreach"""

# ==================== CHILLION PRODUCTS / SOLUTIONS ====================

CHILLION_PRODUCTS = {
    "it_infrastructure": {
        "name": "IT Infrastructure & Enterprise Solutions",
        "short_name": "IT Infrastructure",
        "description": "Enterprise hardware, servers, storage, networking, monitoring, and on-site or remote support under one accountable partner.",
        "key_features": [
            "HP, Dell, Lenovo, Fujitsu, and Acer enterprise hardware supply",
            "Network, server, and database monitoring with AMC support",
            "On-site and remote infrastructure maintenance pan-India",
        ],
        "pain_points": [
            "Fragmented IT vendors",
            "Unplanned downtime",
            "Aging server and storage estate",
            "Limited on-site support coverage",
        ],
        "blog_links": ["https://www.chillion.in/solutions/it-infrastructure"],
    },
    "cyber_security": {
        "name": "Cyber Security & Managed Services",
        "short_name": "Cyber Security",
        "description": "IDS/IPS, network security, surveillance, AMC, 24x7 monitoring, and business continuity for enterprise and government.",
        "key_features": [
            "Intrusion detection and prevention",
            "Network security and surveillance integration",
            "24x7 monitoring and managed AMC structures",
        ],
        "pain_points": [
            "Security gaps across distributed sites",
            "Reactive incident response",
            "Compliance and audit pressure",
            "Limited internal SOC capacity",
        ],
        "blog_links": ["https://www.chillion.in/solutions/cyber-security"],
    },
    "cloud_data_center": {
        "name": "Cloud, Data Center, SaaS & PaaS Solutions",
        "short_name": "Cloud & Data Center",
        "description": "Data center design, cloud migration, virtualization, and high-performance storage for enterprise and government.",
        "key_features": [
            "Data center design and deployment",
            "Cloud migration and virtualization",
            "High-performance storage architectures",
        ],
        "pain_points": [
            "Legacy infrastructure bottlenecks",
            "Slow cloud adoption",
            "Capacity planning uncertainty",
            "High operational overhead",
        ],
        "blog_links": ["https://www.chillion.in/solutions/cloud-data-center"],
    },
    "software_licensing": {
        "name": "Software Licensing & Digital Solutions",
        "short_name": "Software Licensing",
        "description": "CAD/CAM, simulation, Microsoft, virtualization, backup, DMS, and HPC software — licensed, deployed, and supported.",
        "key_features": [
            "ANSYS, Mathcad, Altair HiQube, and CAD/CAM tooling",
            "Document management and engineering workflows",
            "License procurement, deployment, and support",
        ],
        "pain_points": [
            "License compliance risk",
            "Tool sprawl across engineering teams",
            "Slow software rollout",
            "Limited local support for complex stacks",
        ],
        "blog_links": ["https://www.chillion.in/solutions/software-licensing"],
    },
    "defense_engineering": {
        "name": "Defense Technologies & Specialized Engineering",
        "short_name": "Defense Engineering",
        "description": "Defense electronics, simulation, PCB engineering, timing systems, and mission-critical engineering support.",
        "key_features": [
            "PCB design, fabrication, assembly, and test",
            "Simulation and engineering technologies",
            "Precision timing and synchronization systems",
        ],
        "pain_points": [
            "Long procurement cycles",
            "Specialized engineering capacity gaps",
            "Quality and traceability requirements",
            "Multi-vendor coordination overhead",
        ],
        "blog_links": ["https://www.chillion.in/solutions/defense-engineering"],
    },
    "optics_photonics": {
        "name": "Precision Engineering, Optics & Photonics",
        "short_name": "Optics & Photonics",
        "description": "Diamond machining, freeform optics, lens prototyping, and photonics solutions for defense and industrial programs.",
        "key_features": [
            "Optical design and lens prototyping",
            "Diamond direct cut steel technology",
            "Laser, photonics, and precision manufacturing",
        ],
        "pain_points": [
            "Long lead times for optical components",
            "High tooling and rework costs",
            "Limited in-house precision manufacturing",
            "Complex spec-to-delivery workflows",
        ],
        "blog_links": ["https://www.chillion.in/solutions/optics-photonics"],
    },
    "rf_microwave": {
        "name": "RF, Microwave & Antenna Solutions",
        "short_name": "RF & Microwave",
        "description": "RF and microwave products, antenna systems, simulation software, and defense communication integration.",
        "key_features": [
            "RF/microwave product integration",
            "Antenna systems and communication stacks",
            "Simulation-backed RF design support",
        ],
        "pain_points": [
            "Integration complexity across RF subsystems",
            "Performance validation under real conditions",
            "Vendor fragmentation in defense comms",
            "Limited local RF engineering bench strength",
        ],
        "blog_links": ["https://www.chillion.in/solutions/rf-microwave"],
    },
}

# ==================== EMAIL TEMPLATES ====================

EMAIL_TEMPLATES = {
    "infrastructure_intro": {
        "name": "IT Infrastructure Intro",
        "subject": "Single partner for {company_name}'s infrastructure and support",
        "body": """Hi {first_name},

Many enterprise and government teams we work with are consolidating hardware, networking, and AMC support under one accountable partner instead of juggling multiple vendors.

At Chillion, we supply and support enterprise IT infrastructure — servers, storage, networking, monitoring, and on-site or remote AMC — with pan-India coverage from our Hyderabad base.

If infrastructure reliability or vendor consolidation is on your roadmap this year, I would be happy to share a brief, relevant overview. You can pick a time here: [Calendly Demo Link].

Thanks,
{sender_name}
{sender_title}
Chillion IT & Consultancy Pvt. Ltd.
https://www.chillion.in""",
    },
    "defense_engineering": {
        "name": "Defense & Engineering Intro",
        "subject": "Engineering support for specialized defense and industrial programs",
        "body": """Hi {first_name},

We support defense, government, and industrial programs that need more than commodity IT — from PCB engineering and simulation to optics, photonics, RF, and precision manufacturing.

Chillion combines in-house engineering capabilities with structured delivery and AMC-style support so the team that scopes your requirement stays involved through implementation.

If you are evaluating partners for a specialized engineering or infrastructure program, I would welcome a short conversation. Book time here: [Calendly Demo Link].

Thanks,
{sender_name}
{sender_title}
Chillion IT & Consultancy Pvt. Ltd.
https://www.chillion.in""",
    },
    "custom": {
        "name": "AI-Generated Custom",
        "subject": None,
        "body": None,
    },
}

# ==================== LINKEDIN TEMPLATES ====================

LINKEDIN_TEMPLATES = {
    "connection_request": {
        "name": "Connection Request",
        "message": """Hi {first_name},

I noticed your work at {company_name} in technology and engineering programs. Chillion helps defense, government, and enterprise teams with IT infrastructure, cyber security, cloud, and specialized engineering.

Would love to connect.

Best,
{sender_name}""",
    },
    "infrastructure_pain_point": {
        "name": "Infrastructure Pain Point",
        "message": """Hi {first_name},

Quick question — is your team still coordinating infrastructure support across multiple vendors and regions?

Many {industry} leaders we speak with are consolidating hardware, networking, and AMC under one partner. Happy to share what we have seen work if useful.

{sender_name}""",
    },
    "defense_program": {
        "name": "Defense Program Outreach",
        "message": """Hi {first_name},

We work with defense and industrial programs on specialized engineering — PCB, simulation, optics, RF, and precision manufacturing — with delivery teams based in Hyderabad and pan-India support.

Open to a brief chat if you are scoping vendors for an upcoming program?

{sender_name}""",
    },
    "follow_up": {
        "name": "Follow-Up",
        "message": """Hi {first_name},

Following up on my earlier note. Chillion supports end-to-end technology programs across IT infrastructure, security, cloud, software licensing, and advanced engineering.

Worth a 15-minute call to see if we can help with anything on your roadmap?

{sender_name}""",
    },
    "custom": {
        "name": "AI-Generated Custom",
        "message": None,
    },
}


def get_product_info(product_key: str) -> dict:
    """Get product information by key"""
    return CHILLION_PRODUCTS.get(product_key, CHILLION_PRODUCTS["it_infrastructure"])


def get_email_template(template_key: str) -> dict:
    """Get email template by key"""
    return EMAIL_TEMPLATES.get(template_key, EMAIL_TEMPLATES["custom"])


def get_linkedin_template(template_key: str) -> dict:
    """Get LinkedIn template by key"""
    return LINKEDIN_TEMPLATES.get(template_key, LINKEDIN_TEMPLATES["custom"])


def format_template(template: str, **kwargs) -> str:
    """Format a template with provided values, leaving unfilled placeholders"""
    result = template
    for key, value in kwargs.items():
        if value:
            result = result.replace(f"{{{key}}}", str(value))
    return result
