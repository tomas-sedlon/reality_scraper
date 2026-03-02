from typing import List
import os
import sys
import time
import yaml
import pandas as pd
from tabulate import tabulate
from emailing.EmailSender import EmailSender
from ScrapingPipeline import ScrapingPipeline, TYPE_KEY_MAP
from html_report import generate_html_report


def load_config():
    """Load config.yml and merge with config.local.yml if it exists."""
    base_dir = os.path.dirname(__file__)
    cfg_path = os.path.join(base_dir, 'config.yml')
    local_path = os.path.join(base_dir, 'config.local.yml')

    cfg = yaml.safe_load(open(cfg_path))

    if os.path.exists(local_path):
        local_cfg = yaml.safe_load(open(local_path))
        if local_cfg:
            # Merge run_for lists
            local_run_for = local_cfg.get('run_for', [])
            cfg['run_for'] = list(dict.fromkeys(cfg.get('run_for', []) + local_run_for))
            # Merge client dicts (local overrides shared)
            for key, val in local_cfg.items():
                if key == 'run_for':
                    continue
                if key in cfg and isinstance(cfg[key], dict) and isinstance(val, dict):
                    cfg[key].update(val)
                else:
                    cfg[key] = val

    return cfg


def run_pipeline_for_client(client_config, open_html=False, skip_email=False):
    print(f"\n\n\nRunning pipeline for {client_config['db_name']}\n\n\n")
    time.sleep(1)

    scraper = ScrapingPipeline(client_config)
    scraper.start_scraping_workflow()

    property_types = client_config.get('property_types', ['flats'])
    all_new = {}
    all_current = {}
    combined_new_frames = []

    for pt_key in property_types:
        pt = TYPE_KEY_MAP.get(pt_key, pt_key)

        current_data = scraper.get_current_results(pt)
        old_data = scraper.get_old_data(pt)
        only_new = scraper.get_only_new_data(current_data, old_data)
        scraper.insert_data(only_new, pt)
        scraper.show_results(only_new, label=pt)

        all_new[pt] = only_new
        all_current[pt] = current_data
        if not only_new.empty:
            combined_new_frames.append(only_new)

    scraper.session.close()

    # Save CSV with all new items combined
    if combined_new_frames:
        combined = pd.concat(combined_new_frames, ignore_index=True)
        scraper.save_to_csv(combined, scraper.res_file)
    else:
        scraper.save_to_csv(pd.DataFrame(), scraper.res_file)

    # Generate HTML report
    if open_html:
        generate_html_report(all_new, all_current)

    # Send emails about new items
    if not skip_email:
        if combined_new_frames:
            combined = pd.concat(combined_new_frames, ignore_index=True)
            message = tabulate(combined, showindex=False, headers=combined.columns, tablefmt="psql")
        else:
            message = None
        EmailSender(client_config).send_message_to_all(message)


if __name__ == "__main__":
    cfg = load_config()
    run_for: List[str] = cfg['run_for']
    client_config_list = [cfg[client] for client in cfg if client in run_for]

    open_html = '--html' in sys.argv
    skip_email = '--no-email' in sys.argv or open_html

    for client in client_config_list:
        run_pipeline_for_client(client, open_html=open_html, skip_email=skip_email)
