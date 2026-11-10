# KnowUS official photos + public contact (v47, 2026-11-10)
photos/<ST>/<key>.webp: 200px WebP (<25 KB), one per official. The app loads data/photos/<ST>.json from the site, which maps each official to [file, source page].
Allowed photo sources only: official .gov / city / county / legislature sites, the person's own campaign site or social accounts, Ballotpedia (credited "Photo: Ballotpedia"). Never Wikipedia/Wikimedia, AP, Reuters, banned outlets or Democratic sources (policy.mjs).
Name and office matched for every photo; a face check runs on each crop.
Contact: public official contact only (office phone, official email/contact form, office/capitol address, official site, official socials), each with its source page. No home addresses, personal cells/emails, or people-search data. Candidates get campaign contact only.
Pipeline: legjob*.py (legislatures via Open States CSV + legislature pages), locjob.py/locpass2.py (city/county official pages), bpjob2.js + bpdl.py (Ballotpedia, read in a browser), ctonly.py (contact re-pass).
