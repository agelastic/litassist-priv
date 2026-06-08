#!/usr/bin/env bash
#
# Tier 2 - matter-type behavioural spot-check (REAL API CALLS, COSTS MONEY).
#
# Purpose
#   Phase 1 unit tests prove the disciplinary posture REACHES each framing
#   command's system message (offline, free). They cannot prove it CHANGES the
#   generated text. This script does the only thing that can: it runs the real
#   commands on a disciplinary matter and on an identical civil control, then
#   helps you eyeball whether the framing actually shifts.
#
#   The control is scientific: the disciplinary and civil fixtures are byte-for-
#   byte identical EXCEPT the one "Matter type:" line, so any difference in the
#   outputs is attributable to the posture and nothing else.
#
# What to look for (the human verdict, not the script's)
#   disciplinary outputs : should frame for the Legal Services Commissioner /
#                          regulator - a complaint or submission, NOT a court
#                          filing. The original assessment failures were
#                          barbrief inventing a Supreme Court listing and
#                          counselnotes using a court register; those must be
#                          gone here.
#   civil outputs        : your no-regression baseline - should look like
#                          today's ordinary litigation output.
#   absent matter type   : must print the LOUD "assuming 'civil' (litigation)
#                          posture" warning and still produce civil output.
#
# The signal-scan printed after each run (regulator-signals vs court-signals) is
# a CRUDE HEURISTIC to point your eye, never a pass/fail verdict. Read the files.
#
# Usage
#   Run from the repo root (needs config.yaml + the `litassist` CLI on PATH):
#     ./test-scripts/test_matter_type_spotcheck.sh           # default matrix (7 command runs)
#     ./test-scripts/test_matter_type_spotcheck.sh -q        # quick (3 command runs: strategy + warning)
#     ./test-scripts/test_matter_type_spotcheck.sh -a        # all framing commands (11 command runs)
#     ./test-scripts/test_matter_type_spotcheck.sh -y        # skip the cost confirmation
#
# Cost
#   These commands are slow (several minutes each). The counts above are COMMAND
#   INVOCATIONS, not LLM calls. Most commands fan out to SEVERAL paid LLM calls
#   internally: brainstorm = orthodox + unorthodox + analysis + a verification
#   pass (~4-5 calls); strategy = generation + content verification + next-steps
#   + citation validation; barbrief auto-runs content verification inside
#   complete(). On top of that, each complete() may add its own citation-check
#   work, and
#   citation checks make paid Google CSE calls. So the true paid-call count is
#   well above the command count - the full matrix is 20+ LLM calls plus citation
#   lookups. Budget for that, not for the command count.

set -uo pipefail   # NOT -e: a slow/failed command must not abort the whole run.

# --- ANSI helpers (match the repo's existing scripts) -----------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
hdr()  { echo -e "\n${BLUE}=== $1 ===${NC}"; }
ok()   { echo -e "${GREEN}$1${NC}"; }
warn() { echo -e "${YELLOW}$1${NC}"; }
err()  { echo -e "${RED}$1${NC}"; }

# --- options ----------------------------------------------------------------
MODE="default"   # quick | default | all
ASSUME_YES=0
while getopts "qaych" opt; do
  case "$opt" in
    q) MODE="quick" ;;
    a) MODE="all" ;;
    y) ASSUME_YES=1 ;;
    h|*) sed -n '2,40p' "$0"; exit 0 ;;
  esac
done

# --- preconditions ----------------------------------------------------------
if [[ ! -f config.yaml ]]; then
  err "config.yaml not found in $(pwd). Run this from the repo root."
  exit 1
fi
if ! command -v litassist >/dev/null 2>&1; then
  err "litassist not on PATH. Install it (pipx install -e .) and retry."
  exit 1
fi

TS=$(date +%Y%m%d_%H%M%S)
WORK="test-scripts/spotcheck_matter_type_${TS}"
mkdir -p "$WORK"

# --- fixtures: identical except the one Matter type line --------------------
# Disciplinary fixture (mirrors the OLSC/costs assessment matter).
cat > "$WORK/facts_disciplinary.md" <<'EOF'
# Matter Extraction

## 1. Parties:
Complainant (former client) v former solicitor / law practice

## 2. Background:
A combined fee and conduct complaint against a former solicitor arising from a
costs dispute over work done in an earlier civil matter.

## 3. Key Events:
A complaint was lodged with the Legal Services Commissioner alleging overcharging
and unsatisfactory professional conduct.

## 4. Legal Issues:
Whether the practitioner engaged in unsatisfactory professional conduct; whether
the costs charged were fair and reasonable.

## 5. Evidence Available:
Tax invoices, the costs agreement, file notes and email correspondence.

## 6. Opposing Arguments:
The practitioner denies any wrongdoing and says the costs were properly incurred.

## 7. Procedural History:
No court proceedings on foot; the matter is before the regulator.

## 8. Jurisdiction:
Matter type: disciplinary
NSW Office of the Legal Services Commissioner

## 9. Applicable Law:
Legal Profession Uniform Law (NSW)

## 10. Client Objectives:
A refund of overcharged costs and a finding of unsatisfactory professional conduct.
EOF

# Civil control = the SAME file with the one line swapped (no other change).
sed 's/^Matter type: disciplinary$/Matter type: civil/' \
    "$WORK/facts_disciplinary.md" > "$WORK/facts_civil.md"

# Absent control = the SAME file with the Matter type line removed entirely.
sed '/^Matter type: disciplinary$/d' \
    "$WORK/facts_disciplinary.md" > "$WORK/facts_absent.md"

DISC="$WORK/facts_disciplinary.md"
CIVIL="$WORK/facts_civil.md"
NONE="$WORK/facts_absent.md"
OUTCOME="Obtain a refund of overcharged costs and a conduct finding"

# --- signal lexicons (heuristic only) ---------------------------------------
# Forum tells. Deliberately exclude bare 'plaintiff/defendant/register' (too noisy)
# and keep the litigation-forum signatures that the assessment actually saw misfire.
REGULATOR_RE='Commissioner|OLSC|QLSC|regulator|unsatisfactory professional conduct|professional misconduct|Legal Profession Uniform Law|LPUL|disciplinary complaint'
COURT_RE='Supreme Court|District Court|Federal Court|Statement of Claim|originating process|pleadings?|interlocutory|affidavit of service|court listing'

scan_file() {
  local f="$1" tag="$2" reg court
  [[ -f "$f" ]] || return 0
  reg=$(grep -ioE "$REGULATOR_RE" "$f" 2>/dev/null | wc -l | tr -d ' ')
  court=$(grep -ioE "$COURT_RE" "$f" 2>/dev/null | wc -l | tr -d ' ')
  echo "      scan ${f##*/} : regulator-signals=${reg}  court-signals=${court}"
  if [[ "$tag" == "disciplinary" && "$court" -gt "$reg" ]]; then
    warn "      HINT: court-signal heavy for a disciplinary matter - eyeball this file."
  fi
}

# Run one command, capture stdout, find files it newly wrote to outputs/, scan them.
run_cmd() {
  local label="$1" tag="$2"; shift 2
  hdr "$label  (matter=$tag)"
  echo "\$ $*"
  local before after rc
  before=$(ls -1 outputs 2>/dev/null | sort || true)
  "$@" 2>&1 | tee "$WORK/${label}.stdout.log"
  rc=${PIPESTATUS[0]}
  after=$(ls -1 outputs 2>/dev/null | sort || true)
  if (( rc != 0 )); then
    err "  command exited $rc (see $WORK/${label}.stdout.log)"
    return 0
  fi
  ok "  command ok"
  local newfiles
  newfiles=$(comm -13 <(echo "$before") <(echo "$after"))
  if [[ -z "$newfiles" ]]; then
    warn "  no new file in outputs/ (command may echo to console only - check the .stdout.log)"
    scan_file "$WORK/${label}.stdout.log" "$tag"
  else
    while IFS= read -r nf; do
      [[ -n "$nf" ]] && scan_file "outputs/$nf" "$tag"
    done <<< "$newfiles"
  fi
}

# --- cost gate --------------------------------------------------------------
case "$MODE" in
  quick)   N_CMDS=3 ;;
  default) N_CMDS=7 ;;
  all)     N_CMDS=11 ;;
esac
print_header() {
  echo -e "${BLUE}============================================================${NC}"
  echo -e "${BLUE}  Tier 2 matter-type spot-check  (mode=${MODE}, ${N_CMDS} command runs)${NC}"
  echo -e "${BLUE}  Fixtures + logs: ${WORK}${NC}"
  echo -e "${BLUE}============================================================${NC}"
}
print_header
warn "This makes REAL, PAID LLM calls and each command takes several minutes."
warn "Each of the ${N_CMDS} command runs fans out to SEVERAL LLM calls internally"
warn "(brainstorm alone = orthodox + unorthodox + analysis + a verification pass)"
warn "plus paid Google CSE citation checks - so the true paid-call count is well"
warn "above ${N_CMDS}; the full matrix is 20+ LLM calls. Budget for that."
if (( ! ASSUME_YES )); then
  read -r -p "Type RUN to proceed: " confirm
  [[ "$confirm" == "RUN" ]] || { echo "Aborted."; exit 0; }
fi

# --- the matrix -------------------------------------------------------------
# strategy: sharpest, cheapest contrast - always run (disciplinary + civil).
run_cmd "strategy-disciplinary" disciplinary \
  litassist strategy "$DISC" --outcome "$OUTCOME"
run_cmd "strategy-civil" civil \
  litassist strategy "$CIVIL" --outcome "$OUTCOME"

# absent matter type: must warn and default to civil. Always run.
hdr "absent-matter-type warning check  (matter=absent)"
echo "\$ litassist strategy $NONE --outcome ..."
litassist strategy "$NONE" --outcome "$OUTCOME" 2>&1 | tee "$WORK/strategy-absent.stdout.log"
absent_rc=${PIPESTATUS[0]}
if (( absent_rc != 0 )); then
  err "  INCONCLUSIVE: strategy exited $absent_rc before the warning could be checked"
  err "  (see $WORK/strategy-absent.stdout.log) - a nonzero exit can suppress the"
  err "  warning, so a missing warning here does not prove the path is broken."
elif grep -qiF "assuming 'civil'" "$WORK/strategy-absent.stdout.log"; then
  ok "  PASS: default-civil warning fired."
else
  err "  FAIL: expected \"assuming 'civil'\" warning not found - the warn-on-absent path is broken."
fi

if [[ "$MODE" != "quick" ]]; then
  # barbrief: original failure was an invented Supreme Court listing.
  run_cmd "barbrief-disciplinary" disciplinary \
    litassist barbrief "$DISC" --hearing-type directions
  run_cmd "barbrief-civil" civil \
    litassist barbrief "$CIVIL" --hearing-type directions

  # counselnotes: original failure was a court register; flag path (no case_facts arg).
  run_cmd "counselnotes-disciplinary" disciplinary \
    litassist counselnotes "$DISC" --matter-type disciplinary
  run_cmd "counselnotes-civil" civil \
    litassist counselnotes "$CIVIL" --matter-type civil
fi

if [[ "$MODE" == "all" ]]; then
  # brainstorm: 3 generators; also exercises the new --side complainant value.
  run_cmd "brainstorm-disciplinary" disciplinary \
    litassist brainstorm --facts "$DISC" --side complainant --area administrative
  run_cmd "brainstorm-civil" civil \
    litassist brainstorm --facts "$CIVIL" --side complainant --area administrative

  # caseplan full plan: the complaint-drafting deliverable phase should culminate
  # in a regulator submission for a disciplinary matter, not an advice memo.
  run_cmd "caseplan-disciplinary" disciplinary \
    litassist caseplan "$DISC" --budget standard
  run_cmd "caseplan-civil" civil \
    litassist caseplan "$CIVIL" --budget standard
fi

# --- wrap-up ----------------------------------------------------------------
hdr "MANUAL REVIEW REQUIRED"
cat <<EOF
Fixtures and per-command stdout logs: ${WORK}/
Generated documents: outputs/  (new files this run are listed above per command).

Open the disciplinary vs civil pair for each command side by side. The script's
signal counts only point your eye; the verdict is yours:
  - disciplinary: framed for the Commissioner / regulator, no court listing,
    no court register, remedies are regulator remedies (refund + conduct finding).
  - civil: unchanged from today's litigation output (your no-regression check).
  - absent: the warning fired above and the output matches civil.
EOF
