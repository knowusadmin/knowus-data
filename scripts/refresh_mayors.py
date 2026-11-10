#!/usr/bin/env python3
"""Current mayor of each city in the app's data/mayors.json, from the CITY'S OWN OFFICIAL WEBSITE only (owner's source
policy, Nov 9 2026: no Wikipedia/Wikidata). For each city, the mayor's name is kept only when the city's official mayor
page (PAGES below) shows that full name; the page is the source. A city whose page can't be read or doesn't show the
name keeps no "Mayor now" line (the previous official entry is kept for up to 14 days if the page is just unreachable).
No photo, party or start date is taken from anywhere else. No AI, no keys.
Writes data/mayors-current.json: {"checkedAt","source","cities":{"<id>":{"city","st","n","src":{"name","url"},"checkedAt"}}}"""
import json, os, re, sys, unicodedata, datetime as dt
import requests
OUT = os.environ.get('KNOWUS_MAYORS_OUT', 'data/mayors-current.json')
UA = {'User-Agent': 'Mozilla/5.0 (compatible; KnowUS-data-refresh/2.0; +https://github.com/knowusadmin/knowus-data)'}
PAGES = {
 "anaheim-ca": [
  "https://www.anaheim.net/2989/Mayor-Ashleigh-Aitken",
  "https://www.anaheim.net/1123/Mayor-City-Council"
 ],
 "chula-vista-ca": [
  "https://www.chulavistaca.gov/departments/mayor-and-council/mayor",
  "https://www.chulavistaca.gov/departments/mayor-and-council/mayor-john-mccann/contactmayor",
  "https://www.chulavistaca.gov/departments/mayor-council"
 ],
 "corpus-christi-tx": [
  "https://www.corpuschristitx.gov/our-government/mayor-and-council/mayor-s-office/"
 ],
 "henderson-nv": [
  "https://www.cityofhenderson.com/government/mayor-and-city-council",
  "https://www.cityofhenderson.com/"
 ],
 "irvine-ca": [
  "https://cityofirvine.gov/city-council/mayor-larry-agran"
 ],
 "laredo-tx": [
  "https://www.cityoflaredo.com/government/mayor",
  "https://www.cityoflaredo.com/"
 ],
 "lexington-ky": [
  "https://www.lexingtonky.gov/government/mayors-office/about-mayor-linda-gorton"
 ],
 "little-rock-ar": [
  "https://littlerock.gov/government/mayors-office/mayor-scott/"
 ],
 "los-angeles-ca": [
  "https://mayor.lacity.gov/"
 ],
 "louisville-ky": [
  "https://louisvilleky.gov/government/mayor-craig-greenberg",
  "https://louisvilleky.gov/government/mayor-craig-greenberg/contact-office-mayor-craig-greenberg",
  "https://louisvilleky.gov/government/mayor-craig-greenberg/mayors-message-mayor-greenbergs-monthly-update"
 ],
 "north-las-vegas-nv": [
  "https://www.cityofnorthlasvegas.com/departments/city-council-and-mayor",
  "https://www.cityofnorthlasvegas.com/"
 ],
 "oakland-ca": [
  "https://www.oaklandca.gov/Government/City-Council-Leadership/Leadership/Office-of-the-Mayor",
  "https://www.oaklandca.gov/Government/City-Council-Leadership/Leadership",
  "https://www.oaklandca.gov/Government/City-Council-Leadership/Leadership/Office-of-the-Mayor/Biography"
 ],
 "providence-ri": [
  "https://www.providenceri.gov/mayors-office/"
 ],
 "raleigh-nc": [
  "https://raleighnc.gov/city-council/janet-cowell",
  "https://raleighnc.gov/mayors-corner"
 ],
 "reno-nv": [
  "https://www.reno.gov/government/city-council/"
 ],
 "santa-ana-ca": [
  "https://santa-ana.gov/valerie-amezcua/"
 ],
 "st-petersburg-fl": [
  "https://www.stpete.org/"
 ],
 "tallahassee-fl": [
  "https://www.talgov.com/"
 ],
 "trenton-nj": [
  "https://www.trentonnj.org/"
 ],
 "washington-dc": [
  "https://mayor.dc.gov/"
 ]
}
# the name to look for: the person the official page is expected to show (checked every run; a new mayor's name is added here)
NAMES = {
 "anaheim-ca": "Ashleigh Aitken",
 "chula-vista-ca": "John McCann",
 "corpus-christi-tx": "Paulette Guajardo",
 "henderson-nv": "Michelle Romero",
 "irvine-ca": "Larry Agran",
 "laredo-tx": "Victor D. Trevi\u00f1o",
 "lexington-ky": "Linda Gorton",
 "little-rock-ar": "Frank Scott Jr.",
 "los-angeles-ca": "Karen Bass",
 "louisville-ky": "Craig Greenberg",
 "north-las-vegas-nv": "Pamela Goynes-Brown",
 "oakland-ca": "Barbara Lee",
 "providence-ri": "Brett Smiley",
 "raleigh-nc": "Janet Cowell",
 "reno-nv": "Hillary Schieve",
 "santa-ana-ca": "Valerie Amezcua",
 "st-petersburg-fl": "Ken Welch",
 "tallahassee-fl": "John E. Dailey",
 "trenton-nj": "Reed Gusciora",
 "washington-dc": "Muriel Bowser"
}
def strip(s): s = unicodedata.normalize('NFD', s or ''); return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
def shows(html, n):
    t = strip(re.sub(r'<[^>]+>', ' ', html))
    return all(p in t for p in strip(n).replace('.', ' ').split() if len(p) > 2 and p not in ('jr', 'sr'))
def main():
    now = dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    try: prev = json.load(open(OUT))
    except Exception: prev = {'cities': {}}
    out = {'checkedAt': now, 'source': "Each city's official website (the mayor's page named on each entry)", 'cities': {}}
    miss = []
    for cid, urls in PAGES.items():
        n = NAMES[cid]; hit = None; reach = False
        for u in urls:
            try:
                r = requests.get(u, headers=UA, timeout=25)
                if r.status_code == 200: reach = True
                if r.status_code == 200 and shows(r.text, n): hit = u; break
            except Exception: pass
        city, st = cid.rsplit('-', 1)
        if hit: out['cities'][cid] = {'city': city.replace('-', ' ').title(), 'st': st.upper(), 'n': n, 'src': {'name': 'City official website', 'url': hit}, 'checkedAt': now}
        else:
            p = (prev.get('cities') or {}).get(cid)
            if p and p.get('src', {}).get('url') and not reach and (dt.datetime.utcnow() - dt.datetime.strptime(p.get('checkedAt', '2000-01-01T00:00:00Z'), '%Y-%m-%dT%H:%M:%SZ')).days <= 14 and 'wikipedia' not in json.dumps(p):
                out['cities'][cid] = p
            else: miss.append(cid)
    json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False)
    print('mayors verified on official city pages:', len(out['cities']), 'of', len(PAGES), '| not verified:', miss)
if __name__ == '__main__':
    main()
