# Manual audit of the final repair trace

I reviewed every answer in `data/eval/ragas-final-repair-50.jsonl`. This run used
the frozen `s01-s50` scenarios, the 1,155-chunk index, dense retrieval, no
reranker, and the production graph with one bounded citation repair. I audited
the saved file without regenerating any answer.

The run started at `2026-07-22T05:23:13Z` and ended at `05:31:07Z`. Mistral
Small made 56 successful calls: 50 router calls and six repair calls. NVIDIA
Nemotron 3 Ultra made 45 successful answer calls and returned five 503 errors.
Paid DeepSeek V4 Pro handled those five fallbacks. The provider logs recorded
76,572 Mistral input tokens and 1,971 output tokens, 255,227 successful NVIDIA
input tokens and 13,174 output tokens, and 26,139 DeepSeek input tokens and
2,460 output tokens.

## Rubric

- `pass`: the central provision is right, material claims are supported, and any
  punishment stated is accurate.
- `partial`: the answer is useful but omits a needed rule, adds an unsupported
  branch, overstates uncertain facts, or cuts off after answering the main point.
- `fail`: the final response gives no useful legal answer, misses the central
  rule, or states a materially wrong punishment.

I count a deterministic refusal as a usability failure even when it safely
blocks the rejected draft. I do not penalise a supported section just because it
falls outside the hand-written gold labels.

## Result

| verdict | count | share | previous post-fix trace |
|---|---:|---:|---:|
| pass | 35 | 70% | 31 |
| partial | 13 | 26% | 12 |
| fail | 2 | 4% | 7 |

The clean-pass rate rose from 62% to 70%. The usable pass-or-partial rate rose
from 86% to 96%. Six drafts entered citation repair. Five passed deterministic
validation after repair: s13, s30, s33, s39, and s45. Scenario s14 failed its
second validation and returned low confidence.

Validation success does not prove answer quality. The repaired s30 answer still
fails this audit because it misses public-servant personation under BNS 204 and
does not state the extortion punishment. The repair worked cleanly for s13, s33,
and s45. Scenario s39 is useful but partial because the prompt does not say that
the group assault was rape.

## Row-by-row audit

| id | verdict | tags | audit note |
|---|---|---|---|
| s01 | pass | none | Sections 101 and 103 correctly explain murder and its punishment. Section 100 is framed as the alternative if a murder exception applies. |
| s02 | partial | `incomplete_punishment` | Section 305 correctly captures theft of a means of transport, fixing the earlier miss. The answer says it carries a higher maximum but never states the seven-year maximum, then mentions the ordinary-theft community-service proviso without clearly separating it from section 305. |
| s03 | pass | none | Section 318 correctly covers the fake-gold sale and the seven-year property-delivery branch. |
| s04 | partial | `missing_punishment`, `unsupported_branch` | Robbery under section 309 is right, but the answer says its punishment is unavailable and adds organised crime without facts showing continuing unlawful activity. |
| s05 | pass | none | Section 85 covers the current dowry-linked cruelty. Section 80 and BSA 118 are clearly limited to a later dowry-death situation. |
| s06 | pass | none | Sections 63 and 64 correctly identify rape and state the ordinary punishment. |
| s07 | partial | `wrong_extra_rule` | Section 351 and the aggravated death-threat punishment are right. The answer overextends section 232 from threats intended to procure false evidence to stopping a legal complaint. |
| s08 | partial | `overconfident` | Criminal breach of trust under section 316 is right, but the seven-year clerk-or-servant tier depends on the accountant's employment capacity. |
| s09 | pass | none | Section 61 correctly covers the agreement to rob, with section 309 supplying the planned offence. |
| s10 | pass | none | Section 356 correctly covers publication of defamatory material and its printing branch. The BNSS compounding point is supported. |
| s11 | partial | `unsupported_branch` | Section 124 and both acid-related punishment branches are accurate. The facts do not by themselves establish the separate section 74 intent to outrage modesty. |
| s12 | pass | none | Section 140(2) correctly identifies kidnapping for ransom and states death or life imprisonment plus fine. |
| s13 | pass | `repaired` | The repair removes uncommenced BNS 106(2) and correctly keeps rash driving under section 281 and causing death by negligence under section 106(1). |
| s14 | fail | `validator_refusal` | The first draft cited BNS 303(1), and the repair still cited BNS 303. The final answer is a generic refusal instead of the applicable house-breaking analysis under sections 330 and 331. |
| s15 | pass | none | Sections 335, 336, and 338 correctly cover the false signature, forgery, and valuable-security punishment. |
| s16 | partial | `truncated`, `overconfident` | Sections 178 and 181 correctly cover currency counterfeiting and its machinery. The organised-crime branch assumes facts not supplied and cuts off before finishing its fine. |
| s17 | pass | none | Section 80 and BSA 118 are accurately stated for a dowry-linked death within seven years of marriage. Section 85 is a supported additional offence. |
| s18 | partial | `overconfident` | The answer accurately states section 78, but the prompt does not say the following continued after a clear indication of disinterest. The trespass branch is properly conditional. |
| s19 | pass | none | Section 75 directly covers repeated unwanted sexual advances. Section 68 is clearly limited to abuse of authority to induce intercourse. |
| s20 | pass | none | Section 77 directly covers secretly filming a woman bathing, and both conviction tiers are accurate. |
| s21 | pass | none | Section 308 covers a threat to reputation used to obtain money, and the basic and aggravated branches are accurate. |
| s22 | pass | none | Section 324 correctly covers deliberate damage to the car and gives the value-based punishment tiers. |
| s23 | partial | `missing_intent` | Section 329 and its punishments are accurate, but unauthorised entry alone does not prove the required intent to offend, intimidate, insult, annoy, or commit an offence. |
| s24 | pass | none | Section 109 directly covers firing with intent to kill where death does not occur, and both punishment branches are accurate. |
| s25 | pass | none | Permanent loss of sight is grievous hurt under section 116, and section 117 gives the correct seven-year maximum plus fine. |
| s26 | pass | none | Section 137 correctly covers taking a 15-year-old from lawful guardianship. Section 87 is properly conditional on marriage or sexual intent. |
| s27 | pass | none | Section 127 correctly covers two days of wrongful confinement and explains why the three-day tier does not apply. |
| s28 | pass | none | Sections 227 and 229 correctly cover deliberate false evidence under oath. BNSS 383 is accurately framed as a separate summary procedure. |
| s29 | pass | none | Section 170 defines electoral bribery and section 173 supplies the correct punishment. |
| s30 | fail | `repaired`, `missed_central_rule`, `missing_punishment` | The repair removes fabricated BNS 217 but misses personating a public servant under section 204. Cheating by personation and extortion may apply, but the answer does not state the extortion maximum and never answers the central public-servant rule. |
| s31 | partial | `incomplete_rule` | The sudden-fight exception and section 105 are relevant, but the answer chooses the knowledge-only punishment branch without enough facts and omits the alternative branch where intent is proved. |
| s32 | pass | none | The BSA 117 presumption is conditional, and BNS sections 86 and 108 are accurately used. |
| s33 | pass | `repaired` | The repair removes fabricated section 141 and gives an accurate section 143 trafficking analysis, including the multiple-person punishment. |
| s34 | pass | none | Sections 319 and 318 correctly cover bank personation and dishonest inducement to transfer money. |
| s35 | pass | none | Sections 309 and 311 correctly cover robbery with hurt and the grievous-hurt tier. |
| s36 | pass | none | Sections 189 and 191 correctly explain the unlawful common object, rioting, and the armed-rioting punishment. |
| s37 | partial | `truncated` | Section 196 and its punishment correctly cover inciting religious hatred. The answer cuts off while explaining an extra section 299 branch. |
| s38 | pass | none | Section 314 states the mandatory six-month minimum, two-year maximum, and fine. |
| s39 | partial | `repaired`, `ambiguous_facts` | The repair removes unsupported BNSS 243 and gives accurate conditional offences under sections 74 and 76. The prompt says only "assaulted," so the facts do not establish the gold-labelled gang-rape offence under section 70. |
| s40 | pass | none | Sections 88 and 89 correctly cover causing miscarriage without consent. Sections 92 and 85 are supported conditional additions. |
| s41 | pass | none | Section 249 and its punishment branches are accurate, including the spouse exception. |
| s42 | pass | none | Sections 271 and 272 are accurately separated by negligent versus malignant conduct. |
| s43 | partial | `truncated` | Section 238 and all punishment branches are accurate. The answer cuts off at the end of a separate child-birth concealment condition. |
| s44 | pass | none | Sections 217 and 248 correctly fit a knowingly false complaint intended to cause arrest. Section 228 is clearly conditional on fabricated evidence. |
| s45 | pass | `repaired` | The repair removes unsupported BNSS 359 and gives the correct section 74 offence and punishment. |
| s46 | partial | `overconfident` | The listed crimes fit section 111, but organised crime also requires the statutory prior charge-sheet and cognizance history. The prompt does not provide it. |
| s47 | pass | none | Section 113 directly covers the terrorist act, and the death-result and no-death punishments are accurate. |
| s48 | pass | none | Section 152 covers purposeful encouragement of secession or armed rebellion. The BNSS forfeiture rule is supported. |
| s49 | pass | none | Section 147 directly covers the armed attempt to overthrow the Government of India. Section 149 and the BSA presumption are supported additions. |
| s50 | pass | none | Sections 304 and 62 correctly distinguish completed snatching from attempt and give the 1.5-year attempt ceiling. |

## Decision before judging

The repair improves usability without weakening the deterministic validator.
There is one generic refusal instead of six, and three of the repaired answers
are clean passes. The two remaining failures show the limit clearly: citation
membership still cannot prove that the model chose the right central offence or
stated every punishment correctly. I am keeping both rows in the final judge
sample rather than tuning again.
