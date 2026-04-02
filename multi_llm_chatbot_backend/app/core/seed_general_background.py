"""
Seed general (all-persona) construction reference text into Chroma with citation URLs.

Each entry becomes one logical document; chunks are created inside add_document.
"""

import logging
from typing import Any, Dict, List

from app.core.rag_manager import get_rag_manager
from app.core.rag_scopes import RAG_SCOPE_GENERAL, SESSION_GENERAL_BACKGROUND

LOG = logging.getLogger(__name__)

# Curated summaries for embedding (not full regulatory text). URLs point to official sources.
GENERAL_BACKGROUND_ENTRIES: List[Dict[str, Any]] = [
    {
        "filename": "osha_1926_construction_standards.txt",
        "citation_title": "OSHA 29 CFR 1926 — Safety and Health Regulations for Construction",
        "source_url": "https://www.osha.gov/laws-regs/regulations/standardnumber/1926",
        "body": """
Federal OSHA construction standards (29 CFR Part 1926) govern safety and health on construction sites.
Topics include: fall protection, scaffolding, stairways and ladders, electrical wiring and equipment,
excavations and trenching, personal protective equipment, cranes and derricks, steel erection,
demolition, blasting, motor vehicles, concrete and masonry construction, underground construction,
confined spaces, hazardous materials, and recordkeeping. This part is the most-cited regulatory
framework for U.S. construction safety. Inspectors reference subparts by letter (e.g., Subpart M fall protection).
When advising on compliance, tie recommendations to the relevant subpart and encourage verification against the current rule text.
""",
    },
    {
        "filename": "osha_construction_portal.txt",
        "citation_title": "OSHA Construction Industry Portal",
        "source_url": "https://www.osha.gov/construction",
        "body": """
The OSHA construction portal aggregates enforcement guidance, letters of interpretation, training materials,
and emphasis programs. It highlights the "Focus Four" hazards (falls, struck-by, caught-in/between, electrocution)
and frequently publishes lists of most-cited standards. Use it to find quick links to eTools, compliance
assistance, and regional emphasis notices relevant to active jobsites.
""",
    },
    {
        "filename": "ibc_2021_digital_codes.txt",
        "citation_title": "2021 International Building Code (IBC) — ICC Digital Codes",
        "source_url": "https://codes.iccsafe.org/content/IBC2021P2",
        "body": """
The IBC is a model building code addressing structural design, fire-resistance, means of egress, occupancy
classification, height and area limits, interior finishes, and referenced standards. Jurisdictions adopt it
with local amendments. For design and permitting questions, identify the adopted edition year and local
amendments; the online viewer supports keyword search within chapters for egress width, occupancy loads,
and fire-protection requirements.
""",
    },
    {
        "filename": "nfpa_codes_portal.txt",
        "citation_title": "NFPA Codes & Standards (NEC, NFPA 101, and others)",
        "source_url": "https://www.nfpa.org/for-professionals/codes-and-standards",
        "body": """
NFPA publishes the National Electrical Code (NFPA 70), Life Safety Code (NFPA 101), and hundreds of fire,
electrical, and emergency standards. Construction specs often reference NFPA editions by year. The NFPA
site provides purchase and subscription access; summaries in RAG are for orientation—verify edition and
article numbers against the contract documents.
""",
    },
    {
        "filename": "ada_standards_accessible_design.txt",
        "citation_title": "2010 ADA Standards for Accessible Design",
        "source_url": "https://www.access-board.gov/ada/",
        "body": """
The 2010 ADA Standards (often coordinated with ICC A117.1) define scoping and technical requirements for
accessible routes, doors, restrooms, parking, signage, and fixtures in new construction and alterations.
The Access Board provides the official text and illustrations. When comparing to local code, remember ADA
is a civil rights law; state and local accessibility codes may impose additional requirements.
""",
    },
    {
        "filename": "ada_checklist_existing_facilities.txt",
        "citation_title": "ADA Checklist for Existing Facilities",
        "source_url": "https://www.adachecklist.org/doc/fullchecklist/ada-checklist.pdf",
        "body": """
Practical field checklist for surveying existing buildings for ADA compliance during renovations and
tenant improvements. Covers parking, entrances, routes, restrooms, drinking fountains, and more. Useful
for gap analysis before design; not a substitute for designer-of-record review against current standards.
""",
    },
    {
        "filename": "epa_cgp_stormwater_2022.txt",
        "citation_title": "EPA Construction General Permit (CGP) — Stormwater",
        "source_url": "https://www.epa.gov/npdes/2022-construction-general-permit-cgp",
        "body": """
The CGP is an NPDES permit for stormwater discharges from construction activities disturbing one acre or more
(or smaller sites that are part of a larger common plan of development). It requires SWPPP preparation,
erosion and sediment controls, pollution prevention, inspections, and corrective actions. Sites must comply
with effluent limits and applicable state-issued permits where EPA is not the permitting authority.
""",
    },
    {
        "filename": "epa_cgp_resources_templates.txt",
        "citation_title": "EPA CGP Resources, Tools, and SWPPP Templates",
        "source_url": "https://www.epa.gov/npdes/construction-general-permit-resources-tools-and-templates",
        "body": """
EPA provides SWPPP templates, inspection forms, rain event action documentation, and guidance for
stormwater management on construction sites. Field staff can adapt templates to project-specific BMPs;
ensure the SWPPP matches permit conditions and state requirements.
""",
    },
    {
        "filename": "epa_myerg_guide.txt",
        "citation_title": 'EPA "Managing Your Environmental Responsibilities" (MYER)',
        "source_url": "https://www.epa.gov/npdes/construction-general-permit-resources-tools-and-templates",
        "body": """
Referenced from EPA CGP resources: a plain-language guide walking through environmental compliance
considerations across project phases—from pre-construction planning through closeout—including waste,
hazardous materials, wetlands, air quality, and stormwater. Use it as a checklist for environmental
roles and responsibilities on mid-size construction projects.
""",
    },
    {
        "filename": "osha_pocket_guide_construction.txt",
        "citation_title": "OSHA Pocket Guide for Construction (Publication 3252)",
        "source_url": "https://www.osha.gov/construction/compliance",
        "body": """
OSHA's pocket guide summarizes key construction standards in a compact format suitable for toolbox talks
and superintendent reference. It is not a substitute for the full regulatory text but helps prioritize
common hazards and training topics on site.
""",
    },
]


def seed_general_background_publications() -> None:
    """Load curated general-background entries into Chroma (idempotent by filename)."""
    rag = get_rag_manager()
    stats = rag.get_document_stats(SESSION_GENERAL_BACKGROUND)
    already = {d.get("filename") for d in stats.get("documents", [])}

    added = 0
    for entry in GENERAL_BACKGROUND_ENTRIES:
        fn = entry["filename"]
        if fn in already:
            LOG.debug("General background already loaded: %s", fn)
            continue
        body = (entry.get("body") or "").strip()
        if len(body) < 40:
            continue
        res = rag.add_document(
            content=body,
            filename=fn,
            session_id=SESSION_GENERAL_BACKGROUND,
            file_type="txt",
            rag_scope=RAG_SCOPE_GENERAL,
            source_url=entry.get("source_url", ""),
            citation_title=entry.get("citation_title", fn),
            persona_id="",
        )
        if res.get("success"):
            added += 1
            LOG.info("Seeded general background: %s", fn)
        else:
            LOG.warning("Failed to seed %s: %s", fn, res.get("error"))

    if added:
        LOG.info("General background RAG: added %s new publication(s)", added)
    else:
        LOG.info("General background RAG: no new publications to add")
