from typing import List
import os
import sys
import time
import yaml
from tabulate import tabulate
from emailing.EmailSender import EmailSender
from ScrapingPipeline import ScrapingPipeline
from html_report import generate_html_report


def run_pipeline_for_client(client_config, open_html=False, skip_email=False):
    print(f"\n\n\nRunning pipeline for {client_config['db_name']}\n\n\n")
    time.sleep(1)

    # scrape the sites
    scraper = ScrapingPipeline(client_config)
    scraper.start_scraping_workflow()
    # get current data from scrapers
    current_data = scraper.get_current_results()
    # get previous data from db table
    old_data = scraper.get_old_data()
    # get only new flats that were not in our db table
    only_new_flats = scraper.get_only_new_data(current_data, old_data)
    # insert new flats into db
    scraper.insert_flats(only_new_flats)
    # close the db session
    scraper.session.close()
    # show only_new_flats
    scraper.show_results(only_new_flats)
    # save only_new_flats to csv
    scraper.save_to_csv(only_new_flats, scraper.res_file)

    # generate HTML report
    if open_html:
        generate_html_report(only_new_flats, current_data)

    # send emails about new flats
    if not skip_email:
        message = None if only_new_flats.empty else tabulate(only_new_flats, showindex=False, headers=only_new_flats.columns, tablefmt="psql")
        EmailSender(client_config).send_message_to_all(message)


if __name__ == "__main__":
    cfg = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), 'config.yml')))
    run_for: List[str] = cfg['run_for']
    client_config_list = [cfg[client] for client in cfg if client in run_for]

    open_html = '--html' in sys.argv
    skip_email = '--no-email' in sys.argv or open_html

    for client in client_config_list:
        run_pipeline_for_client(client, open_html=open_html, skip_email=skip_email)
