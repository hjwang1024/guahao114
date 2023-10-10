#!/usr/bin/env python
# -*- coding: utf-8


import requests
import yaml
from yaml import Loader

class Browser(object):
    """
    浏览器
    """
    def __init__(self):
        self.session = requests.Session()
        self.hospital_id = ''
        self.cookies = {}
        with open('config.yaml', "r", encoding="utf-8") as yaml_file:
            data = yaml.load(yaml_file, Loader)
            self.hospital_id = data["hospitalId"]
            self.cookies = {
                "cmi-user-ticket": data["cmi-user-ticket"]
            }

        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36',
            'Content-Type': 'application/json; charset=UTF-8',
            'Request-Source': 'PC',
            'Referer': 'https://www.114yygh.com/hospital/' + self.hospital_id + '/home'
        }

    def load_cookies(self):
        self.session.cookies = requests.utils.cookiejar_from_dict(self.cookies)

    def get(self, url, data):
        """
        http get
        """
        pass
        response = self.session.get(url)
        if response.status_code == 200:
            self.session.headers['Referer'] = response.url
        return response

    def post(self, url, data):
        """
        http post
        """
        response = self.session.post(url, json=data)
        if response.status_code == 200:
            self.session.headers['Referer'] = response.url
        return response

