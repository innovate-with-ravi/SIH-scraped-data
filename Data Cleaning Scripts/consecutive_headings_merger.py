def merge_consecutive_headings(text: str) -> str:
    """
    Merges consecutive markdown headings of the same level if they are not separated by content.
    """
    lines = text.split('\n')
    merged_lines = []
    
    last_heading_level = 0
    last_heading_idx = -1
    
    for line in lines:
        stripped = line.strip()
        
        # Determine heading level
        heading_level = 0
        if stripped.startswith('#') and stripped.lstrip('#').startswith(' '):
            heading_level = len(stripped) - len(stripped.lstrip('#'))
            
        if heading_level > 0: # not content but a heading
            if last_heading_idx != -1 and last_heading_level == heading_level:
                is_consecutive = True

                # if there's content in b/w the last_heading & current_heading, it's not consecutive
                # otherwise if there are empty lines in b/w last_heading & current_heading, we merge them
                for j in range(last_heading_idx + 1, len(merged_lines)):
                    if merged_lines[j].strip() != '':
                        is_consecutive = False
                        break
                
                if is_consecutive:
                    content = stripped[heading_level:].strip()
                    # remove the lines between last heading and this heading
                    while len(merged_lines) > last_heading_idx + 1:
                        merged_lines.pop()
                    
                    merged_lines[last_heading_idx] = merged_lines[last_heading_idx] + " " + content
                    continue
                    
            last_heading_level = heading_level
            merged_lines.append(line)
            last_heading_idx = len(merged_lines) - 1
        else: # content => append directly
            merged_lines.append(line)
            
    return '\n'.join(merged_lines)

if __name__ == '__main__':
    mdPath = r"D:\CODING\Hackathons\SIH\SIH-scraped-data\raw_data\raw_pdfs\05-ayurveda_aahara\68835f872eaf4Order dated 25-07-2025 enclosing Ayurveda Aahara.md"

    with open(mdPath, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    md_content = merge_consecutive_headings(md_content)
    
    with open(mdPath, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"Concecutive headings merged at {mdPath}")