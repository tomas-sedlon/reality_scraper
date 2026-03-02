import os
import webbrowser
import datetime
import pandas as pd

# Column definitions per property type: (key, header, css_class, format_func)
COLUMN_CONFIGS = {
    'flat': [
        ('title', 'Location', '', None),
        ('price', 'Price', 'price', lambda v: f"{int(v):,} Kč"),
        ('rooms', 'Rooms', 'num', None),
        ('meters', 'm²', 'num', lambda v: str(int(v))),
        ('price_per_meter', 'Price/m²', 'num', lambda v: f"{float(v):,.0f}"),
        ('floor', 'Floor', 'num', None),
        ('penb', 'PENB', '', None),
        ('state', 'State', '', None),
    ],
    'house': [
        ('title', 'Location', '', None),
        ('price', 'Price', 'price', lambda v: f"{int(v):,} Kč"),
        ('living_area', 'Living m²', 'num', lambda v: str(int(v))),
        ('lot_size', 'Lot m²', 'num', lambda v: str(int(v))),
        ('house_type', 'Type', '', None),
        ('price_per_meter', 'Price/m²', 'num', lambda v: f"{float(v):,.0f}"),
        ('penb', 'PENB', '', None),
        ('state', 'State', '', None),
    ],
    'lot': [
        ('title', 'Location', '', None),
        ('price', 'Price', 'price', lambda v: f"{int(v):,} Kč"),
        ('lot_size', 'Lot m²', 'num', lambda v: str(int(v))),
        ('price_per_meter', 'Price/m²', 'num', lambda v: f"{float(v):,.0f}"),
        ('water', 'Water', '', None),
        ('gas', 'Gas', '', None),
        ('electricity', 'Electricity', '', None),
        ('sewer', 'Sewer', '', None),
    ],
}

TYPE_LABELS = {
    'flat': 'Flats',
    'house': 'Houses',
    'lot': 'Lots',
}


def generate_html_report(new_data, all_data, output_dir: str = './output'):
    """Generate an HTML report. Accepts either DataFrames (legacy) or dicts keyed by property type."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, 'report.html')
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    # Normalize input: if plain DataFrames, wrap in dict
    if isinstance(new_data, pd.DataFrame):
        new_data = {'flat': new_data}
    if isinstance(all_data, pd.DataFrame):
        all_data = {'flat': all_data}

    sections_html = _build_all_sections(new_data, all_data)

    html = f"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reality Report — {now}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; padding: 20px; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 6px; }}
  .meta {{ color: #888; font-size: 0.85rem; margin-bottom: 20px; }}
  .section {{ background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; }}
  .section h2 {{ font-size: 1.1rem; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #e0e0e0; }}
  .section h2 .count {{ color: #888; font-weight: normal; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  th {{ background: #fafafa; text-align: left; padding: 8px 10px; border-bottom: 2px solid #ddd; white-space: nowrap; position: sticky; top: 0; cursor: pointer; user-select: none; }}
  th:hover {{ background: #f0f0f0; }}
  th .arrow {{ font-size: 0.7rem; margin-left: 4px; color: #aaa; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #eee; }}
  tr:hover {{ background: #f9f9f9; }}
  td.price {{ text-align: right; white-space: nowrap; }}
  td.num {{ text-align: right; }}
  td.empty {{ text-align: center; padding: 30px; color: #999; }}
  a {{ color: #1a73e8; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .good {{ color: #2e7d32; }}
  .bad {{ color: #c62828; }}
  .tag {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; }}
  .tag-new {{ background: #e8f5e9; color: #2e7d32; }}
  .filters {{ display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }}
  .filters input {{ padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.82rem; }}
</style>
</head>
<body>
<h1>Reality Scraper Report</h1>
<p class="meta">Generated: {now}</p>

{sections_html}

<script>
function sortTable(tableId, colIdx) {{
  const table = document.getElementById(tableId);
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const dir = table.dataset['sort' + colIdx] === 'asc' ? 'desc' : 'asc';
  table.dataset['sort' + colIdx] = dir;
  rows.sort((a, b) => {{
    let aVal = a.cells[colIdx]?.dataset.val || a.cells[colIdx]?.textContent || '';
    let bVal = b.cells[colIdx]?.dataset.val || b.cells[colIdx]?.textContent || '';
    let aNum = parseFloat(aVal), bNum = parseFloat(bVal);
    if (!isNaN(aNum) && !isNaN(bNum)) return dir === 'asc' ? aNum - bNum : bNum - aNum;
    return dir === 'asc' ? aVal.localeCompare(bVal, 'cs') : bVal.localeCompare(aVal, 'cs');
  }});
  rows.forEach(r => tbody.appendChild(r));
}}
function filterTable(tableId, query) {{
  const rows = document.getElementById(tableId).querySelectorAll('tbody tr');
  const q = query.toLowerCase();
  rows.forEach(r => {{ r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none'; }});
}}
</script>
</body>
</html>"""

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML report saved to {os.path.abspath(path)}")
    webbrowser.open(f'file://{os.path.abspath(path)}')
    return path


def _build_all_sections(new_data: dict, all_data: dict) -> str:
    """Build HTML sections for all property types."""
    sections = []
    all_types = list(dict.fromkeys(list(new_data.keys()) + list(all_data.keys())))

    for pt in all_types:
        label = TYPE_LABELS.get(pt, pt.capitalize())
        cols = COLUMN_CONFIGS.get(pt, COLUMN_CONFIGS['flat'])
        new_df = new_data.get(pt, pd.DataFrame())
        all_df = all_data.get(pt, pd.DataFrame())
        col_count = len(cols) + 1  # +1 for link column

        new_table_id = f"new-{pt}-table"
        all_table_id = f"all-{pt}-table"

        new_rows = _build_rows(new_df, cols) if not new_df.empty else f'<tr><td colspan="{col_count}" class="empty">No new {label.lower()} found</td></tr>'
        all_rows = _build_rows(all_df, cols) if not all_df.empty else f'<tr><td colspan="{col_count}" class="empty">No {label.lower()} found</td></tr>'

        header_ths = ''.join(
            f'<th onclick="sortTable(\'{{}}\',{i})">{col[1]} <span class="arrow">&#x25B4;&#x25BE;</span></th>'
            for i, col in enumerate(cols)
        )
        header_ths += '<th>Link</th>'

        new_headers = header_ths.format(*([new_table_id] * len(cols)))
        all_headers = header_ths.format(*([all_table_id] * len(cols)))

        # Rebuild headers properly
        new_headers = ''
        all_headers = ''
        for i, col in enumerate(cols):
            new_headers += f'<th onclick="sortTable(\'{new_table_id}\',{i})">{col[1]} <span class="arrow">&#x25B4;&#x25BE;</span></th>'
            all_headers += f'<th onclick="sortTable(\'{all_table_id}\',{i})">{col[1]} <span class="arrow">&#x25B4;&#x25BE;</span></th>'
        new_headers += '<th>Link</th>'
        all_headers += '<th>Link</th>'

        sections.append(f"""
<div class="section">
  <h2>New {label} <span class="count">({len(new_df)})</span></h2>
  <div class="filters">
    <input type="text" placeholder="Filter new {label.lower()}..." oninput="filterTable('{new_table_id}', this.value)">
  </div>
  <div style="overflow-x:auto;">
  <table id="{new_table_id}">
    <thead><tr>{new_headers}</tr></thead>
    <tbody>{new_rows}</tbody>
  </table>
  </div>
</div>

<div class="section">
  <h2>All Scraped {label} <span class="count">({len(all_df)})</span></h2>
  <div class="filters">
    <input type="text" placeholder="Filter all {label.lower()}..." oninput="filterTable('{all_table_id}', this.value)">
  </div>
  <div style="overflow-x:auto;">
  <table id="{all_table_id}">
    <thead><tr>{all_headers}</tr></thead>
    <tbody>{all_rows}</tbody>
  </table>
  </div>
</div>""")

    return '\n'.join(sections)


def _build_rows(df: pd.DataFrame, cols) -> str:
    rows = []
    for _, r in df.iterrows():
        cells = []
        for key, header, css_class, fmt in cols:
            val = r.get(key, 'N/A')
            display = fmt(val) if fmt and val not in (None, 'N/A', '') else str(val)
            data_attr = ''
            if css_class in ('price', 'num'):
                try:
                    data_attr = f' data-val="{float(val)}"'
                except (ValueError, TypeError):
                    data_attr = f' data-val="{val}"'
            cls = f' class="{css_class}"' if css_class else ''
            cells.append(f'<td{cls}{data_attr}>{display}</td>')

        link = r.get('link', '')
        source = _detect_source(link)
        cells.append(f'<td><a href="{link}" target="_blank">{source}</a></td>')

        rows.append(f"<tr>{''.join(cells)}</tr>")
    return '\n'.join(rows)


def _detect_source(link: str) -> str:
    if 'sreality' in link:
        return 'sreality.cz'
    if 'bezrealitky' in link:
        return 'bezrealitky.cz'
    if 'idnes' in link:
        return 'idnes.cz'
    return 'link'
