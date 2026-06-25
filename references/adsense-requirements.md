# AdSense Requirements Checklist

Last checked against Google documentation: 2026-06-25.

Use this file for AdSense application readiness, rejection diagnosis, and post-fix verification. It is an operational checklist, not a guarantee of approval. If current Google documentation conflicts with this file, current Google documentation wins.

## Official Sources

- AdSense Help: https://support.google.com/adsense/
- Make sure your site's pages are ready for AdSense: https://support.google.com/adsense/answer/7299563
- Eligibility requirements for AdSense: https://support.google.com/adsense/answer/9724
- Owning the site you want to use to participate in AdSense: https://support.google.com/adsense/answer/91205
- AdSense site management: https://support.google.com/adsense/answer/12131223
- Ads.txt guide: https://support.google.com/adsense/answer/12171612
- Fix AdSense crawler issues: https://support.google.com/adsense/answer/2381908
- AdSense Program policies: https://support.google.com/adsense/answer/48182
- Google Publisher Policies: https://support.google.com/adsense/answer/10502938
- Google Publisher Restrictions: https://support.google.com/adsense/answer/10437795
- Required privacy-policy content for Google advertising cookies: https://support.google.com/adsense/answer/1348695

## Status Rules

- `Pass`: verified with evidence from code, rendered pages, live crawl, account data, or owner-provided proof.
- `Fail`: evidence shows the requirement is not met.
- `Unknown`: the requirement needs AdSense dashboard access, owner confirmation, server/CDN data, analytics, legal review, or broader page sampling.
- `N/A`: the requirement truly does not apply to this site type or monetization mode; explain why.

## Severity Rules

- `Blocker`: likely approval blocker, ownership/crawl failure, hard policy violation, no original value, or severe deceptive UX.
- `High`: meaningful review/ad-serving risk that should be fixed before applying.
- `Medium`: quality, trust, UX, disclosure, implementation, or evidence gap.

## A. Eligibility and Account

| ID | Severity | Requirement | How to verify |
| --- | --- | --- | --- |
| ADS-ELIG-01 | Blocker | Applicant/account owner meets AdSense eligibility, including the age requirement or guardian-account path. | Confirm owner/account context. |
| ADS-ELIG-02 | Blocker | Publisher is not creating a duplicate AdSense account for the same publisher identity. | Ask whether an existing AdSense account exists. |
| ADS-ELIG-03 | Blocker | Site content is expected to comply with AdSense Program policies and Google Publisher Policies. | Complete ADS-PROG, ADS-PUB, and ADS-REST sections. |
| ADS-ELIG-04 | Medium | Hosted products such as Blogger or YouTube use the appropriate hosted-account flow. | Mark N/A for ordinary self-hosted sites. |

## B. Ownership, Verification, and Ads.txt

| ID | Severity | Requirement | How to verify |
| --- | --- | --- | --- |
| ADS-OWN-01 | Blocker | Publisher controls the site and can modify the HTML/CMS/theme path needed for AdSense code. | Verify repo/CMS/theme access and `<head>` injection path. |
| ADS-OWN-02 | Blocker | Publisher is not applying with a site they do not own or cannot verify. | Confirm domain/site ownership. |
| ADS-OWN-03 | High | Site supports normal JavaScript rendering for AdSense code. | Check rendered pages and template head/body structure. |
| ADS-SITE-01 | Blocker | Site can be added to AdSense, verified, reviewed, and marked ready before ads serve. | Check AdSense dashboard when available; otherwise Unknown. |
| ADS-SITE-02 | High | At least one verification method can be deployed, such as ad code, meta tag, or ads.txt depending on the account flow. | Verify implementation path. |
| ADS-TXT-01 | High | If `/ads.txt` exists, Google is authorized with the correct publisher ID after account creation. | Fetch `/ads.txt`; compare seller line with account ID. |
| ADS-TXT-02 | Medium | If `/ads.txt` is missing before account ID exists, the follow-up task is explicit. | Mark Unknown before publisher ID; require post-ID update. |

## C. Content Quality and Site Value

| ID | Severity | Requirement | How to verify |
| --- | --- | --- | --- |
| ADS-CONTENT-01 | Blocker | Site has useful, original, visitor-relevant content. | Sample homepage, category/list pages, and representative detail pages. |
| ADS-CONTENT-02 | Blocker | Copied, syndicated, embedded, or affiliate-feed content has meaningful original commentary, curation, review, data, or tooling. | Compare templates, snippets, embeds, and source attribution. |
| ADS-CONTENT-03 | High | Main content is substantial, not only navigation, tags, empty lists, cards, or thin shells. | Inspect rendered text and source content models. |
| ADS-CONTENT-04 | High | Site is not under construction, empty, placeholder-heavy, or built mainly to show ads. | Check broken sections, lorem ipsum, coming-soon copy, and empty routes. |
| ADS-CONTENT-05 | High | Ads, affiliate blocks, sponsored blocks, or paid promotion do not dominate publisher content. | Estimate above-the-fold and full-page balance. |
| ADS-CONTENT-06 | Medium | Primary language is supported and pages are not low-value mixed-language fragments. | Identify main language and representative pages. |
| ADS-CONTENT-07 | Medium | User-generated content, comments, uploads, or forums are moderated for policy compliance. | Review visible UGC and moderation workflow. |
| ADS-CONTENT-08 | Medium | Pages are not doorway pages or keyword-stuffed pages made mainly for search engines. | Inspect title/H1/body repetition, duplication, and page intent. |

## D. Navigation, UX, and Trust

| ID | Severity | Requirement | How to verify |
| --- | --- | --- | --- |
| ADS-UX-01 | High | Navigation is readable, aligned, functional, and usable on desktop and mobile. | Test header, menu, footer, dropdowns, and responsive behavior. |
| ADS-UX-02 | High | Users can understand what the site is and move between sections without misleading paths. | Check homepage/category/detail flow and internal links. |
| ADS-UX-03 | Blocker | Site does not use fake download/play buttons, nonexistent content links, irrelevant redirects, or ad-like navigation. | Inspect CTAs, button labels, redirects, and ad placeholders. |
| ADS-UX-04 | Blocker | Site does not unexpectedly change user settings, trigger downloads, include malware, or show obstructive popups/popunders. | Test page load, clicks, overlays, and third-party scripts. |
| ADS-UX-05 | Medium | Trust pages exist and are real: About, Contact, Privacy Policy, and Terms/disclaimer where relevant. | Verify accessible pages and non-empty useful content. |
| ADS-UX-06 | Medium | Layout does not confuse ads, affiliate blocks, navigation, and content, especially before approval. | Inspect visual hierarchy and labels. |

## E. Crawlability, Access, and Technical Availability

| ID | Severity | Requirement | How to verify |
| --- | --- | --- | --- |
| ADS-CRAWL-01 | Blocker | Site is live, public, and key URLs do not return 4xx/5xx. | Fetch homepage and representative pages. |
| ADS-CRAWL-02 | Blocker | AdSense crawler is not blocked by login walls, robots.txt, WAF, IP restrictions, or geoblocking. | Check public access, robots rules, CDN/WAF symptoms, and server behavior. |
| ADS-CRAWL-03 | High | Ad-bearing pages do not require POST-only state to display content. | Check forms, search/detail routes, and server routes. |
| ADS-CRAWL-04 | High | Important pages avoid fragile redirects, excessive hops, or cookie/session-only access. | Trace redirects and canonical destinations. |
| ADS-CRAWL-05 | Medium | Content URLs are stable and avoid per-user/session IDs for the same content. | Inspect URLs, canonical tags, and sitemap paths. |
| ADS-CRAWL-06 | High | DNS, TLS, and hosting respond reliably enough for review and crawler access. | Check live response, certificate, and hosting errors. |
| ADS-CRAWL-07 | Medium | Sitemap/internal links expose important pages and newly published content has a crawl path. | Check sitemap and internal navigation. |

## F. AdSense Program Policies

| ID | Severity | Requirement | How to verify |
| --- | --- | --- | --- |
| ADS-PROG-01 | Blocker | Publisher does not inflate clicks or impressions with self-clicks, bots, repeated manual actions, or deceptive software. | Ask owner; inspect traffic/automation if available. |
| ADS-PROG-02 | Blocker | Site does not ask users to click/view ads, reward ad actions, or draw artificial attention to ads. | Inspect copy near ad slots and CTAs. |
| ADS-PROG-03 | Blocker | Ads are distinguishable from content and use neutral labels where labels are present. | Inspect ad labels/design. |
| ADS-PROG-04 | High | Traffic sources are legitimate and do not rely on paid-to-click, auto-surf, spam, software-driven traffic, or poor paid landing pages. | Ask owner; inspect analytics/campaign data if available. |
| ADS-PROG-05 | High | Ad code is not modified in ways that inflate performance or harm advertisers. | Inspect ad wrappers and custom scripts when present. |
| ADS-PROG-06 | Blocker | Google ads are not placed in software, emails, private communication screens, ad-only/non-content pages, unauthorized framed content, or Google-impersonation pages. | Inspect planned/current placement templates. |
| ADS-PROG-07 | High | App WebView monetization is treated as special and not assumed eligible for ordinary website AdSense. | Mark N/A for normal websites. |

## G. Google Publisher Policies: Prohibited Content and Conduct

| ID | Severity | Requirement | How to verify |
| --- | --- | --- | --- |
| ADS-PUB-01 | Blocker | No illegal content, illegal activity promotion, or rights violations. | Review topic, products, downloads, and instructions. |
| ADS-PUB-02 | Blocker | No copyright infringement, counterfeit goods, or brand/trademark abuse. | Check copied media, logos, downloads, and source rights. |
| ADS-PUB-03 | Blocker | No dangerous or derogatory content such as hate, harassment, threats, self-harm promotion, violence praise, terrorism, cartel support, or extortion. | Review content and UGC. |
| ADS-PUB-04 | Blocker | No animal cruelty promotion or endangered/threatened species product sales. | Review niche/product content. |
| ADS-PUB-05 | Blocker | No misleading representation of publisher identity, creator, purpose, affiliations, endorsements, or brand relationships. | Check About, authorship, branding, logos, and disclosures. |
| ADS-PUB-06 | Blocker | No deceptive behavior such as phishing, personal-information theft, fake offers, or intentionally misleading service claims. | Check forms, offers, and lead flows. |
| ADS-PUB-07 | Blocker | No content enabling dishonest behavior such as fake documents, academic cheating, drug-test evasion, hacking, cracking, tracking, or spyware. | Review tools/downloads/tutorials. |
| ADS-PUB-08 | Blocker | No paid sexual acts, cross-border marriage broker content, adult themes in family content, or child sexual abuse/exploitation. | Review adult/family/UGC areas. |
| ADS-PUB-09 | High | Publisher information and ad request data are accurate, including site/app identity and ads.txt/app-ads.txt where applicable. | Check metadata, account mapping, and ads.txt. |
| ADS-PUB-10 | High | Ads do not interfere with content, navigation, or required user interactions. | Inspect responsive layout and ad placement plan. |
| ADS-PUB-11 | Blocker | Ads are not shown on no-content, low-value, under-construction, copied-without-value, unsupported-language, or paid-promotion-dominated pages. | Inspect representative templates. |
| ADS-PUB-12 | High | Ads are not placed out of context, off-screen, in background pages, or where user attention is clearly elsewhere. | Inspect layout and lazy-loaded slots. |
| ADS-PUB-13 | Blocker | No harmful false claims about elections/democratic processes, health consensus, or climate consensus. | Review news, health, politics, science, climate, and UGC content. |
| ADS-PUB-14 | Blocker | No manipulated media that deceives users about politics, social issues, or public-concern topics. | Review images/video/audio and AI-media disclosures. |
| ADS-PUB-15 | Blocker | No child endangerment, grooming, sextortion, sexualization of minors, child trafficking, or CSAM-related signals. | Review content, images, comments, uploads, and moderation logs where available. |
| ADS-PUB-16 | High | Sensitive-event content is not exploitative, denialist, or insensitive when monetized. | Review crisis/news pages and monetization context. |

## H. Google Publisher Restrictions: Restricted Inventory Risks

| ID | Severity | Requirement | How to verify |
| --- | --- | --- | --- |
| ADS-REST-01 | High | Sexual content, sexual entertainment, sexual products, sexual-health supplements, or sexual advice is absent or excluded from ads. | Review categories, images, and UGC. |
| ADS-REST-02 | High | Shocking, graphic, violent, disgusting, or prominently profane content is absent or isolated from ads. | Review articles, game imagery, images, comments, and language. |
| ADS-REST-03 | High | Explosives, firearms, firearm parts, weapons, or acquisition/assembly instructions are absent or excluded from ads. | Review products/tutorials. |
| ADS-REST-04 | High | Tobacco, recreational drugs, drug paraphernalia, or production/use instructions are absent or excluded from ads. | Review products/articles. |
| ADS-REST-05 | High | Alcohol sales or irresponsible drinking promotion is absent or excluded from ads. | Review ecommerce/affiliate links and content framing. |
| ADS-REST-06 | High | Online gambling or paid games of chance are absent unless explicitly eligible by geography and policy. | Review offers, affiliate links, and target geos. |
| ADS-REST-07 | High | Prescription-drug sales, online pharmacies, unapproved drugs/supplements, or delisted apps are absent or excluded from ads. | Review health/ecommerce/app content. |
| ADS-REST-08 | High | Ads do not obscure content; content does not obscure ads; video ad controls are not hidden or broken. | Inspect layout/video placements. |

## I. Privacy and Data

| ID | Severity | Requirement | How to verify |
| --- | --- | --- | --- |
| ADS-PRIV-01 | Blocker | Privacy policy discloses Google-product data collection, sharing, and use, including cookies or similar identifiers. | Inspect privacy page and footer link. |
| ADS-PRIV-02 | High | Privacy policy discloses third-party advertising cookies/web beacons/IP-address use where ads are served. | Check privacy policy language. |
| ADS-PRIV-03 | High | Site does not pass personally identifiable information to Google in ad requests or use Google services to identify users without required notice/consent. | Inspect URLs, query params, ad code, analytics, and data layer. |
| ADS-PRIV-04 | High | EU/UK user consent requirements are handled where applicable. | Check consent banner/CMP and target geography. |
| ADS-PRIV-05 | High | Precise location data, if collected, has disclosure, opt-in consent, secure transmission, and privacy-policy coverage. | Check app/site permissions and data flows. |
| ADS-PRIV-06 | High | Child-directed or COPPA-covered content is marked appropriately and not used for interest-based advertising. | Check audience, content, and account settings. |
| ADS-PRIV-07 | High | Site does not set, modify, intercept, or delete cookies on Google domains. | Inspect custom ad/proxy code if present. |
| ADS-PRIV-08 | High | Personalized ads/audience lists do not use sensitive categories such as child-directed activity, adult/gambling/government-site activity, health, finance, ethnicity, religion, crime, politics, unions, or sexual behavior/orientation. | Inspect ad personalization, remarketing, audiences, and data-layer events. |
| ADS-PRIV-09 | High | Housing, employment, or credit-related targeting in the US/Canada does not use restricted demographics or postal-code targeting. | Check marketing/audience settings if relevant. |
| ADS-PRIV-10 | Medium | If personalized ads are used, publisher has rights to audience data and provides required interest-based advertising disclosures or controls. | Check consent/CMP, privacy policy, and ad choice disclosures. |

## Required Audit Output

Every AdSense audit must include:

1. `Decision`: `Ready`, `Ready after fixes`, or `Not ready`.
2. `Blockers`, `High Risks`, and `Medium Risks`, ordered by severity.
3. For each finding: `ADS ID`, issue, evidence, official/source basis, exact fix, and acceptance criteria.
4. `Exhaustive ADS Checklist` with every ID exactly once:

| ID | Severity | Status | Evidence | Next action |
| --- | --- | --- | --- | --- |
| ADS-ELIG-01 | Blocker | Pass/Fail/Unknown/N/A | ... | ... |

5. `Completeness Check`:
   - Requirement IDs in this reference: 73
   - Requirement IDs in report: `<count>`
   - Missing IDs: `none` or list

Do not mark `Pass` without evidence. Use `Unknown` when account, analytics, AdSense dashboard, owner confirmation, server/CDN data, legal review, or broader page sampling is required.
