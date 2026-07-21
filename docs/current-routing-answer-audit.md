# Manual audit of the current 50-answer route

I reviewed every answer in `data/eval/ragas-current-routing-50.jsonl`. This is the
mixed-provider production run from 2026-07-18: Mistral Small handled the control
calls, NVIDIA Nemotron wrote most answers, and DeepSeek V4 Pro handled six
fallback generations. I did not regenerate any answers.

I checked each answer against the saved gold sections, the exact text in the local
1,151-chunk corpus, and the official online copies of the three statutes. I used the
[India Code BNS PDF](https://www.indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf),
the [India Code BNSS record](https://www.indiacode.nic.in/handle/123456789/20099?col=123456789%2F1362&view_type=search),
the [India Code BSA record](https://www.indiacode.nic.in/indiacode/handle/123456789/20063?view_type=browse),
and the [Ministry of Home Affairs new-criminal-laws page](https://www.mha.gov.in/en/commoncontent/new-criminal-laws).
I checked the online sources on 2026-07-21. This is a project evaluation, not a
legal opinion.

## Rubric

- `pass`: the central provision is right, the material claims are supported, and
  any punishment stated is accurate.
- `partial`: the answer is useful, but it omits a needed provision or punishment,
  adds an unsupported side claim, or states a conditional conclusion too firmly.
- `fail`: the central provision is wrong, a material punishment is wrong, or the
  answer relies on a provision that does not apply to the facts.

I treated a clearly labelled conditional provision as acceptable. I did not mark
an answer down merely because it cited a useful section outside the hand-written
gold labels. The labels are an evaluation aid, not the law.

## Result

| verdict | count | share |
|---|---:|---:|
| pass | 28 | 56% |
| partial | 16 | 32% |
| fail | 6 | 12% |

All 50 rows contain an answer, but only 28 are clean enough that I would keep them
without correction. Another 16 get the main issue mostly right but need a lawyer or
careful reviewer to repair an omission or overreach. Six contain a material legal
error.

The main error tags overlap, so their counts do not add to 50.

| error tag | affected answers | count |
|---|---|---:|
| missing needed section | s09, s15, s22, s29, s31, s36 | 6 |
| prose citation absent from structured citations | s09, s15, s22, s33, s40 | 5 |
| overconfident classification | s01, s08, s16, s46 | 4 |
| wrong punishment | s15, s29, s38 | 3 |
| missing punishment | s04, s30, s31 | 3 |
| unnecessary hypothetical branch | s01, s04, s12 | 3 |
| wrong section used as the rule | s09, s22, s29 | 3 |
| missing aggravated punishment | s33, s34 | 2 |
| unsupported extra provision | s07, s11 | 2 |
| overbroad statutory definition | s18, s36 | 2 |
| uncommenced provision presented as current law | s13 | 1 |

## Row-by-row audit

| id | verdict | tags | audit note |
|---|---|---|---|
| s01 | partial | `overconfident`, `unnecessary_hypothetical` | Sections 101 and 103 support murder and its punishment, but the facts do not rule out an exception or establish intent as firmly as the answer suggests. The attempted-murder paragraph is irrelevant because the question says the victim died. |
| s02 | pass | `benchmark_label_gap` | Section 305 specifically covers theft of a means of transport and carries the stated seven-year maximum plus fine. It is more specific than the gold label, which lists only ordinary theft under section 303. |
| s03 | pass | none | The fake-gold sale fits cheating under section 318, and delivery of money supports the higher subsection (4) punishment. |
| s04 | partial | `missing_punishment`, `unnecessary_hypothetical` | Section 309 correctly identifies robbery, but the answer declines to give the available robbery punishment. Organised crime under section 111 needs a continuing unlawful activity and syndicate facts that the question does not supply. |
| s05 | pass | none | Section 85 directly covers dowry-linked cruelty. The dowry-death and BSA presumption discussion is clearly conditional on death within seven years of marriage. |
| s06 | pass | none | Sections 63 and 64 correctly state the offence and ordinary punishment for rape on the facts supplied. |
| s07 | partial | `unsupported_provision` | Section 351 correctly covers a threat to kill. Section 232 requires an intent to make the person give false evidence; stopping a complaint is not enough by itself. |
| s08 | partial | `overconfident` | Criminal breach of trust under section 316 is right. The seven-year clerk-or-servant punishment depends on the accountant's employment capacity; an outside accountant acting as an agent may fall under subsection (5) instead. |
| s09 | fail | `wrong_section`, `missing_section`, `citation_mismatch` | The agreement to rob is criminal conspiracy under section 61. Section 60 concerns concealing a design to commit an offence, not conspiracy. Dacoity preparation also requires five or more people, which the question does not establish. |
| s10 | pass | none | Section 356 covers publication of a reputation-harming imputation and the answer gives the correct basic and printing-related punishments. |
| s11 | partial | `unsupported_provision` | Section 124 and both acid-related punishment branches are accurate. An acid attack on a woman does not automatically prove the separate section 74 intent to outrage modesty. |
| s12 | partial | `unnecessary_hypothetical` | Section 140(2) is the correct ransom provision. Section 97 concerns taking a child under ten to steal from the child and has no support in the stated facts. |
| s13 | fail | `uncommenced_provision` | Sections 281 and 106(1) are stated conditionally and accurately. The answer presents section 106(2) as current law, but the official commencement note still excludes that subsection. |
| s14 | pass | none | Sections 330, 331(2), 331(4), and 305 correctly cover night house-breaking, the theft purpose, and theft from a dwelling. The punishment ranges are accurate. |
| s15 | fail | `wrong_punishment`, `missing_section`, `citation_mismatch` | A sale deed creates or transfers legal rights and therefore fits the section 2(31) definition of valuable security. Section 338 and its life-or-ten-year punishment cannot be dismissed in favour of basic section 336. |
| s16 | partial | `overconfident` | Sections 178 and 181 correctly cover currency counterfeiting and the machinery. Calling it organised crime solely because a gang acted together skips section 111's continuing-activity and prior-charge-sheet requirements. |
| s17 | pass | none | Section 80, the section 85 cruelty offence, and the BSA section 118 presumption are accurately stated for the facts supplied. |
| s18 | partial | `overbroad_definition` | Section 78 requires repeated following plus contact or attempted contact despite disinterest, or monitoring electronic communications. Watching a house is not itself the broader physical-surveillance offence described by the answer. |
| s19 | pass | none | Section 75 directly covers unwanted sexual advances. Section 68 is correctly framed as a separate conditional offence if authority is abused to induce sexual intercourse. |
| s20 | pass | none | Section 77 directly covers capturing an image of a woman during a private act and the punishment ranges are accurate. |
| s21 | pass | none | Section 308 expressly covers threats to reputation used to obtain money. The basic and death-or-grievous-hurt punishment branches are accurate. |
| s22 | fail | `wrong_section`, `missing_section`, `citation_mismatch` | Smashing car windows is ordinary mischief under section 324. Section 326(f) applies only when fire or an explosive is used, which the question never says. |
| s23 | pass | none | The answer correctly explains that unauthorised entry becomes section 329 criminal trespass only when the required intent to offend, intimidate, insult, or annoy is present. |
| s24 | pass | none | Section 109 directly covers firing with intent to kill where death does not occur. The ordinary and hurt-caused punishment branches are accurate. |
| s25 | pass | none | Permanent loss of sight is grievous hurt under section 116, and section 117(2) supplies the stated seven-year maximum plus fine. |
| s26 | pass | none | A 15-year-old is a child under the BNS. Section 137 correctly covers taking her from lawful guardianship without consent and gives the stated punishment. |
| s27 | pass | none | The facts fit wrongful confinement under section 127. Two days does not trigger the three-day aggravated tier, and the basic punishment is accurate. |
| s28 | pass | none | Sections 227 and 229 correctly cover deliberate false evidence under oath. BNSS section 383 accurately describes the court's separate summary procedure. |
| s29 | fail | `wrong_section`, `wrong_punishment`, `missing_section` | Cash for votes is bribery under section 170, but its punishment is in section 173. Section 174 punishes undue influence or personation and cannot be substituted by calling bribery a form of undue influence. |
| s30 | partial | `missing_punishment` | Sections 204 and 308 correctly identify personating a public servant and extortion. The personation punishment is right, but the extortion punishment is missing. |
| s31 | partial | `missing_section`, `missing_punishment` | The section 101 exceptions are accurately explained. The retrieved context omitted sections 100 and 105, so the answer could not state the offence definition and punishment for culpable homicide not amounting to murder. |
| s32 | pass | none | The BSA section 117 presumption is properly conditional on suicide within seven years of marriage and cruelty by the husband or relatives. Sections 86 and 108 are accurately used. |
| s33 | partial | `missing_aggravated_punishment`, `citation_mismatch` | Sections 143 and 146 correctly cover trafficking for forced labour and compulsory labour. The question is plural, so sections 143(3) or 143(5) may supply higher punishment than the single-person and single-child tiers quoted. Sections 87 and 96 also appear only in the prose. |
| s34 | partial | `missing_aggravated_punishment` | Section 319 correctly covers cheating by personation. Because the deception caused transfer of money, section 318(4)'s seven-year maximum and mandatory fine also matter; the answer mentions only the lower section 318 tiers. |
| s35 | pass | none | Sections 309 and 311 correctly cover robbery with violence and grievous hurt. Dacoity is properly made conditional on five or more offenders. |
| s36 | partial | `overbroad_definition`, `missing_section` | Rioting under section 191 is correct because the mob attacked shops. An unlawful assembly is not defined merely by an object to disturb public peace; section 189 lists the required common objects, while section 190 supplies common-object liability. |
| s37 | pass | none | Section 196 directly covers deliberate promotion of religious hatred. Sections 353 and 299 are stated as fact-dependent alternatives rather than automatic offences. |
| s38 | fail | `wrong_punishment` | Section 314 is the right offence, but the punishment is not "up to two years, or fine, or both." The enacted text requires at least six months, permits up to two years, and also requires a fine. |
| s39 | partial | `ambiguous_facts` | The answer sensibly distinguishes gang rape from a non-rape sexual assault. The word "assaulted" does not establish that the attack was sexual, so ordinary hurt or assault remains unaddressed. |
| s40 | partial | `citation_mismatch` | Sections 88, 89, and 92 are stated with appropriate factual conditions. Section 85 appears in the prose but not in the structured citation list checked by the validator. |
| s41 | pass | none | Section 249 and its punishment branches are accurately stated, including the spouse exception. |
| s42 | pass | none | Sections 271 and 272 are accurately separated by negligent or unlawful conduct versus malignant conduct. |
| s43 | pass | none | Section 238 correctly covers disposal of evidence to screen an offender. Section 94 is clearly limited to the separate child-birth concealment facts. |
| s44 | pass | none | Sections 248 and 217 directly fit a knowingly false complaint intended to cause arrest. Section 228 is correctly left conditional on fabricated evidence. |
| s45 | pass | none | Groping supports both section 75 sexual harassment and section 74 criminal force with intent to outrage modesty. The punishment ranges are accurate. |
| s46 | partial | `overconfident` | The listed crimes are among section 111's examples, but "continuing unlawful activity" also requires more than one qualifying charge-sheet and court cognizance within ten years. The question does not supply that procedural history. |
| s47 | pass | none | The facts fit section 113's terrorist-act definition and the answer correctly separates the death-result and no-death punishments. |
| s48 | pass | none | Section 152 directly covers purposeful or knowing encouragement of secession or armed rebellion. BNSS section 98 is a supported procedural consequence. |
| s49 | pass | none | Section 147 directly covers an armed attempt to overthrow the Government of India. Sections 149 and 113 are supported as additional preparation and terrorist-act provisions on the stated facts. |
| s50 | pass | none | Sections 304 and 62 correctly distinguish completed snatching from attempt, and one-half of the three-year maximum gives the stated 1.5-year ceiling. |

## What I learned from the audit

The retrieval and answer problems are now easier to separate. The clean failures
in s09, s22, and s31 come from missing the needed provision in the 12-chunk answer
context. The failures in s15, s29, and s38 are generation or legal-reasoning errors:
the needed law was known or cited, but the answer chose the wrong punishment or
classification.

The citation validator also has a blind spot. It checks the structured `citations`
array, but the prose can still name another section. I found this in s09, s15, s22,
s33, and s40. Every saved row has structured citations, but that does not mean every
section number written in the answer was checked.

One gold label also needs correction. Scenario s02 labels only ordinary theft under
section 303, while the question describes theft of a motorcycle. Section 305 is the
more specific enacted provision for theft of a means of transport, and the model's
use of it was correct.

The current route is useful as a research demo, but a 56% clean-pass rate is not
enough for unsupervised legal answers. The next change should target the prose-citation
blind spot and the small group of punishment errors before adding another agent loop.

## Fix status

I fixed the prose-citation blind spot on 2026-07-21. The deterministic validator now
extracts section references from the answer text and rejects any that are missing from
the structured citation list. Running that parser over this frozen trace caught s09,
s15, s22, s33, and s40, which matches the manual audit. I did not regenerate answers.

I also added a current-law guard for s13. India Code still records BNS 106(2) as
excluded from commencement. The generator now receives that note with section 106,
and the deterministic validator rejects an answer that still applies subsection (2).

Tracing s15 found an earlier ingestion fault. A PDF footnote truncated BNS section 2
after definition (4), so definition 2(31) for valuable security never entered the old
1,151-chunk corpus. The parser now removes repeated section matches before setting
body boundaries. The rebuilt local index has 1,155 chunks and includes definition
2(31). The audit result above remains the score for the saved pre-fix answers.

The rebuilt route also adds bounded doctrine hints and fills missing sibling chunks.
On the frozen 50 scenarios, full-generation-window section recall rose from 0.900 to
0.970 with `BAAI/bge-large-en-v1.5`, dense retrieval, and no reranker. The repaired
contexts now include BNS 61 for s09, BNS 324 for s22, BNS 173 for s29, BNS 100 and
105 for s31, definition 2(31) for s15, and the punishment chunk of BNS 314 for s38.
