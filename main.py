from typing import List
import os
import time
import yaml
from tabulate import tabulate
from emailing.EmailSender import EmailSender
import multiprocessing
from ScrapingPipeline import ScrapingPipeline


def run_pipeline_for_client(client_config):
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
    # truncate our table and insert current_data to be able to filter against them in the future
    #scraper.truncate_flats()
    scraper.insert_flats(only_new_flats)
    # close the db session
    scraper.session.close()
    # show only_new_flats
    scraper.show_results(only_new_flats)
    # save only_new_flats to csv
    scraper.save_to_csv(only_new_flats, scraper.res_file)
    # send emails about new flats
    message = None if only_new_flats.empty else tabulate(only_new_flats, showindex=False, headers=only_new_flats.columns, tablefmt="psql")
    #message = None if only_new_flats.empty else only_new_flats.to_string(index=False)
    EmailSender(client_config).send_message_to_all(message)


if __name__ == "__main__":
    cfg = yaml.safe_load(open(os.path.join(os.path.dirname(__file__),'config.yml')))
    # run the whole workflow for each client in run_for
    run_for: List[str] = cfg['run_for']
    client_config_list = [cfg[client] for client in cfg if client in run_for]
    # run in paralel
    pool = multiprocessing.Pool(processes=4)
    pool.map(run_pipeline_for_client, client_config_list)
    pool.close()
    pool.join()
    pool.terminate()

