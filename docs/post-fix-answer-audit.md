# Manual audit of the post-fix 50-answer trace

I reviewed every answer in `data/eval/ragas-post-fix-routing-50.jsonl`. This is
the 2026-07-22 production run over the rebuilt 1,155-chunk index with dense
retrieval and no reranker. Mistral Small handled the control calls. NVIDIA
Nemotron wrote 39 answers, and DeepSeek V4 Pro handled 11 fallback answers. I
audited the saved trace without regenerating it.

I checked the answers against the saved gold sections, the exact text in the
rebuilt local corpus, and the official sources used in the earlier audit. Those
sources are the [India Code BNS PDF](https://www.indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf),
the [India Code BNSS record](https://www.indiacode.nic.in/handle/123456789/20099?col=123456789%2F1362&view_type=search),
the [India Code BSA record](https://www.indiacode.nic.in/indiacode/handle/123456789/20063?view_type=browse),
and the [Ministry of Home Affairs new criminal laws page](https://www.mha.gov.in/en/commoncontent/new-criminal-laws).
The online copies were last checked on 2026-07-21. This is a project evaluation,
not a legal opinion.

## Rubric

- `pass`: the central provision is right, material claims are supported, and any
  punishment stated is accurate.
- `partial`: the answer is useful but omits a needed rule, adds an unsupported
  branch, overstates uncertain facts, or ends before finishing a side point.
- `fail`: the final response gives no usable legal answer, relies on the wrong
  central rule, or states a materially wrong punishment.

I counted a deterministic refusal as a failure for usability even when refusing
was safer than returning the rejected draft. I did not penalise a supported
section merely because it was outside the hand-written gold labels.

## Result

| verdict | count | share | earlier trace |
|---|---:|---:|---:|
| pass | 31 | 62% | 28 |
| partial | 12 | 24% | 16 |
| fail | 7 | 14% | 6 |

The clean-pass rate improved from 56% to 62%, but the usable pass-or-partial rate
fell from 88% to 86%. Five of the six earlier material failures are now clean
passes: s09, s15, s22, s29, and s38. The repaired retrieval context also moved
s31 from partial to pass. The remaining earlier failure, s13, is now safely
blocked because BNS 106(2) is not in force, but the user still receives only a
generic refusal.

The stricter citation check created the main usability regression. It rejected
six drafts and returned a generic low-confidence response for s07, s12, s13,
s33, s34, and s40. Five of those rows were partial rather than failed in the old
trace. Scenario s30 is the other new failure because it gives the wrong maximum
punishment for extortion and then cuts off mid-sentence.

The error tags overlap, so their counts do not add to 50.

| error tag | affected answers | count |
|---|---|---:|
| generic validator refusal | s07, s12, s13, s33, s34, s40 | 6 |
| overconfident classification | s01, s08, s16, s18, s23, s39, s46 | 7 |
| truncated answer | s04, s30, s44 | 3 |
| unsupported extra branch | s04, s11 | 2 |
| missed specific provision | s02 | 1 |
| wrong punishment | s30 | 1 |

## Row-by-row audit

| id | verdict | tags | audit note |
|---|---|---|---|
| s01 | partial | `overconfident` | Sections 100, 101, and 103 are all present now, but the short facts do not establish intent or exclude a murder exception as firmly as the answer suggests. |
| s02 | partial | `missed_specific_provision` | Ordinary theft under section 303 is correct, but section 305 directly covers theft of a means of transport. The answer cites section 305 only for theft from a building and misses the motorcycle rule and its seven-year maximum. |
| s03 | pass | none | Section 318 correctly covers the fake-gold sale, and delivery of the money supports the subsection (4) punishment. |
| s04 | partial | `truncated`, `unsupported_branch` | Robbery under section 309 is right. The answer does not give the available robbery punishment and cuts off while discussing organised crime, which needs continuing unlawful activity and syndicate facts. |
| s05 | pass | none | Section 85 covers dowry-linked cruelty. Section 80 and the BSA section 118 presumption are clearly limited to a later dowry-death situation. |
| s06 | pass | none | Sections 63 and 64 correctly identify rape and state the ordinary punishment. |
| s07 | fail | `validator_refusal` | The saved final answer is a generic refusal after the draft mentioned unsupported BNS section 32. It does not tell the user that a threat to kill is criminal intimidation under section 351. |
| s08 | partial | `overconfident` | Criminal breach of trust under section 316 is right, but the seven-year clerk-or-servant tier depends on the accountant's employment capacity. An outside accountant acting as an agent may fall under a different subsection. |
| s09 | pass | none | The repaired context produces the right answer: the agreement to rob is criminal conspiracy under section 61, with robbery correctly identified under section 309. |
| s10 | pass | none | Section 356 covers the defamatory publication, and the answer gives the correct basic and printing-related punishments. |
| s11 | partial | `unsupported_branch` | Section 124 and both acid-related punishment branches are accurate. An acid attack on a woman does not by itself prove the separate section 74 intent to outrage modesty. |
| s12 | fail | `validator_refusal` | The saved final answer is a generic refusal after the draft mentioned unsupported BNS section 139. The response never gives the applicable ransom provision in section 140(2). |
| s13 | fail | `validator_refusal`, `uncommenced_provision` | The current-law guard correctly rejects a draft that applied uncommenced BNS 106(2). The final response is still unusable because sections 281 and 106(1) can answer the facts without subsection (2). |
| s14 | pass | none | Sections 330, 331, and 305 correctly cover night house-breaking, the theft purpose, and theft from a dwelling. The punishment ranges are accurate. |
| s15 | pass | none | The restored section 2(31) definition supports treating a property sale deed as valuable security. Sections 335, 336, and 338 are correctly applied, including the life-or-ten-year section 338 punishment. |
| s16 | partial | `overconfident` | Sections 178 and 181 correctly cover currency counterfeiting and the machinery. Organised crime under section 111 also requires the statutory continuing-activity history, not merely a gang working together. |
| s17 | pass | none | Section 80 and the BSA section 118 presumption are accurately stated for a dowry-linked death within seven years of marriage. |
| s18 | partial | `overconfident` | The answer accurately states section 78, but following becomes stalking only with the required contact or attempted contact despite disinterest. Watching a house is not enough by itself. |
| s19 | pass | none | Section 75 directly covers repeated unwanted sexual advances, and both punishment tiers are accurate. |
| s20 | pass | none | Section 77 directly covers secretly filming a woman bathing, and both conviction tiers are accurate. |
| s21 | pass | none | Section 308 expressly covers a threat to reputation used to obtain money. The basic and aggravated punishment branches are accurate. |
| s22 | pass | none | The retrieval repair works. The answer uses ordinary mischief under section 324 and gives the value-based punishment tiers without inventing fire or explosives. |
| s23 | partial | `overconfident` | The answer eventually states the required criminal-trespass intent, but it first treats locked and unauthorised entry as enough. A lock can show deliberate entry, not the separate intent to offend, intimidate, insult, or annoy. |
| s24 | pass | none | Section 109 directly covers firing with intent to kill where death does not occur, and both punishment branches are accurate. |
| s25 | pass | none | Permanent loss of sight is grievous hurt under section 116, and section 117 supplies the correct seven-year maximum plus fine. |
| s26 | pass | none | Section 137 correctly covers taking a 15-year-old from lawful guardianship without consent and gives the right punishment. |
| s27 | pass | none | Section 127 correctly covers two days of wrongful confinement and explains why the three-day aggravated tier does not apply. |
| s28 | pass | none | Sections 227 and 229 correctly cover deliberate false evidence under oath. BNSS section 383 is accurately framed as a separate summary procedure. |
| s29 | pass | none | The repaired context produces the right pairing: section 170 defines electoral bribery and section 173 supplies its punishment. |
| s30 | fail | `wrong_punishment`, `truncated` | Sections 204 and 308 identify the two offences, but the answer states a three-year maximum for completed extortion. Section 308(2) permits up to seven years. The response then cuts off. |
| s31 | pass | none | Sections 100, 101, and 105 are all present now. The answer correctly explains the sudden-fight exception and both culpable-homicide punishment branches. |
| s32 | pass | none | The BSA section 117 presumption is properly conditional, and BNS sections 86 and 108 are accurately used. |
| s33 | fail | `validator_refusal` | The saved final answer is a generic refusal after the draft mentioned unsupported section 141. It gives no trafficking or forced-labour analysis under sections 143 and 146. |
| s34 | fail | `validator_refusal` | The saved final answer is a generic refusal after the draft mentioned unsupported BNSS section 359. It gives no cheating-by-personation analysis under BNS sections 318 and 319. |
| s35 | pass | none | Sections 309 and 311 correctly cover robbery with hurt and the deadly-weapon or grievous-hurt tier. Dacoity is properly conditional on five or more offenders. |
| s36 | partial | `missing_rule` | Section 191 correctly covers rioting, but the answer assumes an unlawful assembly without explaining the qualifying common object under section 189 or common-object liability under section 190. |
| s37 | pass | none | Sections 196, 353, and 299 are accurately separated by their different intent and content requirements. |
| s38 | pass | none | The rebuilt section 314 context fixes the punishment. The answer now states the mandatory six-month minimum, two-year maximum, and fine. |
| s39 | partial | `ambiguous_facts` | Gang rape under section 70 is accurately stated as a conditional rule, but the prompt says only "assaulted." The answer does not explain that the facts must establish rape or another sexual offence first. |
| s40 | fail | `validator_refusal` | The saved final answer is a generic refusal after the draft mentioned unsupported section 85. It never gives the applicable miscarriage analysis under sections 88 and 89. |
| s41 | pass | none | Section 249 and its punishment branches are accurate, including the spouse exception. BNSS section 129 is stated conditionally. |
| s42 | pass | none | Sections 271 and 272 are accurately separated by negligent conduct versus malignant conduct. |
| s43 | pass | none | Section 238 directly covers hiding a body to screen an offender. Section 94 is clearly limited to separate child-birth concealment facts. |
| s44 | partial | `truncated` | Sections 217 and 248 correctly fit a knowingly false complaint intended to cause arrest. The answer cuts off while discussing the conditional false-evidence branch. |
| s45 | pass | none | Sections 75 and 74 both fit deliberate groping, and their punishment ranges are accurate. |
| s46 | partial | `overconfident` | The listed crimes fit section 111, but "continuing unlawful activity" also requires the statutory charge-sheet and cognizance history. The prompt does not provide it. |
| s47 | pass | none | Section 113 directly covers the terrorist act, and the death-result and no-death punishments are accurate. |
| s48 | pass | none | Section 152 covers purposeful encouragement of secession or armed rebellion. The BNSS procedural consequences are supported. |
| s49 | pass | none | Section 147 directly covers the armed attempt to overthrow the Government of India. Sections 149 and 113 are supported additional provisions. |
| s50 | pass | none | Sections 304 and 62 correctly distinguish completed snatching from attempt and give the 1.5-year attempt ceiling. Section 129 is a supported conditional addition. |

## What changed

The retrieval and parser work did what I wanted on the targeted legal mistakes.
The new answers correctly recover conspiracy, mischief, electoral bribery,
culpable homicide, valuable-security forgery, and the mandatory minimum for
misappropriating found property. Those are real answer-level improvements, not
just higher retrieval coverage.

The validator behaviour is now the main limit. Rejecting an unsupported prose
citation is safer than returning it, but production immediately turns the whole
answer into a generic refusal. Five previously useful partial answers are lost
that way. The smallest next fix is not another retriever change. It is one bounded
regeneration after citation rejection, using the same retrieved context and the
validator's exact invalid-section list. The separate generator ceiling also needs
attention because three otherwise useful answers stop mid-sentence.
