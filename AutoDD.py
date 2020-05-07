#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" AutoDD: Automatically does the so called Due Diligence for you. """

#AutoDD - Automatically does the "due diligence" for you.
#Copyright (C) 2020  Fufu Fang

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <https://www.gnu.org/licenses/>.

__author__ = "Fufu Fang and Jeff Levy"
__copyright__ = "The GNU General Public License v3.0"

from psaw import PushshiftAPI
from datetime import datetime, timedelta, date
import re
import spacy
from collections import defaultdict

nlp = spacy.load('en_core_web_sm')

class AutoDD():
    def __init__(self, days=1, use_ticker_validation=False):
        assert(days <= 7), 'In the interests of mercy toward Reddits API, please specify 7 days or less.'
        self.look_back = days
        self.use_ticker_validation = use_ticker_validation

        self.tickers = defaultdict(list)
        self.pattern = "[A-Z]{3,4}" #for regex ticker matching

        if use_ticker_validation:
            self.ticker_df = self.get_tickers()
            self.failed_validates = [] #track validation failures for auditing

    def get_tickers(self):
        # https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download
        # https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download
        # https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download
        import pandas as pd
        path = os.path.join(os.getcwd(), 'Documents', 'GitHub', 'AutoDD_fork', 'tickers')
        markets = ['amex.csv', 'nasdaq.csv', 'nyse.csv']
        df = pd.concat([pd.read_csv(os.path.join(path, f), usecols=['Symbol', 'Name']) for f in markets])
        df = df.groupby('Symbol').head(1) #verified that the few duplicates are exact matches
        return df

    def get_reddit(self, subreddit='pennystocks'):
        """Returns a generator for the submission in past n days"""
        n = self.look_back
        api = PushshiftAPI()
        s_date = datetime.today() - timedelta(days=n)
        s_timestamp = int(s_date.timestamp())
        pennystocks = api.search_submissions(after=s_timestamp,
                                             subreddit=subreddit,
                                             filter=['title', 'selftext', 'url', 'author', 'created'])
        return pennystocks, subreddit

    def parse_reddit(self):
        pennystocks, subreddit = self.get_reddit()

        for post in pennystocks:
            if not (hasattr(post, 'title') and hasattr(post, 'selftext')):
                continue
            tickers = self._find_tickers(post)
            for t in tickers:
                ticker = re.match(self.pattern, t.text).group(0) #Spacy sometimes groups other text with the pattern match when finding orgs
                self.tickers[ticker].append({'author':post.author,
                                             'title':post.title,
                                             'text':post.selftext,
                                             'date':date.fromtimestamp(post.created),
                                             'url':post.url,
                                             'token':t,
                                             'subreddit':subreddit})

    def _find_tickers(self, post):
        """Takes a PushshiftAPI submission object (one post) and returns a list of stock tickers as
        Spacy tokens, or an empty list."""
        text = '\n '.join([post.title, post.selftext])
        doc = nlp(text)
        ents = [ent for ent in doc.ents if ent.label_ == 'ORG' and self._is_ticker(ent.text)] #future: find corporation names in this list and link them to tickers
        return ents

    def _is_ticker(self, t):
        """Takes any string, then returns True if it's a stock ticker, else False.  Needs improvement."""
        is_ticker = re.match(self.pattern, t)
        if self.use_ticker_validation and is_ticker:
            ticker_validates = is_ticker.group(0) in self.ticker_df['Symbol'].values
            if not ticker_validates:
                self.failed_validates.append(t)
                is_ticker = False
        return is_ticker

if __name__ == '__main__':
    dd = AutoDD()
    dd.parse_reddit()

#
# def get_freq_list(gen):
#     """
#     Return the frequency list for the past n days
#
#     :param int gen: The generator for subreddit submission
#     :returns:
#         - all_tbl - frequency table for all stock mentions
#         - title_tbl - frequency table for stock mentions in titles
#         - selftext_tbl - frequency table for all stock metninos in selftext
#     """
#
#     # Python regex pattern for stocks codes
#     pattern = "[A-Z]{3,4}"
#     # Dictionary containing the summaries
#     title_dict = {}
#     selftext_dict = {}
#     all_dict = {}
#
#     for i in gen:
#         if hasattr(i, 'title'):
#             title = ' ' + i.title + ' '
#             title_extracted = re.findall(pattern, title)
#             for j in title_extracted:
#                 if j in title_dict:
#                     title_dict[j] += 1
#                 else:
#                     title_dict[j] = 1
#
#                 if j in all_dict:
#                     all_dict[j] += 1
#                 else:
#                     all_dict[j] = 1
#
#         if hasattr(i, 'selftext'):
#             selftext = ' ' + i.selftext + ' '
#             selftext_extracted = re.findall(pattern, selftext)
#             for j in selftext_extracted:
#                 if j in selftext_dict:
#                     selftext_dict[j] += 1
#                 else:
#                     selftext_dict[j] = 1
#
#                 if j in all_dict:
#                     all_dict[j] += 1
#                 else:
#                     all_dict[j] = 1
#
#     title_tbl = sorted(title_dict.items(), key=lambda x: x[1], reverse=True)
#     selftext_tbl = sorted(selftext_dict.items(), key=lambda x: x[1],
#                           reverse=True)
#     all_tbl = sorted(all_dict.items(), key=lambda x: x[1], reverse=True)
#
#     return all_tbl, title_tbl, selftext_tbl
#
#
# def filter_tbl(tbl, min):
#     """
#     Filter a frequency table
#
#     :param list tbl: the table to be filtered
#     :param int min: the number of days in the past
#     :returns: the filtered table
#     """
#     BANNED_WORDS = [
#         'THE', 'FUCK', 'ING', 'CEO', 'USD', 'WSB', 'FDA', 'NEWS', 'FOR', 'YOU',
#         'BUY', 'HIGH', 'ADS', 'FOMO', 'THIS', 'OTC', 'ELI', 'IMO',
#         'CBS', 'SEC', 'NOW', 'OVER', 'ROPE', 'MOON', "SSR"
#     ]
#     tbl = [row for row in tbl if row[1] > min]
#     tbl = [row for row in tbl if row[0] not in BANNED_WORDS]
#     return tbl
#
#
# def print_tbl(tbl):
#     print("Code\tFrequency")
#     for row in tbl:
#         padding = ""
#         if len(row[0]) < 4:
#             padding = ' '
#         print(str(row[0]) + padding + "\t" + str(row[1]))
#
#
# if __name__ == '__main__':
#     gen = get_submission(1)  # Get 1 day worth of submission
#     all_tbl, _, _ = get_freq_list(gen)
#     all_tbl = filter_tbl(all_tbl, 2)
#     print_tbl(all_tbl)
