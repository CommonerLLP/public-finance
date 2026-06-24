import pdfplumber
import json
import re

def get_lines(page):
    words = page.extract_words(extra_attrs=['fontname'])
    words.sort(key=lambda w: w['top'])
    
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
            current_line.sort(key=lambda x: x['x0'])
            lines.append(current_line)
            current_top = w['top']
            current_line = [w]
    if current_line:
        current_line.sort(key=lambda x: x['x0'])
        lines.append(current_line)
        
    return lines

def parse_lmmha(pdf_path):
    major_heads = {}
    current_major = None
    current_submajor = None
    
    with pdfplumber.open(pdf_path) as pdf:
        for i in range(28, min(499, len(pdf.pages))):
            page = pdf.pages[i]
            lines = get_lines(page)
            
            for line in lines:
                if not line: continue
                
                # Split line into columns based on x0
                major_code_words = []
                major_name_words = []
                minor_code_words = []
                minor_name_words = []
                
                for w in line:
                    x0 = w['x0']
                    if x0 < 120:
                        major_code_words.append(w)
                    elif 120 <= x0 < 250:
                        major_name_words.append(w)
                    elif 250 <= x0 < 310:
                        minor_code_words.append(w)
                    else:
                        minor_name_words.append(w)
                        
                major_code_str = " ".join([w['text'] for w in major_code_words])
                major_name_str = " ".join([w['text'] for w in major_name_words])
                minor_code_str = " ".join([w['text'] for w in minor_code_words])
                minor_name_str = " ".join([w['text'] for w in minor_name_words])
                
                # Check for major/submajor headers which shouldn't be processed as codes
                if major_code_str.startswith("MAJOR") or "MINOR" in minor_code_str or "HEADS" in minor_name_str:
                    continue
                if major_code_str.startswith("Note:") or major_name_str.startswith("Note:"):
                    continue

                # Process Major Code/Name
                if major_code_str:
                    if re.match(r'^\d{4}$', major_code_str) and 'Bold' in major_code_words[0]['fontname']:
                        current_major = major_code_str
                        current_submajor = None
                        name = re.sub(r'\s*\(\d+\).*$', '', major_name_str)
                        major_heads[current_major] = {"name": name, "submajors": {}, "minors": {}}
                    elif re.match(r'^\d{2}$', major_code_str) and 'Bold' in major_code_words[0]['fontname']:
                        current_submajor = major_code_str
                        name = re.sub(r'\s*\(\d+\).*$', '', major_name_str)
                        if current_major:
                            major_heads[current_major]["submajors"][current_submajor] = {"name": name, "minors": {}}
                elif major_name_str:
                    # Continuation of Major/Submajor Name
                    if 'Bold' in major_name_words[0]['fontname']:
                        name = re.sub(r'\s*\(\d+\).*$', '', major_name_str)
                        if current_submajor and current_major:
                            major_heads[current_major]["submajors"][current_submajor]["name"] += " " + name
                        elif current_major:
                            major_heads[current_major]["name"] += " " + name
                            
                # Process Minor Code/Name
                if minor_code_str:
                    if re.match(r'^\d{3}$', minor_code_str):
                        code = minor_code_str
                        name = re.sub(r'\s*\(\d+\).*$', '', minor_name_str)
                        if current_major:
                            if current_submajor:
                                major_heads[current_major]["submajors"][current_submajor]["minors"][code] = name
                            else:
                                major_heads[current_major]["minors"][code] = name
                elif minor_name_str:
                    # Continuation of Minor Name
                    if not 'Bold' in minor_name_words[0]['fontname']:
                        name = re.sub(r'\s*\(\d+\).*$', '', minor_name_str)
                        # Avoid notes
                        if "will be accounted" not in name and "below this minor" not in name and "Sub-Heads:" not in name:
                            if current_major:
                                if current_submajor:
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
