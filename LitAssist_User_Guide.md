# LitAssist User Guide

## Introduction

LitAssist is a comprehensive legal workflow automation tool designed for Australian legal practice. It provides a structured end-to-end pipeline for litigation support:

```
ingest → analyse → structure → brainstorm → draft
```

This guide demonstrates how to use each workflow through a running example of a family court case, *Smith v Jones*, involving a complex child custody dispute with issues of interstate relocation and allegations of parental alienation.

## Running Example: Smith v Jones

To illustrate each workflow in a practical context, we'll use a fictional family court case with the following characteristics:

**Case Overview:** Smith v Jones (Federal Circuit and Family Court of Australia, Division 1)

**Key Parties:**
- Jennifer Smith (mother, 38): Formerly resided in Sydney, recently relocated to Brisbane for a senior hospital position
- Michael Jones (father, 40): Still residing in Sydney
- Emily Jones (12) and Thomas Jones (8): Currently living with their mother in Brisbane

**Core Issues:**
1. **Complex Parenting Arrangements**: The parents previously had a consent order with a week-about arrangement when both lived in Sydney.
2. **Interstate Relocation**: Ms. Smith relocated with the children to Brisbane in January 2025, citing a career opportunity. Mr. Jones filed a contravention application in February 2025.
3. **Allegations of Parental Alienation**: Mr. Jones alleges Ms. Smith is "poisoning the children against him," while Ms. Smith claims Mr. Jones exhibits controlling behavior.

**Procedural Status:**
- Interim parenting orders issued in April 2025
- Final hearing scheduled for June 2025

This running example provides context for understanding how each LitAssist workflow contributes to managing a complex family law matter from initial research through to final submissions.

## Installation and Setup

Ensure you have Python installed, then install LitAssist and set up your configuration:

```bash
# Install dependencies
pip install -r requirements.txt

# Configure your API keys (copy from template first)
cp config.yaml.template config.yaml
# Edit config.yaml with your API keys
```

## Workflow 1: Lookup - Rapid Case-Law Search

**Pipeline Phase**: Ingest (Research)

### Purpose

The `lookup` command performs rapid searches on AustLII for relevant case law using Google Custom Search, then processes the results through Gemini to produce a structured legal answer with citations.

### Command

```bash
python -m litassist.cli lookup "your legal question" [--mode irac|broad] [--verify]
```

Options:
- `--mode`: Choose between IRAC (Issue, Rule, Application, Conclusion) or a broader exploration
- `--verify`: Enable self-critique verification pass

### Example Usage

In our *Smith v Jones* case, we might need to quickly research the legal framework for parental alienation:

```bash
python -m litassist.cli lookup "What is the legal framework for determining parental alienation in Australian family court cases?" --mode irac
```

**Output Example**:
```
Issue: What legal framework do Australian family courts use to determine cases involving parental alienation?

Rule: In Australia, parental alienation is addressed primarily through the Family Law Act 1975 (Cth), which emphasizes the best interests of the child as the paramount consideration in parenting matters. In Karabes v Karabes [2019] FamCAFC 3, the Full Court clarified that while parental alienation is not explicitly defined in the legislation, courts must consider:
1. The benefit to children of having a meaningful relationship with both parents (s60CC(2)(a))
2. The need to protect children from physical or psychological harm (s60CC(2)(b))
3. The willingness and ability of each parent to facilitate a relationship between the child and the other parent (s60CC(3)(c))

Application: When determining whether parental alienation has occurred, courts examine evidence of one parent systematically denigrating the other parent or deliberately interfering with parent-child contact without justification. In Miles & Zanelli [2022] FedCFamC1A 20, Justice Kent emphasized that courts must distinguish between legitimate protective behaviors and unjustified alienating behaviors. Evidence is typically provided through experts such as family consultants, psychiatrists, or psychologists as seen in Kappas & Drakos [2018] FamCA 37.

Conclusion: Australian family courts address parental alienation through the best interests framework of the Family Law Act. Courts apply a thorough examination of evidence regarding parental behavior and expert testimony, weighing the importance of meaningful relationships with both parents against any genuine protective concerns. Courts can order various remedies including changes to parenting arrangements, therapy interventions, or in extreme cases, changes to the child's primary residence as demonstrated in Ralton & Ralton [2016] FCWA 65.

Sources:
- Family Law Act 1975 (Cth), sections 60B, 60CC, https://www8.austlii.edu.au/cgi-bin/viewdb/au/legis/cth/consol_act/fla1975114/
- Karabes v Karabes [2019] FamCAFC 3, https://www8.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/FamCAFC/2019/3.html
- Miles & Zanelli [2022] FedCFamC1A 20, https://www8.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/FedCFamC1A/2022/20.html
- Kappas & Drakos [2018] FamCA 37, https://www8.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/FamCA/2018/37.html
- Ralton & Ralton [2016] FCWA 65, https://www8.austlii.edu.au/cgi-bin/viewdoc/au/cases/wa/FCWA/2016/65.html
```

### Next in Pipeline

After establishing the relevant legal frameworks through `lookup`, you can proceed to the `digest` workflow to analyze the case documents in detail.

## Workflow 2: Digest - Large Document Processing

**Pipeline Phase**: Analyse

### Purpose

The `digest` command processes large documents by splitting them into manageable chunks and using Claude to either summarize content chronologically or identify potential legal issues in each section.

### Command

```bash
python -m litassist.cli digest <file> [--mode summary|issues] [--verify]
```

Options:
- `--mode`: Choose between chronological summary or issue-spotting (default: summary)
- `--verify`: Enable self-critique verification pass

### Example Usage

For the *Smith v Jones* case, we have received a lengthy affidavit from our client that needs to be broken down:

```bash
python -m litassist.cli digest smith_affidavit.pdf --mode issues
```

**Output Example**:
```
--- Chunk 1 ---
Potential Legal Issues:

1. Jurisdictional Questions
   There appears to be a potential jurisdictional dispute as Ms. Smith has relocated from NSW to Queensland with the children without Mr. Jones's consent. This raises issues under Family Law Act s65DAA regarding relocation and may trigger the need for a specific "relocation order" from the court.

2. Parental Responsibility
   Ms. Smith's unilateral decision-making regarding the children's schooling and medical care potentially conflicts with the requirement for joint consultation on major long-term issues under s61DA of the Family Law Act, particularly as there seems to have been a previous parenting order establishing equal shared parental responsibility.

3. Family Violence Allegations
   Ms. Smith makes several references to "controlling behavior" and "emotional manipulation" which, while not explicitly characterized as family violence, could potentially be framed as coercive control under s4AB(2) of the Family Law Act. However, the allegations lack specific incidents and may require further particulars.

--- Chunk 2 ---
Potential Legal Issues:

4. Best Interests Considerations
   The children's expressed wishes to remain with their mother in Queensland raises consideration of s60CC(3)(a) regarding children's views, particularly for the 12-year-old child whose views may be given greater weight due to age and maturity.

5. Parental Alienation Concerns
   Mr. Jones's allegations that Ms. Smith is "poisoning the children against him" raise potential parental alienation issues. This relates to s60CC(3)(c) regarding the willingness of each parent to facilitate a relationship between the children and the other parent.
   
...
```

### Next in Pipeline

After analyzing the documents with `digest`, you need to extract key facts in a structured format using the `extractfacts` workflow.

## Workflow 3: ExtractFacts - Deterministic Fact Extraction

**Pipeline Phase**: Structure

### Purpose

The `extractfacts` command processes a document to extract relevant case facts and organizes them into a structured format with ten standard headings, providing a foundation for other commands that require structured facts.

### Command

```bash
python -m litassist.cli extractfacts <file> [--verify]
```

Options:
- `--verify`: Enable self-critique verification pass

### Example Usage

Now we need to create a structured fact sheet for the *Smith v Jones* case:

```bash
python -m litassist.cli extractfacts smith_jones_file.pdf
```

**Output Example**:
The command creates a `case_facts.txt` file with the following structured format:

```
1. Jurisdiction & Forum
Federal Circuit and Family Court of Australia, Division 1
Filed in Brisbane Registry (Queensland)
Case subject to Family Law Act 1975 (Cth)

2. Parties & Roles
Applicant: Jennifer Smith (mother, 38)
Respondent: Michael Jones (father, 40)
Children: Emily Jones (12) and Thomas Jones (8)

3. Procedural Posture
Application filed by Ms. Smith on March 15, 2025
Interim parenting orders issued on April 2, 2025
Parties participated in Family Dispute Resolution on April 30, 2025 (unsuccessful)
Matter scheduled for final hearing on June 10, 2025

4. Chronology of Key Events
2012 - Parties married in Sydney
2013 - Emily born
2017 - Thomas born
2022 - Parties separated but continued living in Sydney home
2023 - Consent parenting orders established (week-about arrangement)
January 2025 - Ms. Smith relocated with children to Brisbane (citing job opportunity)
February 2025 - Mr. Jones filed contravention application

5. Factual Background
Parties had jointly-owned property in Sydney
Ms. Smith accepted senior position in Brisbane hospital
Children enrolled in Brisbane schools since February 2025
Mr. Jones continues to reside in Sydney
Current communication between parties is minimal and strained

...
```

### Next in Pipeline

With the structured case facts in place, you can now use the `ideate` workflow to generate novel legal arguments or remedies.

## Workflow 4: Ideate - Creative Legal Strategy Generation

**Pipeline Phase**: Brainstorm

### Purpose

The `ideate` command uses Grok's creative capabilities to generate ten unorthodox litigation arguments or remedies based on the facts provided. It's particularly useful for brainstorming alternative legal approaches.

### Command

```bash
python -m litassist.cli ideate case_facts.txt [--verify]
```

Options:
- `--verify`: Enable self-critique verification pass

### Example Usage

For the *Smith v Jones* case, we can use the structured facts to generate creative legal strategies:

```bash
python -m litassist.cli ideate case_facts.txt
```

**Output Example**:
```
--- Ideas ---

Ten Unorthodox Litigation Arguments for Smith v Jones:

1. "Digital Domicile" Argument
   Assert that the children's established online relationships with friends and extended family in Sydney constitute a digital domicile that should be recognized by the court as a factor in determining their best interests. Argue that geographic relocation is less disruptive in the digital age as the children maintain their social connections through technology.

2. Educational Innovation Metric
   Commission an educational assessment comparing innovative teaching methodologies between the Brisbane and Sydney schools, arguing that the Brisbane schools offer pedagogical approaches specifically beneficial for these children's learning styles. This shifts focus from mere relocation to educational opportunity specificity.

3. "Parental Development" Framework
   Propose a novel legal framework where the court considers each parent's personal and professional development trajectory as integral to their parenting capacity. Argue that Ms. Smith's career advancement directly enhances her parenting abilities through greater financial security, professional fulfillment, and role modeling.

4. Climate Change Adaptation Defense
   Present evidence that Brisbane's climate and infrastructure are better positioned for climate resilience than Sydney, potentially offering the children a more stable future. This unusual argument connects relocation to long-term welfare considerations beyond conventional family law factors.

5. Indigenous Connection Consideration
   If either parent or the children have any Indigenous heritage, explore whether the Brisbane location offers better connection to specific Country or cultural resources that would support the children's cultural identity development under UNDROC principles.

...
```

### Next in Pipeline

Finally, using the research, analysis, structured facts, and creative ideas from previous workflows, you can create a well-supported draft using the `draft` workflow.

## Workflow 5: Draft - Retrieval-Augmented Drafting

**Pipeline Phase**: Draft

### Purpose

The `draft` command implements a Retrieval-Augmented Generation workflow to create well-supported legal drafts. The process embeds document chunks, stores them in Pinecone, retrieves relevant passages using MMR re-ranking, and generates a draft with GPT-4o that incorporates these citations.

### Command

```bash
python -m litassist.cli draft <pdf> <query> [--verify] [--diversity FLOAT]
```

Options:
- `--verify`: Enable self-critique verification pass
- `--diversity`: Control diversity of search results (0.0-1.0)

### Example Usage

For our *Smith v Jones* case, we can now draft a submission on the relocation issue:

```bash
python -m litassist.cli draft smith_bundle.pdf "outline of submissions regarding relocation of children in Smith v Jones"
```

**Output Example**:
```
# OUTLINE OF SUBMISSIONS
## SMITH v JONES (SYD2025/0123)
### ISSUE OF RELOCATION OF CHILDREN

1. INTRODUCTION

1.1 These submissions are made on behalf of the Applicant mother, Ms. Jennifer Smith, who seeks final parenting orders permitting her and the children, Emily (12) and Thomas (8), to remain in Brisbane.

1.2 The relocation occurred in January 2025 due to Ms. Smith's acceptance of a senior position at Brisbane Children's Hospital, which represents a significant career advancement and provides enhanced financial security for the children.

2. LEGAL FRAMEWORK

2.1 The paramount consideration is the best interests of the children (s60CA, Family Law Act 1975).

2.2 As noted in MRR v GR [2010] HCA 4 at [15]: "a court cannot order a person to live in a particular place. But it can, consistent with the terms of the Act, frame parenting orders in a way which could have the practical effect of requiring a parent to reside in a particular location if that parent wishes to have the child reside with or spend time with him or her."

2.3 In Morgan & Miles [2007] FamCA 1230, the Court emphasized that relocation cases are not a separate category of case but must be determined according to the same principles as all parenting cases, with the best interests of the children as the paramount consideration.

3. PRIMARY CONSIDERATIONS (s60CC(2))

3.1 Benefit to children of meaningful relationship with both parents
...

[Content continues with well-structured legal arguments incorporating citations from the document]
```

## End-to-End Pipeline Example

To demonstrate how these five workflows combine into a seamless end-to-end pipeline for the *Smith v Jones* case:

1. **Ingest (Lookup)**: Research legal frameworks for parental alienation and relocation cases in Australian family law.
   ```bash
   python -m litassist.cli lookup "What is the legal framework for determining parental alienation in Australian family court cases?"
   python -m litassist.cli lookup "What factors do Australian courts consider in relocation cases?" --mode broad
   ```

2. **Analyse (Digest)**: Process and analyze case documents to identify key issues and chronology.
   ```bash
   python -m litassist.cli digest smith_affidavit.pdf --mode issues
   python -m litassist.cli digest jones_response.pdf --mode summary
   ```

3. **Structure (ExtractFacts)**: Extract and organize case facts into a structured format.
   ```bash
   python -m litassist.cli extractfacts smith_jones_file.pdf
   ```

4. **Brainstorm (Ideate)**: Generate creative legal arguments and strategies based on case facts.
   ```bash
   python -m litassist.cli ideate case_facts.txt
   ```

5. **Draft**: Create a well-supported legal submission incorporating citations from case documents.
   ```bash
   python -m litassist.cli draft smith_bundle.pdf "outline of submissions regarding relocation of children in Smith v Jones"
   ```

## Conclusion

LitAssist streamlines legal workflows by automating research, analysis, and drafting processes. By following the end-to-end pipeline demonstrated in this guide, legal professionals can efficiently handle complex cases like *Smith v Jones* while ensuring thorough research, structured analysis, and well-supported legal arguments.

## Global Options

Options available for all commands:

```bash
python -m litassist.cli [GLOBAL OPTIONS] <command> [ARGS] [OPTIONS]
```

- `--log-format [json|markdown]` - Set audit log format (default: markdown)
- `--verbose` - Enable detailed debug logging

## Audit Logging

All command executions are logged for audit purposes:
- Logs stored in `logs/` directory
- Format: `logs/<command>_YYYYMMDD-HHMMSS.{json|md}`
- Contents include metadata, inputs, prompts, responses, and token usage

## Legal Disclaimer

All outputs from LitAssist are draft documents only and must be reviewed by qualified legal counsel before use in formal proceedings.
