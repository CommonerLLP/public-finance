import pdfplumber
import json
import re

def get_lines(page):
    words = page.extract_words()
    # Sort words by top and then by left
    words.sort(key=lambda w: (round(w['top'], 1), w['x0']))
    
    lines = []
    current_line = []
    current_top = None
    
    for w in words:
        if current_top is None:
            current_top = w['top']
            current_line.append(w)
        elif abs(w['top'] - current_top) < 3:
            current_line.append(w)
        else:
            lines.append(current_line)
            current_top = w['top']
            current_line = [w]
    if current_line:
        lines.append(current_line)
        
    return lines

def parse_lmmha(pdf_path):
    major_heads = {}
    
    current_major = None
    current_submajor = None
    
    # Text classification based on x0
    # Major/Submajor Code: ~100
    # Major/Submajor Name: ~136 to ~250
    # Minor Code: ~208 or ~280
    # Minor Name: ~244 or ~317
    
    with pdfplumber.open(pdf_path) as pdf:
        # Start at page 28, end at 498
        for i in range(28, min(499, len(pdf.pages))):
            page = pdf.pages[i]
            lines = get_lines(page)
            
            for line in lines:
                if not line: continue
                text = " ".join([w['text'] for w in line])
                x0 = line[0]['x0']
                
                # Ignore headers/footers
                if text.startswith("MAJOR / SUB-MAJOR") or "MINOR HEADS" in text:
                    continue
                if text.startswith("Note:") or re.match(r'^\(\d+\)', text):
                    continue
                
                # Major Head: Code is 4 digits
                if 95 <= x0 <= 105 and re.match(r'^\d{4}\s', text):
                    code = text[:4]
                    name = text[5:].strip()
                    # Remove footnotes like (1), (2)
                    name = re.sub(r'\s*\(\d+\).*$', '', name)
                    current_major = code
                    current_submajor = None
                    major_heads[code] = {
                        "name": name,
                        "submajors": {},
                        "minors": {}
                    }
                # Sub-Major Head: Code is 2 digits
                elif (95 <= x0 <= 140) and re.match(r'^\d{2}\s', text):
                    code = text[:2]
                    name = text[3:].strip()
                    name = re.sub(r'\s*\(\d+\).*$', '', name)
                    current_submajor = code
                    if current_major:
                        major_heads[current_major]["submajors"][code] = {"name": name, "minors": {}}
                # Minor Head: Code is 3 digits
                elif (200 <= x0 <= 290) and re.match(r'^\d{3}\s', text):
                    code = text[:3]
                    name = text[4:].strip()
                    name = re.sub(r'\s*\(\d+\).*$', '', name)
                    if current_major:
                        if current_submajor:
                            major_heads[current_major]["submajors"][current_submajor]["minors"][code] = name
                        else:
                            major_heads[current_major]["minors"][code] = name
                # Continuation of name
                elif (120 <= x0 <= 200) and not re.match(r'^\d', text):
                    name = re.sub(r'\s*\(\d+\).*$', '', text)
                    if current_submajor and current_major:
                        major_heads[current_major]["submajors"][current_submajor]["name"] += " " + name
                    elif current_major:
                        major_heads[current_major]["name"] += " " + name
                # Continuation of minor name
                elif (230 <= x0 <= 330) and not re.match(r'^\d', text):
                    name = re.sub(r'\s*\(\d+\).*$', '', text)
                    if current_major:
                        if current_submajor:
                            # Append to last minor
                            if major_heads[current_major]["submajors"][current_submajor]["minors"]:
                                last_minor = list(major_heads[current_major]["submajors"][current_submajor]["minors"].keys())[-1]
                                major_heads[current_major]["submajors"][current_submajor]["minors"][last_minor] += " " + name
                        else:
                            if major_heads[current_major]["minors"]:
                                last_minor = list(major_heads[current_major]["minors"].keys())[-1]
                                major_heads[current_major]["minors"][last_minor] += " " + name

    return major_heads

if __name__ == '__main__':
    data = parse_lmmha('references/lmmha/LMMHA_CGA_2026.pdf')
    with open('references/lmmha/lmmha_clean.json', 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Parsed {len(data)} Major Heads.")
