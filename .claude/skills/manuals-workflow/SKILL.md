---
name: manuals-workflow
description: Procedures and rules for generating, updating, and taking screenshots for connect_diagnostics_manual and connect_diagnostics_uat_manual apps.
argument-hint: "<manual action or module>"
---

# Manuals Workflow & Rules

The manuals are two independent Frappe apps:
- `connect_diagnostics_manual`: System manuals and publishing engine (`engine.py`).
- `connect_diagnostics_uat_manual`: UAT test guides.

Installed on separate sites with only `frappe`, `wiki`, and the manual app. `connect_diagnostics_setup` does not publish directly; tools in `manual/` write into them.

## Mandatory Rules (Owner, Oct 2026)
1. **Synchronous Updates**: A code change that alters user behavior/UI MUST update the manual chapter (`manuals/<space>/manual.md`), retake screenshots, and update tests in the same PR.
2. **Screenshots**:
   - Every page must have at least one screenshot with numbered red boxes showing what to click (stored via Git LFS).
   - Picture blocks: a `###` subheading, the image, a caption line directly under it (`*ภาพที่ <chapter>.<n> ...*`, one pair of asterisks, no blank line), then a numbered list for that picture only. Boxes are numbered 1..n, one number per box, restarting at 1 in each block; item k explains box k. General rules go in their own block, never in a picture's list.
   - Company manual (`basics` and other system spaces) pictures are data-driven: write prose with `<!-- pic-here: <id> -->`, add the picture to `manual_site/pictures/<space>.yaml` (steps, boxes, Thai lines), then `python -m connect_diagnostics_setup.manual_site.pictures run|render|check <space>` on the mock site (`manual_site/README.md` "Picture specs"); look at every PNG. Never hand-code a picture or hand-edit a block between `pic:begin`/`pic:end`.
   - Team and UAT manuals: `manual/screenshots/walkthrough.cjs` or `bench e2e run --manual-shots`.
   - Thai text requires the app's Sarabun font (`public/fonts`).
3. **UAT Guides**:
   - Generated with `bench rebuild-guide --module <Workbook>` (one step), or by hand from `bench e2e run --manual-shots` followed by `bench e2e guide`.
   - Never edit by hand.
4. **Team Manuals**:
   - Written by hand over skeletons from `bench e2e handbook --framework`.
   - Pictures synced via `bench e2e handbook --shots`.
5. **Terminology**:
   - System names (DocTypes, fields, states, roles) remain English as on screen, never translated.
   - Public guest access (`roles: ["Guest"]` in `space.json`).
   - Personal records (leave, pay) must use test employee data, never real employees.
