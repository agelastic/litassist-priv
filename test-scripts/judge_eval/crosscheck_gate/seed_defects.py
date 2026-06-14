"""Reproducible seeder for the P1-12 cross-check gate variants.

Regenerates test-scripts/judge_eval/crosscheck_gate/variants/*.variant.md from the
frozen ../cases/*.output.md benchmark outputs by applying the documented defects
below. Each entry is one seeded defect: (variant_file, defect_id, class, old, new),
matching manifest.yaml. Classes: confab=confabulated citation; wrongprop=real cite
for a wrong proposition; jurisdiction=wrong-jurisdiction statute/court;
contradiction=internal inconsistency; fabricated=fact not in sources. Each `old`
must match exactly once; the script asserts that. Run from anywhere:
    python test-scripts/judge_eval/crosscheck_gate/seed_defects.py
"""
import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(_DIR, "..", "cases")
VARIANTS = os.path.join(_DIR, "variants")

DEFECTS = [
    # ---------------- draft_harper ----------------
    ("draft_harper.variant.md", "D1", "jurisdiction",
     "The alleged breach of that duty is to be assessed under the Civil Liability Act 2002 (NSW), including s 5B.",
     "The alleged breach of that duty is to be assessed under the Wrongs Act 1958 (Vic), including s 48."),
    ("draft_harper.variant.md", "D2", "confab",
     "because the harm resulted from a latent equipment defect known, or which ought to have been known, to you.",
     "because the harm resulted from a latent equipment defect known, or which ought to have been known, to you. This precise scenario was considered in Henderson v Wollongong Leisure Pty Ltd [2019] NSWCA 211, where the Court of Appeal held a commercial operator liable for a corroded fixing on an elevated attraction."),
    ("draft_harper.variant.md", "D3", "wrongprop",
     "subject to the Civil Liability Act 2002 (NSW) Part 2, including s 16 – [TO BE QUANTIFIED];",
     "subject to the Civil Liability Act 2002 (NSW) Part 2, including s 16; the appropriate measure of such non-economic loss is governed by March v Stramare (E & MH) Pty Ltd (1991) 171 CLR 506 – [TO BE QUANTIFIED];"),
    ("draft_harper.variant.md", "D4", "fabricated",
     "Future treatment and rehabilitation expenses – [TO BE QUANTIFIED following medical evidence];",
     "Future treatment and rehabilitation expenses – our client's treating orthopaedic surgeon, Dr Helena Voss, has certified that she will require a second corrective procedure in early 2027 at an estimated cost of AU$48,000;"),
    ("draft_harper.variant.md", "D5", "contradiction",
     "Quantum is limited to known expenses ($14,800) with placeholders for unverified amounts.",
     "Quantum is limited to known expenses ($26,500) with placeholders for unverified amounts."),

    # ---------------- strategy_harper ----------------
    ("strategy_harper.variant.md", "S1", "confab",
     "characterisation of the specific risk is fact-sensitive).",
     "characterisation of the specific risk is fact-sensitive); see also Thompson v Blue Mountains Adventure Co [2018] NSWSC 1442 (corroded fixing on elevated attraction not an obvious risk)."),
    ("strategy_harper.variant.md", "S2", "wrongprop",
     "2. (Factual) Whether the waiver was sufficiently brought to Ms Harper's attention (ticket case principles) — *Oceanic Sun Line Special Shipping Co Inc v Fay* (1988) 165 CLR 197.",
     "2. (Factual) Whether the waiver was sufficiently brought to Ms Harper's attention (ticket case principles) — *Oceanic Sun Line Special Shipping Co Inc v Fay* (1988) 165 CLR 197, which establishes that s 5L does not apply to commercial operators of recreational facilities."),
    ("strategy_harper.variant.md", "S3", "jurisdiction",
     "Pre-filing preliminary discovery under r 5.3 *Uniform Civil Procedure Rules 2005* (NSW) requires demonstration",
     "Pre-filing preliminary discovery under r 5.3 *County Court Civil Procedure Rules 2018* (Vic) requires demonstration"),
    ("strategy_harper.variant.md", "S4", "contradiction",
     "in which case the primary limitation period would expire on 22/02/2029.",
     "in which case the primary limitation period would expire on 22/02/2028."),
    ("strategy_harper.variant.md", "S5", "fabricated",
     "Defendant has already denied liability in writing (18/03/2026), signalling appetite for litigation rather than early settlement.",
     "Defendant has already denied liability in writing (18/03/2026); however, the defendant's insurer, Allianz Australia, has confidentially reserved $750,000 for this claim, signalling appetite for litigation rather than early settlement."),

    # ---------------- lookup_harper ----------------
    ("lookup_harper.variant.md", "L1", "confab",
     "A reasonable participant is entitled to assume that the safety infrastructure provided by the commercial operator has been properly maintained and is structurally sound.",
     "A reasonable participant is entitled to assume that the safety infrastructure provided by the commercial operator has been properly maintained and is structurally sound (Spencer v Treetops Adventure Pty Ltd [2021] NSWCA 88)."),
    ("lookup_harper.variant.md", "L2", "wrongprop",
     "A \"dangerous recreational activity\" is defined under section 5K as a recreational activity that involves a \"significant risk of physical harm\".",
     "A \"dangerous recreational activity\" is defined under section 5K as a recreational activity that involves a \"significant risk of physical harm\", as authoritatively settled in Wyong Shire Council v Shirt (1980) 146 CLR 40."),
    ("lookup_harper.variant.md", "L3", "jurisdiction",
     "the operator is not negligent in failing to take precautions against a risk of harm unless the risk was foreseeable",
     "under section 48 of the Wrongs Act 1958 (Vic), the operator is not negligent in failing to take precautions against a risk of harm unless the risk was foreseeable"),
    ("lookup_harper.variant.md", "L4", "contradiction",
     "the operator cannot rely on the \"obvious risk\" defence under section 5L. The structural failure of a guardrail is not an obvious risk to a reasonable participant.",
     "the operator can rely on the \"obvious risk\" defence under section 5L, and the structural failure of a guardrail is an obvious risk that defeats the claim."),
    ("lookup_harper.variant.md", "L5", "fabricated",
     "If the guardrail failure was the result of egregious neglect or a total absence of inspections, the operator's conduct might cross the threshold into reckless conduct",
     "The plaintiff's medical reports confirm a permanent 18% whole-person impairment. If the guardrail failure was the result of egregious neglect or a total absence of inspections, the operator's conduct might cross the threshold into reckless conduct"),

    # ---------------- extractfacts_harper ----------------
    ("extractfacts_harper.variant.md", "E1", "confab",
     "The defendant subsequently denied liability by letter, relying on the signed waiver and statutory provisions relating to obvious risk and recreational activities under the *Civil Liability Act 2002* (NSW).",
     "The defendant subsequently denied liability by letter, relying on the signed waiver and statutory provisions relating to obvious risk and recreational activities under the *Civil Liability Act 2002* (NSW); the closest authority on comparable facts is *Riverside Gorge Tours Pty Ltd v Nguyen* [2017] NSWCA 305."),
    ("extractfacts_harper.variant.md", "E2", "wrongprop",
     "the relevant provision is generally *Limitation Act 1969* (NSW) s 50C, which refers to three years from the date of discoverability",
     "the relevant provision is generally *Limitation Act 1969* (NSW) s 50C, which refers to three years from the date of discoverability, the leading authority for which is *Australian Safeway Stores Pty Ltd v Zaluzna* (1987) 162 CLR 479"),
    ("extractfacts_harper.variant.md", "E3", "jurisdiction",
     "New South Wales has the **Local Court of New South Wales**, not a Magistrates' Court for civil personal injury jurisdiction.",
     "New South Wales has the **Magistrates' Court of Victoria**, not a Local Court, for civil personal injury jurisdiction."),
    ("extractfacts_harper.variant.md", "E4", "contradiction",
     "| **Ms Eleanor Harper** | Prospective plaintiff / Client | Born 1989; occupation: schoolteacher; resident of Penrith NSW; sustained personal injury on 22/02/2026 |",
     "| **Ms Eleanor Harper** | Prospective plaintiff / Client | Born 1989; aged 28 at the date of the incident; occupation: schoolteacher; resident of Penrith NSW; sustained personal injury on 22/02/2026 |"),
    ("extractfacts_harper.variant.md", "E5", "fabricated",
     "A park employee (Mr Daniel Okafor) reportedly made a statement to her at the scene indicating that the relevant section \"was meant to be re-rigged last month,\" suggesting possible known deferred maintenance.",
     "A park employee (Mr Daniel Okafor) reportedly made a statement to her at the scene indicating that the relevant section \"was meant to be re-rigged last month,\" suggesting possible known deferred maintenance. Mr Okafor has since provided a signed witness statement dated 5 May 2026 confirming the park ignored three prior written maintenance warnings.")
]


def main():
    by_file = {}
    for entry in DEFECTS:
        by_file.setdefault(entry[0], []).append(entry)
    os.makedirs(VARIANTS, exist_ok=True)
    for fname, entries in by_file.items():
        case = os.path.join(CASES, fname.replace(".variant.md", ".output.md"))
        with open(case, encoding="utf-8") as f:
            text = f.read()
        for _f, did, _cls, old, new in entries:
            if text.count(old) != 1:
                print(f"ABORT {did}: expected 1 match for old in {fname}, got {text.count(old)}")
                sys.exit(1)
            text = text.replace(old, new)
        out = os.path.join(VARIANTS, fname)
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"{fname}: seeded {len(entries)} defects")


if __name__ == "__main__":
    main()
