import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def create_implementation_plan_docx():
    doc = docx.Document()

    # Page setup - 1 inch margins
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Styling helper functions
    def add_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(24)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D) # Navy Blue
        return p

    def add_subtitle(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(14)
        run.font.italic = True
        run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
        return p

    def add_heading_1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(18)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
        return p

    def add_heading_2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6) # Medium Blue
        return p

    def add_heading_3(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Calibri'
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        return p

    def add_paragraph(text, bold_prefix=""):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            run_b = p.add_run(bold_prefix)
            run_b.font.name = 'Calibri'
            run_b.font.size = Pt(11)
            run_b.font.bold = True
            run_b.font.color.rgb = RGBColor(0x26, 0x26, 0x26)
        run_t = p.add_run(text)
        run_t.font.name = 'Calibri'
        run_t.font.size = Pt(11)
        run_t.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        return p

    def add_bullet(text, bold_prefix=""):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            run_b = p.add_run(bold_prefix)
            run_b.font.name = 'Calibri'
            run_b.font.size = Pt(11)
            run_b.font.bold = True
            run_b.font.color.rgb = RGBColor(0x26, 0x26, 0x26)
        run_t = p.add_run(text)
        run_t.font.name = 'Calibri'
        run_t.font.size = Pt(11)
        run_t.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        return p

    def add_callout(text, title="NOTE"):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        tcPr = cell._element.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F2F4F7"/>')
        tcPr.append(shd)
        borders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:left w:val="single" w:sz="24" w:space="0" w:color="1F497D"/><w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/></w:tcBorders>')
        tcPr.append(borders)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        run_title = p.add_run(f"[{title}] ")
        run_title.font.name = 'Calibri'
        run_title.font.size = Pt(11)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)
        run_text = p.add_run(text)
        run_text.font.name = 'Calibri'
        run_text.font.size = Pt(10.5)
        run_text.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        doc.add_paragraph()

    def style_table(table, col_widths, headers, data):
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_cells = table.rows[0].cells
        for i, header_text in enumerate(headers):
            hdr_cells[i].text = header_text
            tcPr = hdr_cells[i]._element.get_or_add_tcPr()
            shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="1F497D"/>')
            tcPr.append(shd)
            p = hdr_cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.name = 'Calibri'
                run.font.size = Pt(10.5)
                run.font.bold = True
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        
        for r_idx, row_data in enumerate(data):
            row_cells = table.add_row().cells
            bg_color = "F9FAFB" if r_idx % 2 == 1 else "FFFFFF"
            for c_idx, cell_value in enumerate(row_data):
                row_cells[c_idx].text = cell_value
                tcPr = row_cells[c_idx]._element.get_or_add_tcPr()
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>')
                tcPr.append(shd)
                p = row_cells[c_idx].paragraphs[0]
                for run in p.runs:
                    run.font.name = 'Calibri'
                    run.font.size = Pt(10)
                    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)

        for row in table.rows:
            for c_idx, w in enumerate(col_widths):
                row.cells[c_idx].width = Inches(w)

    # -------------------------------------------------------------
    # DOCUMENT CONTENT GENERATION
    # -------------------------------------------------------------
    add_title("Freelancer Marketplace API — Advanced Follow-Up Features")
    add_subtitle("Comprehensive Implementation Plan, Codebase Audit & System Flow Design")
    doc.add_paragraph()

    # Section 1: Executive Summary
    add_heading_1("1. Executive Summary & Project Context")
    add_paragraph("This document provides an exhaustive, production-grade technical implementation plan and system flow design for the Advanced Follow-Up Features specification of the Freelancer Marketplace API. The follow-up scope builds upon the existing FastAPI architecture, PostgreSQL/Supabase database stack, SQLAlchemy ORM, Alembic migrations, Pydantic validation schemas, JWT authentication, and server-side role-based authorization (CLIENT / FREELANCER roles).")
    add_paragraph("The assignment goal is to deliver three core advanced tracks:")
    add_bullet(" Event-driven Email & SMS notifications via Supabase/Twilio integrations with idempotency, bounded retries, template substitution, user preferences, and non-blocking asynchronous delivery.", "Track A — Notification System:")
    add_bullet(" Complete private object storage via Supabase Storage, with file metadata tracking in PostgreSQL, signed access URLs, resource lifecycle cascading cleanups, and ownership-based authorization.", "Track B — Secure File Storage:")
    add_bullet(" High-performance business analytics engine backed by efficient SQL aggregations, date-range filtering, database indexes, and role-scoped performance metrics.", "Track C — Advanced Analytics:")

    # Section 2: Codebase Audit & Gap Analysis
    add_heading_1("2. Codebase Audit & Implementation Gap Analysis")
    add_paragraph("An exhaustive audit of the existing codebase was conducted across models, services, routers, schemas, dependencies, and unit tests to determine current completion status.")
    
    headers_gap = ["Component / Track", "Current Status", "Implemented Components", "Remaining Work / Gaps"]
    data_gap = [
        ["Core API & Models", "100% Completed", "Auth, User, Freelancer Profile, Jobs, Proposals, Contracts, Milestones, Reviews, Sessions", "None. Core marketplace workflows are intact."],
        ["Track A: Notifications", "0% Completed (Missing)", "None", "All models, notification service, email/SMS provider triggers, background workers, preferences, and APIs."],
        ["Track B: Secure File Storage", "75% Completed (Partial)", "FileUpload model, FileStorageService, upload/download/delete endpoints for Profile, Proposal, Contract, Milestone", "Resource deletion cascading cleanup, stream upload for >50MB files, security unit tests."],
        ["Track C: Advanced Analytics", "0% Completed (Missing)", "None", "Analytics engine service, direct SQL aggregation queries, database compound indexes, views, role-scoped analytics APIs."]
    ]
    t_gap = doc.add_table(rows=1, cols=4)
    style_table(t_gap, [1.5, 1.1, 2.0, 2.4], headers_gap, data_gap)
    doc.add_paragraph()

    # Section 3: Track A Implementation Plan
    add_heading_1("3. Track A — Email & SMS Notification Subsystem Implementation Plan")
    add_paragraph("The Notification System will react to important marketplace lifecycle events and deliver multi-channel messages (EMAIL, SMS, or BOTH) without blocking core database transactions or risking transaction rollbacks due to notification provider failures.")
    
    add_heading_2("3.1 Proposed Database Schema & Alembic Migration")
    add_paragraph("Two new database tables will be created in PostgreSQL via Alembic migrations:")
    add_bullet(" Stores every notification event instance, metadata payload, channel choice, delivery status, retry count, error logs, and unique idempotency key.", "Table 1: notifications —")
    add_bullet(" Stores user-configurable notification preferences per channel (email_enabled, sms_enabled, transactional_enabled, marketing_enabled).", "Table 2: notification_preferences —")

    add_callout("idempotency_key = f'evt_{event_name}_{resource_id}_{action}' ensures duplicate webhook/API retries never send duplicate emails/SMS to users.", "IDEMPOTENCY STRATEGY")

    add_heading_2("3.2 Event Taxonomy & Marketplace Triggers")
    headers_evt = ["Event Name", "Target Recipient", "Channel", "Trigger Source / Location"]
    data_evt = [
        ["USER_REGISTERED", "Registered User", "EMAIL", "app/services/auth.py (create_user)"],
        ["PROPOSAL_RECEIVED", "Job Client Owner", "EMAIL, SMS", "app/services/proposal.py (submit_proposal)"],
        ["PROPOSAL_ACCEPTED", "Freelancer", "EMAIL, SMS", "app/services/proposal.py (accept_proposal)"],
        ["CONTRACT_CREATED", "Client & Freelancer", "EMAIL", "app/services/contract.py (create_contract_from_proposal)"],
        ["MILESTONE_SUBMITTED", "Client", "EMAIL", "app/services/milestone.py (submit_milestone)"],
        ["MILESTONE_APPROVED", "Freelancer", "EMAIL, SMS", "app/services/milestone.py (approve_milestone)"],
        ["MILESTONE_REJECTED", "Freelancer", "EMAIL", "app/services/milestone.py (reject_milestone)"],
        ["CONTRACT_COMPLETED", "Client & Freelancer", "EMAIL, SMS", "app/services/contract.py (complete_contract)"],
        ["REVIEW_SUBMITTED", "Contract Counterpart", "EMAIL", "app/services/review.py (create_review)"]
    ]
    t_evt = doc.add_table(rows=1, cols=4)
    style_table(t_evt, [1.8, 1.4, 1.1, 2.7], headers_evt, data_evt)
    doc.add_paragraph()

    add_heading_2("3.3 Proposed API Surface for Notifications")
    add_bullet(" GET /api/notifications — Retrieve current user's notification audit history (paginated).")
    add_bullet(" GET /api/notifications/preferences — Get current user's notification settings.")
    add_bullet(" PATCH /api/notifications/preferences — Update user's notification settings.")
    add_bullet(" POST /api/notifications/test — Development-only endpoint to test notification templates (disabled in production).")

    # Section 4: Track B Implementation Plan
    add_heading_1("4. Track B — Secure File Storage Gap Completion Plan")
    add_paragraph("The project already contains a robust FileStorageService and Uploads Router. To complete 100% of Track B PDF requirements, the following technical gaps will be addressed:")
    add_bullet(" Implement automatic Supabase Storage file cleanup hooks when an associated Proposal, Contract, or Milestone is deleted.", "Resource Deletion Lifecycle Strategy:")
    add_bullet(" For uploads exceeding 20MB, implement chunked/streamed uploads to prevent API memory exhaustion.", "Streamed Upload Strategy:")
    add_bullet(" Add automated Pytest security unit tests verifying that unassigned freelancers/clients cannot generate download URLs or delete private attachments.", "Security Test Suite:")

    # Section 5: Track C Implementation Plan
    add_heading_1("5. Track C — Advanced Analytics Engine Implementation Plan")
    add_paragraph("The Advanced Analytics subsystem will calculate real-time marketplace KPIs, aggregations, trend analysis, and skill metrics directly inside PostgreSQL using optimized SQL aggregation queries (avoiding loading raw datasets into Python memory).")

    add_heading_2("5.1 Required Analytics Endpoints & Metric Formulas")
    headers_ana = ["Endpoint", "Target Role", "Key Metrics Included", "Optimization Method"]
    data_ana = [
        ["GET /api/analytics/marketplace", "Public / Auth", "Job publication rate, Proposal-to-acceptance rate, Average proposals/job, Contract completion rate", "SQL aggregation + Compound Indexes"],
        ["GET /api/analytics/jobs", "CLIENT / FREELANCER", "Jobs created, published, closed count, completion trends by date range", "SQL date_trunc grouping"],
        ["GET /api/analytics/proposals", "CLIENT / FREELANCER", "Proposal funnel: submitted, accepted, rejected, acceptance rate", "SQL conditional SUM/COUNT"],
        ["GET /api/analytics/milestones", "CLIENT / FREELANCER", "Milestone submitted, approved, rejected, overdue rate, average completion timing", "SQL Timestamp age diffs"],
        ["GET /api/analytics/freelancer/me", "FREELANCER Only", "Contracts won, proposal success rate, total earnings, review rating averages", "Indexed filter (freelancer_id)"],
        ["GET /api/analytics/client/me", "CLIENT Only", "Total jobs posted, total spent, hiring velocity, proposal volume per job", "Indexed filter (client_id)"],
        ["GET /api/analytics/skills", "Public / Auth", "Most requested job skills, proposal activity by skill, skill conversion rate", "JOIN job_skills + proposals aggregation"],
        ["GET /api/analytics/trends", "Public / Auth", "Daily/weekly/monthly marketplace transaction volumes", "Materialized View / SQL date_trunc"]
    ]
    t_ana = doc.add_table(rows=1, cols=4)
    style_table(t_ana, [1.8, 1.4, 2.3, 1.5], headers_ana, data_ana)
    doc.add_paragraph()

    # Section 6: System Design & Development Flow Diagrams
    add_heading_1("6. System Design & Development Flow Diagrams")

    add_heading_2("6.1 High-Level Layered System Architecture")
    add_paragraph("The system follows a clean 4-tier decoupled architecture:")
    add_callout(
        "Client Request (Swagger/HTTP)\n"
        "       │\n"
        "       ▼\n"
        "┌─────────────────────────────────────────────────────────────┐\n"
        "│ FastAPI Routers Layer (Validation, Auth & Rate Limiting)    │\n"
        "└──────────────────────────────┬──────────────────────────────┘\n"
        "                               │\n"
        "                               ▼\n"
        "┌─────────────────────────────────────────────────────────────┐\n"
        "│ Business Services Layer (Contract, Milestone, Analytics)    │\n"
        "└──────────────────────────────┬──────────────────────────────┘\n"
        "                               │\n"
        "            ┌──────────────────┴──────────────────┐\n"
        "            ▼                                     ▼\n"
        "┌───────────────────────┐             ┌───────────────────────┐\n"
        "│ Notification Subsystem│             │ Storage Subsystem     │\n"
        "│ (Email/SMS Worker)    │             │ (Supabase Storage)    │\n"
        "└───────────┬───────────┘             └───────────┬───────────┘\n"
        "            │                                     │\n"
        "            └──────────────────┬──────────────────┘\n"
        "                               ▼\n"
        "┌─────────────────────────────────────────────────────────────┐\n"
        "│ Database Layer (PostgreSQL / Alembic / Views / Indexes)     │\n"
        "└─────────────────────────────────────────────────────────────┘",
        "SYSTEM ARCHITECTURE DIAGRAM"
    )

    add_heading_2("6.2 Event-Driven Notification Dispatch Flow")
    add_paragraph("The notification engine uses background tasks to guarantee zero transaction rollbacks on notification failure:")
    add_callout(
        "1. Marketplace Event Trigger (e.g., submit_milestone)\n"
        "   │\n"
        "   ├─► 2. Commit Core Database Transaction (Status = SUBMITTED)\n"
        "   │\n"
        "   └─► 3. Dispatch Async Background Task (Notification Engine)\n"
        "          │\n"
        "          ├─► 4. Check Idempotency Key (Skip if duplicate)\n"
        "          ├─► 5. Check User Preferences (Skip if channel disabled)\n"
        "          ├─► 6. Render Template with Variable Substitution\n"
        "          ├─► 7. Send via Supabase / Twilio Provider\n"
        "          └─► 8. Log Delivery Status (SENT / FAILED with Retry Backoff)",
        "NOTIFICATION FLOW DIAGRAM"
    )

    add_heading_2("6.3 Analytics Query & Aggregation Pipeline Flow")
    add_paragraph("Analytics requests bypass Python memory loading by using optimized SQL queries:")
    add_callout(
        "Client GET /api/analytics/marketplace?start_date=2026-01-01&end_date=2026-09-01\n"
        "   │\n"
        "   ▼\n"
        "FastAPI Router (Role Authorization & Query Param Parsing)\n"
        "   │\n"
        "   ▼\n"
        "Analytics Service (SQLAlchemy Executing Single SQL Aggregation Query)\n"
        "   │\n"
        "   ▼\n"
        "PostgreSQL Query Engine (Utilizing Compound Indexes on status & created_at)\n"
        "   │\n"
        "   ▼\n"
        "Aggregated Result Row Returned Directly to FastAPI -> JSON Output Response",
        "ANALYTICS PIPELINE DIAGRAM"
    )

    # Section 7: Definition of Done & Quality Assurance
    add_heading_1("7. Definition of Done & Verification Criteria")
    add_bullet(" All three tracks (Notifications, File Storage, Analytics) fully implemented and integrated into FastAPI.", "1. Functional Completeness:")
    add_bullet(" Zero regressions on existing Auth, Job, Proposal, Contract, Milestone, and Review endpoints.", "2. Backward Compatibility:")
    add_bullet(" 100% server-side role authorization and resource ownership protection enforced.", "3. Security & Scope Enforcement:")
    add_bullet(" All database migrations applied successfully via Alembic scripts.", "4. Migration Integrity:")
    add_bullet(" Pytest suite passing cleanly for success paths, error paths, idempotency, and security boundaries.", "5. Automated Testing:")
    add_bullet(" Railway deployment verified with environment variables documented in .env.example.", "6. Deployment Readiness:")

    doc.save("Freelancer_Marketplace_FollowUp_Implementation_Plan_and_System_Design.docx")
    print("DOCUMENT SUCCESSFULLY CREATED!")

if __name__ == "__main__":
    create_implementation_plan_docx()
