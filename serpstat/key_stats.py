#!/usr/bin/env python
import json
import signal
import time
import sys
import os
from urllib.parse import urlencode
import requests
import tldextract
import csv
import argparse
from retry import retry

args_description = """
* Example 1: top 100 by keyword filtered by domain
    ./key_stats_single.py -k "key word file" -s g_ua -d "olx.ua,google.com.ua"

* Example 2: top x urls by keyword and keyword_info
    ./key_stats_single.py -k "key word file" -s g_ua -d "olx.ua,google.com.ua" -i -t 10
    *** --domains or -d если в параметре -d указать sub.domain.com.ua - все равно будет *.domain.com.ua

* Очередь файлов через точку с запятой
    ./key_stats_single.... ; ./key_stats...

* Параллель:
    new:    tmux new -s keystat
    attach: tmux a -t keystat
    запускать разные файлы в разных окнах tmux
    new tmux window    : ctrl+b, c
    goto window number : ctrl+b, 0 .. 9
    next tmux window   : ctrl+b, n
    rename window (by current task): ctrl+b, ,
"""

parser = argparse.ArgumentParser()
group1 = parser.add_argument_group('* Example: keys only', './key_stats_single.py -k "key word file" -s g_ua -d "olx.ua,google.com.ua"')
parser.add_argument("-k", "--keys-file", help="имя файла в кавычках", type=str, nargs=1)
parser.add_argument("-s", "--search-engine", help="параметр поиска в формате серпстата: g_ua", type=str, nargs=1)
parser.add_argument("-d", "--domains", help="список доменов в кавычках, без пробелов, через запятую", type=str, nargs=1)

group2 = parser.add_argument_group('* Example: keys+info', './key_stats_single.py -k "key word file" -s g_ua -d "olx.ua" -i -t 10')
parser.add_argument("-i", "--keyword-info", help="генерить доп инфу", action="store_true")
parser.add_argument("-t", "--top", help="максимум запросов из топа", type=int, default=[0], nargs=1)

args = parser.parse_args()

try:
    keys_file = args.keys_file[0]
    domains = args.domains[0].split(',')
    search_engine = args.search_engine[0]
    keyword_info = args.keyword_info
    limit_top = args.top[0]

    if os.path.isfile(keys_file) is False:
        print("wrong key_file name\n try -h for help")
        exit(1)

    if keys_file == '' and search_engine == '' and domains == '':
        print("missing -s or -d\n try -h for help")
        exit(1)

    if keyword_info is True and limit_top < 1:
        print(" -t must be > 0 \n try -h for help")
        exit(1)

    if keyword_info is False and limit_top > 0:
        print("missing -i \n try -h for help")
        exit(1)

except Exception as e:
    print(e)
    parser.print_help()
    exit(1)

print(args)

keyword_info_fields = [
    'cost', 'concurrency', 'found_results', 'region_queries_count',
    'region_queries_count_wide', 'region_queries_count_last', 'geo_names', 'social_domains']
token = 'YOUR_TOKEN'
csv_delimiter = ','
csv_quote_char = '"'
csv_quoting = csv.QUOTE_ALL

g_last_line = None


def api_call(api_name, keyword):
    base = 'http://api.serpstat.com/v3/' + api_name + '?'
    url = base + urlencode({'token': token, 'query': keyword, 'se': search_engine})
    response = requests.get(url)
    if response.status_code == 200:
        write_log('.log', [200, url, response.content.decode('utf-8')])
    else:
        write_log('.log', [response.status_code, url, ''])
    return response


def match_domains(url):
    for domain in domains:
        if domain == '*':
            return True
        a = tldextract.extract(url)
        b = tldextract.extract(domain)
        if a.domain == b.domain and a.suffix == b.suffix:
            return True
    return False


def write_log(file_name, arr):
    with open(file_name, mode='a') as fh:
        f = csv.writer(fh, delimiter=csv_delimiter, quotechar=csv_quote_char, quoting=csv_quoting)
        f.writerow(arr)


@retry(Exception, tries=3, delay=3)
def process(n, keyword):
    response = api_call('keyword_top', keyword)
    #print(response.content.decode('utf-8'))

    assert(response.status_code == 200)

    if response.status_code == 200:
        res = response.content.decode('utf-8')
        j = json.loads(res)
        if j['status_code'] == 404:
            #print("key_not_found") #log to key not found
            write_log(keys_file + '.404_key_not_found.csv', [n, keyword])
        elif j['status_code'] == 200:
            not_found = True
            top_urls = []
            for line in j['result']['top']:
                url = line.get('url')
                top_urls.append(url)
                if match_domains(url):
                    not_found = False
                    #print('%d:%s,%s,%s' % (n, keyword, url, line.get('position')))
                    write_log(keys_file + '.top_100.csv', [keyword, url, line.get('subdomain'), line.get('position')])
            if not_found:
                #print('%d,%s,domain_not_found' % (n, keyword)) #domain not found
                write_log(keys_file + '.domain_not_found.csv', [n, keyword, res])

            if keyword_info is True:
                info_response = api_call('keyword_info', keyword)
                assert (info_response.status_code == 200)

                if info_response.status_code == 200:
                    res = info_response.content.decode('utf-8')
                    j = json.loads(res)
                    keyword_info_vals = []
                    for f in keyword_info_fields:
                        keyword_info_vals.append(str(j['result'].get(f)))

                    if os.path.isfile(keys_file + '.keyassort.csv') is False:
                        write_log(keys_file + '.keyassort.csv', ['Keyword', 'URL'] + keyword_info_fields)

                    for n in range(min([len(top_urls), limit_top])):
                        if n == 0:
                            write_log(keys_file + '.keyassort.csv', [keyword, top_urls[n]] + keyword_info_vals)
                        else:
                            write_log(keys_file + '.keyassort.csv', ['', top_urls[n]])



def get_last_line():
    global g_last_line
    if g_last_line is None:
        try:
            with open(keys_file + '.last_line', 'r') as kf:
                try:
                    g_last_line = int(kf.readline().strip())
                except ValueError:
                    g_last_line = -1
        except FileNotFoundError:
            g_last_line = -1
    return g_last_line


def skip_to(n): return n <= get_last_line()


def set_last_line(n):
    with open(keys_file + '.last_line', 'w') as kf:
        kf.write(str(n))


with open(keys_file, 'r') as kf:
    line = kf.readline()
    n = 0
    start = time.perf_counter()
    while line:
        time.sleep(1.5) # If you want to make it slow
        #print("%d,%s" % (n, line.strip()))
        if skip_to(n):
            if n%60==0:
                print(".", end='', flush=True)
            #print("skipped")
        else:
            process(n, line.strip())
            set_last_line(n)
            if n%15==0:
                print("[%dms]" % int((time.perf_counter() - start) * 1000 / 15), end='', flush=True)
                start = time.perf_counter()
            if n%60==0:
                print(str(n), end='', flush=True)
        line = kf.readline()
        n += 1
    print("This Is The End ... My Only Friend")
