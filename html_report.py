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
        ('penb', 'PENB', 'penb', None),
        ('state', 'State', '', None),
    ],
    'house': [
        ('title', 'Location', '', None),
        ('price', 'Price', 'price', lambda v: f"{int(v):,} Kč"),
        ('living_area', 'Living m²', 'num', lambda v: str(int(v))),
        ('lot_size', 'Lot m²', 'num', lambda v: str(int(v))),
        ('house_type', 'Type', '', None),
        ('price_per_meter', 'Price/m²', 'num', lambda v: f"{float(v):,.0f}"),
        ('penb', 'PENB', 'penb', None),
        ('state', 'State', '', None),
    ],
    'lot': [
        ('title', 'Location', '', None),
        ('price', 'Price', 'price', lambda v: f"{int(v):,} Kč"),
        ('lot_size', 'Lot m²', 'num', lambda v: str(int(v))),
        ('price_per_meter', 'Price/m²', 'num', lambda v: f"{float(v):,.0f}"),
        ('water', 'Water', 'infra', None),
        ('gas', 'Gas', 'infra', None),
        ('electricity', 'Electricity', 'infra', None),
        ('sewer', 'Sewer', 'infra', None),
    ],
}

TYPE_LABELS = {
    'flat': 'Flats',
    'house': 'Houses',
    'lot': 'Lots',
}

TYPE_ICONS = {
    'flat': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>',
    'house': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    'lot': '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/></svg>',
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

    all_types = list(dict.fromkeys(list(new_data.keys()) + list(all_data.keys())))

    tabs_html = _build_tabs(all_types, new_data, all_data)
    panels_html = _build_panels(all_types, new_data, all_data)

    html = f"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reality Report — {now}</title>
<style>
{_get_css()}
</style>
</head>
<body>

<header class="header">
  <div class="header-inner">
    <div class="header-title">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
      <div>
        <h1>Reality Report</h1>
        <span class="header-meta">{now}</span>
      </div>
    </div>
  </div>
</header>

<nav class="tabs">
  {tabs_html}
</nav>

<main class="main">
  {panels_html}
</main>

<script>
{_get_js()}
</script>
</body>
</html>"""

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML report saved to {os.path.abspath(path)}")
    webbrowser.open(f'file://{os.path.abspath(path)}')
    return path


def _get_css():
    return """
  :root {
    --bg: #f0f2f5;
    --card: #ffffff;
    --border: #e2e5ea;
    --text: #1a1d23;
    --text-secondary: #6b7280;
    --accent: #2563eb;
    --accent-light: #eff3ff;
    --green: #059669;
    --green-bg: #ecfdf5;
    --red: #dc2626;
    --amber: #d97706;
    --radius: 10px;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-lg: 0 4px 12px rgba(0,0,0,0.08);
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }

  .header {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    color: #fff;
    padding: 20px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }
  .header-inner {
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .header-title {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .header-title svg { opacity: 0.9; }
  .header-title h1 {
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .header-meta {
    font-size: 0.8rem;
    opacity: 0.6;
  }

  .tabs {
    background: var(--card);
    border-bottom: 1px solid var(--border);
    display: flex;
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 24px;
    gap: 0;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: var(--shadow-sm);
  }
  .tab {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 14px 20px;
    font-size: 0.88rem;
    font-weight: 500;
    color: var(--text-secondary);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.15s ease;
    white-space: nowrap;
    user-select: none;
  }
  .tab:hover { color: var(--text); background: #f8f9fa; }
  .tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }
  .tab .badge {
    background: var(--bg);
    color: var(--text-secondary);
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 10px;
  }
  .tab.active .badge {
    background: var(--accent-light);
    color: var(--accent);
  }
  .tab .new-badge {
    background: var(--green-bg);
    color: var(--green);
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 10px;
  }

  .main {
    max-width: 1400px;
    margin: 0 auto;
    padding: 24px;
  }

  .panel { display: none; }
  .panel.active { display: block; }

  .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    margin-bottom: 20px;
  }
  .stat-card {
    background: var(--card);
    border-radius: var(--radius);
    padding: 16px 18px;
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--border);
  }
  .stat-card .stat-label {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
  }
  .stat-card .stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .stat-card .stat-sub {
    font-size: 0.78rem;
    color: var(--text-secondary);
    margin-top: 2px;
  }
  .stat-new .stat-value { color: var(--green); }

  .section {
    background: var(--card);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    border: 1px solid var(--border);
    margin-bottom: 20px;
    overflow: hidden;
  }
  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
    gap: 10px;
  }
  .section-title {
    font-size: 0.95rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .section-title .count {
    color: var(--text-secondary);
    font-weight: 400;
  }
  .section-title .new-dot {
    width: 8px;
    height: 8px;
    background: var(--green);
    border-radius: 50%;
    display: inline-block;
  }

  .filter-wrap {
    position: relative;
  }
  .filter-wrap input {
    padding: 7px 12px 7px 34px;
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 0.82rem;
    width: 220px;
    outline: none;
    transition: border-color 0.15s, box-shadow 0.15s;
    background: #fafbfc;
  }
  .filter-wrap input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    background: #fff;
  }
  .filter-wrap svg {
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-secondary);
    pointer-events: none;
  }

  .table-wrap { overflow-x: auto; }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
  }
  thead { background: #f8f9fb; }
  th {
    text-align: center;
    padding: 10px 14px;
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-secondary);
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
    position: sticky;
    top: 0;
    background: #f8f9fb;
    transition: background 0.1s;
  }
  th:first-child { text-align: left; }
  th:hover { background: #eef0f4; }
  th .sort-icon {
    display: inline-block;
    margin-left: 4px;
    font-size: 0.65rem;
    color: #ccc;
    vertical-align: middle;
  }
  th.sorted-asc .sort-icon, th.sorted-desc .sort-icon { color: var(--accent); }

  td {
    padding: 10px 14px;
    border-bottom: 1px solid #f0f1f3;
    vertical-align: middle;
    text-align: center;
  }
  td:first-child { text-align: left; }
  tbody tr { transition: background 0.1s; }
  tbody tr:hover { background: #f7f8fa; }
  tbody tr:last-child td { border-bottom: none; }

  td.price { text-align: right; white-space: nowrap; font-weight: 500; font-variant-numeric: tabular-nums; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  td.empty-row {
    text-align: center;
    padding: 40px 20px;
    color: var(--text-secondary);
    font-size: 0.9rem;
  }

  .link-cell a {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 500;
    text-decoration: none;
    transition: filter 0.1s;
  }
  .link-cell a:hover { filter: brightness(0.9); text-decoration: none; }
  .src-sreality { background: #fee2e2; color: #b91c1c; }
  .src-bezrealitky { background: #dbeafe; color: #1d4ed8; }
  .src-idnes { background: #fef3c7; color: #92400e; }
  .src-other { background: var(--bg); color: var(--text-secondary); }

  .penb-badge {
    display: inline-block;
    width: 26px;
    text-align: center;
    padding: 2px 0;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    color: #fff;
  }
  .penb-a { background: #059669; }
  .penb-b { background: #34d399; color: #064e3b; }
  .penb-c { background: #fbbf24; color: #78350f; }
  .penb-d { background: #f97316; }
  .penb-e { background: #ef4444; }
  .penb-f { background: #b91c1c; }
  .penb-g { background: #6b7280; }
  .penb-na { background: #e5e7eb; color: #9ca3af; }

  .infra-yes { color: var(--green); font-weight: 500; }
  .infra-no { color: var(--red); font-weight: 500; }

  @media (max-width: 768px) {
    .main { padding: 12px; }
    .stats { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .filter-wrap input { width: 160px; }
    .section-header { padding: 12px 14px; }
    td, th { padding: 8px 10px; }
    .tab { padding: 12px 14px; font-size: 0.82rem; }
  }
"""


def _get_js():
    return """
function initTabs() {
  const tabs = document.querySelectorAll('.tab');
  const panels = document.querySelectorAll('.panel');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(tab.dataset.panel).classList.add('active');
    });
  });
  if (tabs.length) tabs[0].click();
}

function sortTable(tableId, colIdx) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const th = table.querySelectorAll('th')[colIdx];
  const allTh = table.querySelectorAll('th');

  // determine direction
  const wasAsc = th.classList.contains('sorted-asc');
  allTh.forEach(t => { t.classList.remove('sorted-asc', 'sorted-desc'); });
  const dir = wasAsc ? 'desc' : 'asc';
  th.classList.add('sorted-' + dir);

  rows.sort((a, b) => {
    let aVal = a.cells[colIdx]?.dataset.val || a.cells[colIdx]?.textContent || '';
    let bVal = b.cells[colIdx]?.dataset.val || b.cells[colIdx]?.textContent || '';
    let aNum = parseFloat(aVal), bNum = parseFloat(bVal);
    if (!isNaN(aNum) && !isNaN(bNum)) return dir === 'asc' ? aNum - bNum : bNum - aNum;
    return dir === 'asc' ? aVal.localeCompare(bVal, 'cs') : bVal.localeCompare(aVal, 'cs');
  });
  rows.forEach(r => tbody.appendChild(r));
}

function filterTable(tableId, query) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const rows = table.querySelectorAll('tbody tr');
  const q = query.toLowerCase();
  rows.forEach(r => { r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none'; });
}

document.addEventListener('DOMContentLoaded', initTabs);
"""


def _build_tabs(all_types, new_data, all_data):
    tabs = []
    for i, pt in enumerate(all_types):
        label = TYPE_LABELS.get(pt, pt.capitalize())
        icon = TYPE_ICONS.get(pt, '')
        all_count = len(all_data.get(pt, pd.DataFrame()))
        new_count = len(new_data.get(pt, pd.DataFrame()))
        new_badge = f' <span class="new-badge">+{new_count}</span>' if new_count else ''
        tabs.append(
            f'<div class="tab" data-panel="panel-{pt}">'
            f'{icon} {label} <span class="badge">{all_count}</span>{new_badge}'
            f'</div>'
        )
    return '\n  '.join(tabs)


def _build_panels(all_types, new_data, all_data):
    panels = []
    for pt in all_types:
        label = TYPE_LABELS.get(pt, pt.capitalize())
        cols = COLUMN_CONFIGS.get(pt, COLUMN_CONFIGS['flat'])
        new_df = new_data.get(pt, pd.DataFrame())
        all_df = all_data.get(pt, pd.DataFrame())

        stats = _build_stats(pt, new_df, all_df, cols)
        new_section = _build_section(f"new-{pt}", f"New {label}", new_df, cols, is_new=True)
        all_section = _build_section(f"all-{pt}", f"All {label}", all_df, cols, is_new=False)

        panels.append(f"""
<div class="panel" id="panel-{pt}">
  {stats}
  {new_section}
  {all_section}
</div>""")
    return '\n'.join(panels)


def _build_stats(pt, new_df, all_df, cols):
    cards = []

    # Total count
    cards.append(_stat_card("Total Listings", str(len(all_df)), ""))

    # New count
    if not new_df.empty:
        cards.append(_stat_card("New Found", f"+{len(new_df)}", "", css_class="stat-new"))

    # Price stats
    price_col = 'price'
    if not all_df.empty and price_col in all_df.columns:
        avg_price = all_df[price_col].mean()
        min_price = all_df[price_col].min()
        cards.append(_stat_card("Avg Price", f"{int(avg_price):,} Kč", f"Min: {int(min_price):,} Kč"))

    # Price/m² stats
    ppm_col = 'price_per_meter'
    if not all_df.empty and ppm_col in all_df.columns:
        avg_ppm = all_df[ppm_col].mean()
        min_ppm = all_df[ppm_col].min()
        cards.append(_stat_card("Avg Price/m²", f"{int(avg_ppm):,} Kč", f"Min: {int(min_ppm):,} Kč"))

    return f'<div class="stats">{"".join(cards)}</div>'


def _stat_card(label, value, sub, css_class=""):
    cls = f' {css_class}' if css_class else ''
    sub_html = f'<div class="stat-sub">{sub}</div>' if sub else ''
    return (
        f'<div class="stat-card{cls}">'
        f'<div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div>'
        f'{sub_html}'
        f'</div>'
    )


def _build_section(section_id, title, df, cols, is_new):
    table_id = f"{section_id}-table"
    col_count = len(cols) + 1  # +1 for link

    dot = '<span class="new-dot"></span> ' if is_new else ''

    headers = ''
    for i, col in enumerate(cols):
        headers += (
            f'<th onclick="sortTable(\'{table_id}\',{i})">'
            f'{col[1]} <span class="sort-icon">&#9650;&#9660;</span></th>'
        )
    headers += '<th>Source</th>'

    if df.empty:
        rows = f'<tr><td colspan="{col_count}" class="empty-row">No listings found</td></tr>'
    else:
        rows = _build_rows(df, cols)

    search_icon = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>'

    return f"""
<div class="section">
  <div class="section-header">
    <div class="section-title">{dot}{title} <span class="count">({len(df)})</span></div>
    <div class="filter-wrap">
      {search_icon}
      <input type="text" placeholder="Filter..." oninput="filterTable('{table_id}', this.value)">
    </div>
  </div>
  <div class="table-wrap">
    <table id="{table_id}">
      <thead><tr>{headers}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>"""


def _build_rows(df: pd.DataFrame, cols) -> str:
    rows = []
    for _, r in df.iterrows():
        cells = []
        for key, header, css_class, fmt in cols:
            val = r.get(key, 'N/A')
            display = fmt(val) if fmt and val not in (None, 'N/A', '') else str(val)

            if css_class == 'penb':
                cells.append(_penb_cell(val))
                continue

            if css_class == 'infra':
                cells.append(_infra_cell(val))
                continue

            data_attr = ''
            if css_class in ('price', 'num'):
                try:
                    data_attr = f' data-val="{float(val)}"'
                except (ValueError, TypeError):
                    data_attr = f' data-val="{val}"'
            cls = f' class="{css_class}"' if css_class else ''
            cells.append(f'<td{cls}{data_attr}>{display}</td>')

        link = r.get('link', '')
        source, src_class = _detect_source(link)
        cells.append(
            f'<td class="link-cell">'
            f'<a href="{link}" target="_blank" class="{src_class}">{source}</a>'
            f'</td>'
        )

        rows.append(f"<tr>{''.join(cells)}</tr>")
    return '\n'.join(rows)


def _penb_cell(val):
    val_str = str(val).strip().upper() if val not in (None, '', 'N/A') else 'N/A'
    css = f'penb-{val_str.lower()}' if val_str in 'ABCDEFG' else 'penb-na'
    display = val_str if val_str != 'N/A' else '–'
    return f'<td style="text-align:center"><span class="penb-badge {css}">{display}</span></td>'


def _infra_cell(val):
    val_str = str(val).strip() if val not in (None, '', 'N/A') else 'N/A'
    if val_str.lower() in ('ano', 'yes', 'true', '1'):
        return '<td class="infra-yes">Ano</td>'
    elif val_str.lower() in ('ne', 'no', 'false', '0'):
        return '<td class="infra-no">Ne</td>'
    return f'<td>{val_str}</td>'


def _detect_source(link: str) -> tuple:
    if 'sreality' in link:
        return ('sreality.cz', 'src-sreality')
    if 'bezrealitky' in link:
        return ('bezrealitky.cz', 'src-bezrealitky')
    if 'idnes' in link:
        return ('idnes.cz', 'src-idnes')
    return ('link', 'src-other')
