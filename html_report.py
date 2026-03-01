import os
import webbrowser
import datetime
import pandas as pd


def generate_html_report(new_flats: pd.DataFrame, all_flats: pd.DataFrame, output_dir: str = './output'):
    """Generate an HTML report of scraped flats and open it in the browser."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, 'report.html')
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    new_rows = _build_rows(new_flats) if not new_flats.empty else '<tr><td colspan="9" class="empty">No new flats found</td></tr>'
    all_rows = _build_rows(all_flats) if not all_flats.empty else '<tr><td colspan="9" class="empty">No flats found</td></tr>'

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

<div class="section">
  <h2>New Flats <span class="count">({len(new_flats)})</span></h2>
  <div class="filters">
    <input type="text" id="filter-new" placeholder="Filter new flats..." oninput="filterTable('new-table', this.value)">
  </div>
  <div style="overflow-x:auto;">
  <table id="new-table">
    <thead><tr>
      <th onclick="sortTable('new-table',0)">Location <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('new-table',1)">Price <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('new-table',2)">Rooms <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('new-table',3)">m&#178; <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('new-table',4)">Price/m&#178; <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('new-table',5)">Floor <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('new-table',6)">PENB <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('new-table',7)">State <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th>Link</th>
    </tr></thead>
    <tbody>{new_rows}</tbody>
  </table>
  </div>
</div>

<div class="section">
  <h2>All Scraped Flats <span class="count">({len(all_flats)})</span></h2>
  <div class="filters">
    <input type="text" id="filter-all" placeholder="Filter all flats..." oninput="filterTable('all-table', this.value)">
  </div>
  <div style="overflow-x:auto;">
  <table id="all-table">
    <thead><tr>
      <th onclick="sortTable('all-table',0)">Location <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('all-table',1)">Price <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('all-table',2)">Rooms <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('all-table',3)">m&#178; <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('all-table',4)">Price/m&#178; <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('all-table',5)">Floor <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('all-table',6)">PENB <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th onclick="sortTable('all-table',7)">State <span class="arrow">&#x25B4;&#x25BE;</span></th>
      <th>Link</th>
    </tr></thead>
    <tbody>{all_rows}</tbody>
  </table>
  </div>
</div>

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


def _build_rows(df: pd.DataFrame) -> str:
    rows = []
    for _, r in df.iterrows():
        price = int(r.get('price', 0))
        ppm = float(r.get('price_per_meter', 0))
        meters = int(r.get('meters', 0))
        floor = r.get('floor', 'N/A')
        rooms = r.get('rooms', '')
        link = r.get('link', '')
        source = _detect_source(link)
        rows.append(f"""<tr>
  <td>{r.get('title', '')}</td>
  <td class="price" data-val="{price}">{price:,} Kč</td>
  <td class="num">{rooms}</td>
  <td class="num" data-val="{meters}">{meters}</td>
  <td class="num" data-val="{ppm:.0f}">{ppm:,.0f}</td>
  <td class="num" data-val="{floor}">{floor}</td>
  <td>{r.get('penb', 'N/A')}</td>
  <td>{r.get('state', 'N/A')}</td>
  <td><a href="{link}" target="_blank">{source}</a></td>
</tr>""")
    return '\n'.join(rows)


def _detect_source(link: str) -> str:
    if 'sreality' in link:
        return 'sreality.cz'
    if 'bezrealitky' in link:
        return 'bezrealitky.cz'
    if 'idnes' in link:
        return 'idnes.cz'
    return 'link'
