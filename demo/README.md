# LitAssist Demo: TechStart v CloudCorp

## Welcome to the LitAssist Demo Case Study

This demonstration showcases LitAssist's complete litigation workflow using a realistic commercial dispute between a fintech startup and their cloud infrastructure provider.

### The Case

**TechStart Pty Ltd v CloudCorp Australia Pty Ltd**
- **Claim**: $850,000 for breach of Service Level Agreement
- **Court**: Federal Court of Australia
- **Issues**: Catastrophic 52-hour service outage causing significant business losses

### What You'll See

This demo demonstrates:
1. **Intelligent Case Planning** - How LitAssist generates executable litigation roadmaps
2. **AI-Powered Research** - Targeted legal research on breach of contract and limitation clauses
3. **Document Analysis** - Processing emails, contracts, and expert reports
4. **Strategy Development** - Both orthodox and creative legal approaches
5. **Professional Drafting** - Court-ready documents with verified citations

### How to Use This Demo

#### Option 1: Browse the Outputs
Navigate through the `outputs/` directory to see pre-generated results from each LitAssist command.

#### Option 2: Run It Yourself
If you have LitAssist installed:

```bash
# Start with the case plan
litassist caseplan demo/case_facts.txt --budget standard

# Then run the generated script
bash caseplan_commands_standard.sh
```

### Directory Structure

```
demo/
├── case_facts.txt                 # Initial client brief
├── documents/                     # Source documents
│   ├── service_agreement_excerpts.txt
│   ├── email_correspondence.txt
│   ├── expert_report_summary.txt
│   └── financial_impact.txt
└── outputs/                       # LitAssist outputs
    ├── 01_planning/              # Case planning
    ├── 02_research/              # Legal research
    ├── 03_analysis/              # Document analysis
    ├── 04_strategy/              # Strategy development
    ├── 05_drafts/                # Legal documents
    └── 06_brief/                 # Barrister's brief
```

### Key Learning Points

1. **Workflow Automation**: See how complex legal tasks are broken down into manageable steps
2. **AI Augmentation**: Understand how different AI models contribute to legal analysis
3. **Quality Control**: Notice the verification steps and human oversight built into the process
4. **Time Efficiency**: Compare traditional vs. AI-augmented workflow timelines

### For Law Students

This case demonstrates several important legal concepts:
- Service Level Agreements in commercial contracts
- Limitation of liability clauses and their exceptions
- Proving gross negligence in commercial disputes
- Calculating and claiming consequential losses
- Strategic use of urgent injunctions

### For Legal Practitioners

Consider how LitAssist could help with:
- Rapid case assessment and strategy development
- Comprehensive legal research with citation verification
- First drafts of court documents
- Organizing evidence and preparing briefs
- Maintaining consistency across large matters

### Try It Yourself

1. Review the initial `case_facts.txt` file
2. Examine the source documents in `documents/`
3. Follow the workflow through each output stage
4. Notice how each command builds on previous outputs
5. Consider how you might adapt this workflow for your own matters

### Questions?

- Documentation: [litassist.github.io](https://litassist.github.io)
- GitHub: [github.com/litassist/litassist](https://github.com/litassist/litassist)
- Email: support@litassist.io

---

*This is a fictional case study for demonstration purposes. Any resemblance to real companies or cases is purely coincidental.*