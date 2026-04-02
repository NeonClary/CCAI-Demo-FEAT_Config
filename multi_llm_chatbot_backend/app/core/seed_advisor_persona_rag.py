"""
Seed default advisor-specific RAG entries (curated summaries + citation URLs).

Full PDFs are not fetched at runtime; text below is for retrieval. Users may add
more documents via the Admin knowledge UI.
"""

import logging
from typing import Any, Dict, List

from app.core.rag_manager import get_rag_manager
from app.core.rag_scopes import RAG_SCOPE_PERSONA, SESSION_ADMIN_PERSONA

LOG = logging.getLogger(__name__)

ADVISOR_PERSONA_ENTRIES: List[Dict[str, Any]] = [
    # --- Washington Regulations Advisor (wac_advisor) ---
    {
        "filename": "seed_wac_rcw_19_27_building_code_act.txt",
        "persona_id": "wac_advisor",
        "citation_title": "RCW Chapter 19.27 — Washington State Building Code Act",
        "source_url": "https://app.leg.wa.gov/rcw/default.aspx?cite=19.27&full=true",
        "body": """
RCW Chapter 19.27 is the Washington State Building Code Act. It governs how Washington adopts and amends
the International Building Code (IBC), International Residential Code (IRC), and related model codes for
plumbing, mechanical, energy, and fuel gas. The chapter establishes the State Building Code Council’s
authority, the typical three-year adoption cycle aligned with model code updates, and how local
jurisdictions may adopt amendments. It explains the relationship between state minimum standards and
local code amendments. Use this chapter to answer “why” Washington’s codes look the way they do and how
state law authorizes WAC provisions that implement the building code. Always verify the adopted code
edition and local amendments for the specific jurisdiction and project date.
""",
    },
    {
        "filename": "seed_wac_296_155_safety_construction.txt",
        "persona_id": "wac_advisor",
        "citation_title": "WAC 296-155 — Safety Standards for Construction Work (WA L&I / DOSH)",
        "source_url": "https://app.leg.wa.gov/wac/default.aspx?cite=296-155",
        "body": """
WAC 296-155 contains Washington’s safety standards for construction work. Washington operates its own
state-plan occupational safety and health program (WISHA) administered by Labor & Industries (L&I),
Division of Occupational Safety and Health (DOSH). Most construction employers in Washington are subject
to L&I enforcement rather than federal OSHA. WAC 296-155 is the construction-specific counterpart to
federal 29 CFR 1926; when advising Washington projects, cite WAC 296-155 alongside or instead of federal
OSHA where WISHA applies. Topics include general safety and health provisions, personal protective
equipment, fall protection, excavation, cranes, electrical, and other construction hazards. Cross-check
the current WAC text and any DOSH directives or policies for the specific hazard.
""",
    },
    {
        "filename": "seed_wac_197_11_sepa.txt",
        "persona_id": "wac_advisor",
        "citation_title": "WAC 197-11 — SEPA Rules (State Environmental Policy Act)",
        "source_url": "https://ecology.wa.gov/regulations-permits/sepa/environmental-review/sepa-laws-rules",
        "body": """
WAC 197-11 implements the State Environmental Policy Act (SEPA) in Washington. It sets procedural rules
for environmental review of construction and other project actions. The lead agency determines
jurisdiction, identifies probable environmental impacts, and decides whether a threshold determination,
Environmental Impact Statement (EIS), or exemption applies. The rules address categorical exemptions,
SEPA checklists, scoping, timing of review relative to permits, and mitigation. For construction projects,
SEPA often runs parallel to local land-use and building permits. Essential concepts: threshold determination,
DNS (determination of nonsignificance), DS (determination of significance), adoption of existing documents,
and appeals. Ecology and local governments publish guidance; tie advice to WAC 197-11 articles and the
lead agency’s role for the specific proposal.
""",
    },
    # --- Washington Land Use Advisor (land_use_advisor) ---
    {
        "filename": "seed_land_use_vision_2050_psrc.txt",
        "persona_id": "land_use_advisor",
        "citation_title": "VISION 2050 — Full Plan (PSRC)",
        "source_url": "https://www.psrc.org/sites/default/files/2022-02/vision-2050-plan%20(1).pdf",
        "body": """
VISION 2050 is the Puget Sound Regional Council (PSRC) regional growth strategy for the central Puget
Sound region. The plan sets multicounty planning policies, regional growth strategy, and actions that
guide where and how the region grows through 2050. It informs updates to countywide planning policies
(CPPs) and local comprehensive plans under the Growth Management Act. Key themes include housing,
transportation, equity, economic development, and climate. When answering questions about regional
consistency, urban growth boundaries, or alignment of local plans with regional policy, reference
VISION 2050 themes and the relationship to PSRC’s role under RCW 36.70A.410. The official adopted PDF
should be consulted for exact policy language; this summary supports retrieval of core concepts only.
""",
    },
    {
        "filename": "seed_land_use_rcw_36_70a_gma.txt",
        "persona_id": "land_use_advisor",
        "citation_title": "RCW 36.70A — Washington Growth Management Act (GMA)",
        "source_url": "https://app.leg.wa.gov/rcw/default.aspx?cite=36.70a&full=true",
        "body": """
RCW Chapter 36.70A is the Growth Management Act (GMA)—Washington’s foundational statute for managing
growth and development. It requires counties and cities that fully plan to adopt comprehensive plans and
development regulations that address mandatory elements: land use, housing, capital facilities, utilities,
rural lands, transportation, recreation, and more. The GMA defines critical areas (wetlands, fish and
wildlife habitat, geologic hazard, flood, aquifer recharge) and requires their protection. It establishes
urban growth areas (UGAs), countywide planning policies, and coordination between jurisdictions. VISION 2050
and local comp plans implement the GMA regionally and locally. Use the RCW for statutory authority,
deadlines, and mandatory plan updates; cite specific sections when discussing appeals, concurrency, or
environmental review integration with SEPA.
""",
    },
    {
        "filename": "seed_land_use_mrsc_comprehensive_planning.txt",
        "persona_id": "land_use_advisor",
        "citation_title": "MRSC — Comprehensive Planning Resource Page",
        "source_url": "https://mrsc.org/explore-topics/planning/gma/comprehensive-planning",
        "body": """
The Municipal Research and Services Center (MRSC) maintains practical guidance on comprehensive planning
under the GMA. Cities and counties that fully plan must periodically review and update comprehensive
plans (typically on a 10-year cycle under state schedules). The MRSC page compiles update timelines,
Department of Commerce guidance, examples of local code adoptions, and links to countywide planning
policies. It helps bridge statute (RCW 36.70A) and on-the-ground implementation: public participation,
SEPA integration, housing action plans, and consistency between regional, countywide, and local plans.
Use it for practitioner-focused questions about process, checklists, and where to find model ordinances.
""",
    },
    # --- Employee Handbook Advisor (dunn_employee_assist) ---
    {
        "filename": "seed_hr_dunn_handbook_2023.txt",
        "persona_id": "dunn_employee_assist",
        "citation_title": "Dunn Construction Employee Handbook (Effective January 1, 2023)",
        "source_url": "https://www.dunnconstruction.com/wp-content/uploads/2023/01/Dunn-Construction-Handbook-Effective-Jan.-1-2023-.pdf",
        "body": """
The Dunn Construction Employee Handbook (effective January 1, 2023) is the company’s primary policy
document for employment terms. It typically covers: employment relationship and at-will status; conduct
and code of ethics; anti-harassment and equal opportunity; attendance and timekeeping; paid time off (PTO)
and leave; benefits eligibility and enrollment; workplace safety reporting; drug and alcohol policy;
discipline and grievance procedures; use of company equipment and vehicles; and confidentiality.

Workplace safety concerns: Employees should report hazards, unsafe conditions, or safety concerns to their
supervisor or project manager as soon as practical. The handbook describes how to escalate concerns to HR
or safety leadership and may reference anonymous or non-retaliation reporting options where applicable.
For emergencies, follow site emergency procedures and 911 when life or health is at risk.

Injuries and first aid: For minor cuts, scrapes, or injuries on the job, workers should notify their
supervisor, obtain first aid per site procedures, and complete any required incident or near-miss
reporting. Serious injuries require immediate medical attention and documentation per company policy.

Policies may change; direct employees to HR for the authoritative PDF and for matters requiring individual
interpretation. When answering, distinguish general industry practice from company-specific policy and
encourage verification against the current handbook posted by the employer.
""",
    },
    {
        "filename": "seed_hr_dunn_handbook_reporting_injury_supplement.txt",
        "persona_id": "dunn_employee_assist",
        "citation_title": "Dunn Construction Employee Handbook (Effective January 1, 2023)",
        "source_url": "https://www.dunnconstruction.com/wp-content/uploads/2023/01/Dunn-Construction-Handbook-Effective-Jan.-1-2023-.pdf",
        "body": """
Reporting workplace safety concerns: Tell your supervisor or project manager about hazards, unsafe acts,
or near-misses promptly. Escalate to HR or corporate safety per the handbook’s chain of reporting.
Company policy may include non-retaliation protections for good-faith reporting.

On-the-job injuries (e.g., cuts, scrapes): Notify your supervisor, use site first-aid supplies and
procedures, and complete incident reporting as required. Seek medical care when appropriate; serious
injuries require emergency response and documentation under company and OSHA expectations.
""",
    },
    {
        "filename": "seed_hr_aldot_2_12_contractor_compliance.txt",
        "persona_id": "dunn_employee_assist",
        "citation_title": "ALDOT Construction Manual — §2.12 Contractor Compliance Requirements",
        "source_url": "https://www.dot.state.al.us/publications/Construction/pdf/ConstructionManual/2.12ContractorComplianceRequirements.pdf",
        "body": """
Alabama Department of Transportation (ALDOT) Construction Manual Section 2.12 addresses contractor
compliance requirements on ALDOT projects. It covers certified payroll submissions, prevailing wage
obligations under federal Davis-Bacon and Related Acts when applicable to federally funded work,
employee classifications, subcontractor compliance, and documentation the project manager or resident
engineer must review. Field supervisors and project managers use this section to understand payroll
documentation, labor interviews, and escalation when noncompliance is suspected. For Dunn teams on
ALDOT or similar federal-aid highway work, tie guidance to contract-specific wage determinations and
the prime contractor’s flow-down obligations to subcontractors.
""",
    },
    {
        "filename": "seed_hr_dol_davis_bacon_compliance_guide.txt",
        "persona_id": "dunn_employee_assist",
        "citation_title": "U.S. DOL Davis-Bacon Act Compliance Guide",
        "source_url": "https://webapps.dol.gov/elaws/elg/dbra.htm",
        "body": """
The U.S. Department of Labor eLaws Davis-Bacon and Related Acts (DBRA) guide explains prevailing wage
requirements on federally funded construction contracts. Contractors and subcontractors must pay not less
than locally prevailing wages and fringe benefits listed on the wage determination for the job classification.
Key topics: weekly payrolls, proper classification of laborers and mechanics, fringe benefit credit,
apprentices registered in approved programs, overtime, and record retention. On projects where Alabama
has no separate state prevailing wage law, federal Davis-Bacon often governs wage rates on federal-aid
projects. Direct employees to payroll, project controls, or HR for certified payroll questions and to the
contract’s wage decision for exact rates and classifications.
""",
    },
]


def seed_advisor_persona_rag_documents() -> None:
    """Load curated persona-scoped reference entries into Chroma (idempotent by filename)."""
    rag = get_rag_manager()
    stats = rag.get_document_stats(SESSION_ADMIN_PERSONA)
    already = {d.get("filename") for d in stats.get("documents", [])}

    added = 0
    for entry in ADVISOR_PERSONA_ENTRIES:
        fn = entry["filename"]
        if fn in already:
            LOG.debug("Advisor persona RAG already loaded: %s", fn)
            continue
        body = (entry.get("body") or "").strip()
        if len(body) < 40:
            continue
        res = rag.add_document(
            content=body,
            filename=fn,
            session_id=SESSION_ADMIN_PERSONA,
            file_type="txt",
            rag_scope=RAG_SCOPE_PERSONA,
            source_url=entry.get("source_url", ""),
            citation_title=entry.get("citation_title", fn),
            persona_id=entry["persona_id"],
        )
        if res.get("success"):
            added += 1
            LOG.info("Seeded advisor persona RAG: %s -> %s", fn, entry["persona_id"])
        else:
            LOG.warning("Failed to seed %s: %s", fn, res.get("error"))

    if added:
        LOG.info("Advisor persona RAG: added %s new document(s)", added)
    else:
        LOG.info("Advisor persona RAG: no new seed documents to add")
