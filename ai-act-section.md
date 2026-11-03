## EU AI Act Transparency (Art. 50)

> **Disclaimer:** This is an automated technical-legal pre-check of publicly visible pages and image metadata, as of 2026-11-03.
> It is not legal advice. AI origin can only be detected where provenance metadata survived. "No signal" does not mean "not AI-generated".

**Status: ⚠️ Action needed (recommended, low effort).** Reported separately, not part of the GEO Score.
**Role:** Deployer of image generators. The site itself names the tools: one image carries an OpenAI/DALL·E C2PA manifest, and two file names follow Freepik's AI-generator naming pattern. No chatbot. Probably no public-interest text in the sense of Art. 50(4).
**Scanned:** 10 pages, 73 image slots (scanner) plus 70 unique original assets (supplementary scan).
- AI-marked: 1 (labelled 0, page notice only 0, unlabelled 1)
- AI-indicated by the operator's own file name, with no embedded marker: 2 (both unlabelled)
- Labelled without marker: 0
- No signal: 67 unique images (scanner: 69 slots, many of them repeats)
- Not scanned: 4 (SVG logo)

**Method note (important):** The scanner reported 0 AI markers. That result is wrong for this site, for two reasons:
1. **It scanned CDN renditions, not the originals.** Gatsby/Contentful serves resized copies from `images.ctfassets.net/...?w=…&fm=…`, and these copies have all metadata stripped. Verified on the DALL·E image: the original `.webp` carries a C2PA manifest, while the `?w=456&fm=webp` rendition contains no C2PA bytes.
2. **It missed images delivered only via `<picture><source>`.** The DALL·E "Sportabzeichen" teaser has no `<img src>` that points to the asset.

To fill the gap, the first 768 KB of every original asset referenced in the 10 pages' HTML (70 files, 1 s delay) was fetched and searched for C2PA, IPTC DigitalSourceType and generator strings. The two Freepik PNGs were downloaded in full.

### What Article 50 requires from this site
- **Deep fakes (Art. 50(4) subpara. 1):** A visible label is required, at the latest at first exposure, on any AI-generated or AI-manipulated image that resembles real persons, places, objects or events and would falsely appear authentic. This applies, for example, to a photorealistic AI "photo" presented as the club's grounds, team or events. A tool's C2PA marking does not replace the visible label.
- **Illustrative or stylised AI graphics** (clipart, logos, obvious symbol images) are not deep fakes. They need no label under Art. 50, although a short "KI-generiert" note is good practice.
- **AI-written text on matters of public interest** must be disclosed unless a human has reviewed it under editorial responsibility. Club-life news is most likely outside this rule (see below).
- **Chatbots (Art. 50(1)):** Not relevant. No chat widget was found.
- **Timing:** The deployer duties apply from 2 Aug 2026. By the Commission's reading as reported in legal commentary, content published before that date does not have to be labelled retroactively, but labelling is encouraged.

### Legal Baseline Verification
| Rule | Status | Source | Checked |
|---|---|---|---|
| Art. 50 applies from 2 Aug 2026 | Confirmed ("These transparency obligations apply from 2 August 2026") | [Commission: Guidelines on transparency obligations (adopted 20 Jul 2026, updated 31 Jul 2026)](https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems) | 2026-11-03 |
| Art. 50(2) transition to 2 Dec 2026 for systems placed on the market before 2 Aug 2026 | Confirmed via secondary sources: Digital Omnibus, Reg. (EU) 2026/1744, OJ L of 24 Jul 2026 (listed on EUR-Lex), in force 27 Jul 2026. The EUR-Lex text itself could not be retrieved, so the article wording was not checked | [EUR-Lex AI Act page listing 2026/1744](https://www.eur-lex.europa.eu/eli/reg/2024/1689); [A&O Shearman e-alert](https://edge.sitecorecloud.io/allenoveryllp1-aoshearmanwe0db-production-ecf3/media/project/aoshearman/pdf-downloads/insights/2026/07/ealert---eu-digital-omnibus-on-ai_-the-wait-is-over-but-the-compliance-clock-is-running.pdf); [iubenda](https://www.iubenda.com/en/blog/ai-omnibus-adopted-august-2-obligations-july-2026/) | 2026-11-03 |
| Deployer disclosure (deep fakes, public-interest text): no transition | Confirmed. The Omnibus does not postpone the other Art. 50 duties (secondary sources) | Same as above; [McCann FitzGerald on the Commission guidelines](https://www.mccannfitzgerald.com/knowledge/data-privacy-and-cyber-risk/ai-transparency-european-commissions-guidelines-on-article-50-part-2-deployer-obligations) | 2026-11-03 |
| No retroactive labelling of content published before 2 Aug 2026 | Reported by several law-firm summaries of the final guidelines and FAQ. The Commission FAQ itself could not be reached, so this rests on secondary sources only | [Lewis Silkin](https://www.lewissilkin.com/insights/2026/07/31/the-new-ai-labelling-rules-for-deployers-in-the-advertising-supply-chain); [lausen.com](https://lausen.com/en/section-504-of-the-ai-act-what-organisations-must-label-as-ai-content-from-august-2026/) | 2026-11-03 |
| Deployer cannot rely on the provider's machine-readable marking; the label must be perceivable by humans | Confirmed (secondary sources on the guidelines) | [McCann FitzGerald](https://www.mccannfitzgerald.com/knowledge/data-privacy-and-cyber-risk/ai-transparency-european-commissions-guidelines-on-article-50-part-2-deployer-obligations) | 2026-11-03 |
| Code of Practice on marking and labelling AI-generated content | Final, published 10 Jun 2026, voluntary | [Commission news](https://digital-strategy.ec.europa.eu/en/news/commission-publishes-code-practice-marking-and-labelling-ai-generated-content) | 2026-11-03 |
| DE enforcement | KI-MIG (KI-Marktüberwachungs- und Innovationsförderungsgesetz) in force since 29 Jul 2026. The Bundesnetzagentur is the market surveillance authority from 2 Aug 2026 | [Bundesnetzagentur press release 29 Jul 2026](https://www.bundesnetzagentur.de/SharedDocs/Pressemitteilungen/DE/2026/20260729_KI_VO.html); [IHK](https://www.ihk.de/ihklw/produkte/beratung-und-service/ecommerce-und-internet/ki-mig-veroeffentlicht-7142702) | 2026-11-03 |
| Fines (Art. 99(4)): up to EUR 15 M or 3 % of worldwide turnover | Not re-checked against the primary text in this run. Taken from Art. 99(4) of Reg. (EU) 2024/1689 | [EUR-Lex 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) | 2026-11-03 |

### AI Images
| Image (page) | Marker | Label | Deep-fake verdict | Action |
|---|---|---|---|---|
| Homepage hero, `freepik__drone-shot-of-a-soccer-stadium__55656.png`, alt "TSV Bitzfeld 1922 e.V." (`/`) | No embedded marker (full 4 MB PNG checked). The file name follows Freepik's AI-generator pattern `freepik__<prompt>__<id>`, which is the operator's own upload and an indicator, not proof | None (no caption, no notice; the alt text names only the club) | **Likely deep fake, if AI-generated:** a photorealistic drone view of a sports ground in a village, used as the club's homepage hero, which a visitor will take for an aerial photo of the TSV's own grounds | Confirm the origin internally. If it is AI: add a visible "KI-generiert" / "Symbolbild (KI)" caption or overlay, or replace it with a real photo of the grounds. Online since at least Nov 2025 (Wayback), so it predates 2 Aug 2026 |
| News teaser "Satzungsänderung beim TSV Bitzfeld 1922 e.V.", `freepik__candid-photography-with-natural-textures-and-highl__67220.png`, alt "Vertrag" (`/neuigkeiten/`, also as JSON-LD `image`) | No embedded marker. Freepik AI file-name pattern | None | **Unlikely:** a generic symbol image (paper, pen, glasses, unreadable pseudo-text). It does not claim to show the club's real statute | Optional: caption "Symbolbild (KI)" |
| News teaser "Sportabzeichen", `DALL_E_2024-12-07_19.24.23_-_A_minimalist_and_sporty_clipart_design…webp` (`/`, `/neuigkeiten/`) | **Strong:** C2PA manifest (`c2pa.created`, softwareAgent DALL·E/OpenAI) plus IPTC `trainedAlgorithmicMedia`, in the original asset only. Stripped in the served renditions | None | **Unlikely:** a stylised clipart medal emblem, clearly not a photo | None required under Art. 50. Optional "KI-generiert" note. Keep the original metadata |
| 67 other unique images (team portraits, gallery photos "Festakt" 2022 and "Jahresfeier" 2020, WhatsApp group photos, flyers, logos) | No AI marker. 24 originals carry ordinary Photoshop CS4/CS6 or Lightroom Classic edit metadata, with no generative markers | n/a | Not assessed. AI origin cannot be determined from outside. File names and EXIF-style timestamps point to camera photos | Internal inventory (see below) |

No og:image reuse problem: the homepage og:image is the SVG logo, and the article og:images are real photos.

### Chatbots
None detected on the 10 scanned pages (scanner `chat_widgets: []`; no known widget scripts in the HTML). Not applicable.

### AI-Generated Text
Most likely **not applicable.** The "Neuigkeiten" cover club life: training weekends, a youth trip to a football match, events, dance group expansion, Sportabzeichen dates, statute amendments. These are association communications to members and fans, not information "on matters of public interest" in the sense of Art. 50(4) subpara. 2. The board (Vorstand), named in the Impressum, also exercises editorial control, which would trigger the editorial exception anyway. AI-written text cannot be detected reliably, and no text on this site is classified as AI-generated.

### Needs Review
- **Homepage hero:** confirm internally whether it is AI-generated and whether it shows the real Bitzfeld grounds. This decides between "label it" and "no action".
- **Article `/neuigkeiten/ausflug-der-jugendfussballabteilung-des-tsv-bitzfeld-zum-drittligaspiel/`:** an earlier review said it "reads like generated text". That is a stylistic guess, not evidence. It also concerns club news, not public-interest text. Recommendation only: if AI drafting tools are used, make sure a board member reviews and approves each article.
- **`no_signal` images:** metadata is stripped by the CDN, so origin cannot be checked from outside. The club should keep an internal note of which images came from AI tools (Freepik, DALL·E/ChatGPT).

### Findings by Severity
- **[Medium] [AI Act]** The homepage hero (`freepik__drone-shot-of-a-soccer-stadium…png`) is photorealistic, presented as the club's own setting, carries no label, and its file name indicates Freepik AI. It is a likely deep fake if it is AI-generated. It is rated Medium rather than High because AI origin rests only on the file name and because it was published before 2 Aug 2026, so no retroactive duty applies per the Commission guidance. It becomes **High** if it is re-uploaded or reused, or if a similar AI image is published after 2 Aug 2026 without a visible label.
- **[Low] [AI Act]** Two illustrative AI images (DALL·E Sportabzeichen emblem, Freepik "Vertrag" symbol image) carry no "KI-generiert" note. Art. 50 does not require one, but a note is recommended for consistency and trust, in both the caption and the alt text.
- **[Low] [AI Act]** There is no internal AI-content policy or register (recommendation).
- **Note (not Art. 50):** The AI hero could mislead visitors about the club's real facilities. UWG § 5 is unlikely to apply to a non-profit club's member communication, so this is mentioned only for completeness.

### Recommended Actions
1. Clarify the hero image's origin. If it is AI-generated, either add a visible caption or overlay ("KI-generiert" / "Symbolbild (KI)") or replace it with a real drone or ground photo of the Bitzfeld sports facility. Replacing it is the better option for trust and E-E-A-T.
2. From now on, give every AI image a visible caption at the image (alt text alone is not enough) and add "(KI-generiert)" to the alt text as well.
3. Keep provenance metadata: link or serve the original asset where possible, or record AI origin in the Contentful asset description so captions can be generated automatically.
4. Keep an internal register of AI-generated images and texts, with the tool used and the board member who reviewed them.
