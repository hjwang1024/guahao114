#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import time
import datetime
import logging
from tqdm import tqdm, trange
from browser import Browser
import yaml
from yaml import Loader

if sys.version_info.major != 3:
    logging.error("请在python3环境下运行本程序")
    sys.exit(-1)


class Config(object):

    def __init__(self, config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as yaml_file:
                data = yaml.load(yaml_file, Loader)
                debug_level = data["DebugLevel"]
                if debug_level == "debug":
                    self.debug_level = logging.DEBUG
                elif debug_level == "info":
                    self.debug_level = logging.INFO
                elif debug_level == "warning":
                    self.debug_level = logging.WARNING
                elif debug_level == "error":
                    self.debug_level = logging.ERROR
                elif debug_level == "critical":
                    self.debug_level = logging.CRITICAL

                logging.basicConfig(level=self.debug_level,
                                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                                    datefmt='%a, %d %b %Y %H:%M:%S')

                self.phoneNumber = data["phoneNumber"]
                self.date = data["date"]
                self.hospitalId = data["hospitalId"]
                self.firstDeptCode = data["firstDeptCode"]
                self.secondDeptCode = data["secondDeptCode"]
                self.timePeriod = data["timePeriod"]
                self.cardType = data["cardType"]
                self.hospitalCardId = data["hospitalCardId"]
                self.medicareCardId = data["medicareCardId"]
                self.doctorName = data["doctorName"]
                self.assign = data['assign']

                
                logging.info("配置加载完成")
                logging.debug("手机号:" + str(self.phoneNumber))
                logging.debug("挂号日期:" + str(self.date))
                logging.debug("医院id:" + str(self.hospitalId))
                logging.debug("上午/下午:" + str(self.timePeriod))
                logging.debug("所选医生:" + str(self.doctorName))
                logging.debug("是否挂指定医生:" + str(self.assign))

                if not self.date:
                    logging.error("请填写挂号时间")
                    exit(-1)

        except Exception as e:
            logging.error(repr(e))
            sys.exit()



class Guahao(object):
    """
    挂号
    """
    def __init__(self, config_path="config.yaml"):
        self.browser = Browser()
        self.dutys = []
        self.refresh_time = ''
        self.duty_url = "https://www.114yygh.com/web/product/detail"
        self.confirm_url = "https://www.114yygh.com/web/product/confirm"
        self.save_url = "https://www.114yygh.com/web/order/save"
        self.query_hospital_url = "https://www.114yygh.com/web/hospital/detail"  # 查询医院详情

        self.config = Config(config_path)  # config对象

    def is_login(self):
        logging.info("开始检查是否已经登录")
        response = self.browser.get("http://www.114yygh.com/web/user/info" + "?_time=" + str(self.timestamp()), data='')
        try:
            data = json.loads(response.text)
            if data["resCode"] == 0:
                logging.debug("response data:" + response.text)
                return True
            else:
                logging.debug("response data: HTML body")
                return False
        except Exception as e:
            logging.error(e)
            return False

    def auth_login(self):
        """
        登录
        """
        try:
            self.browser.load_cookies()
            if self.is_login():
                logging.info("cookies登录成功")
                return True
        except Exception as e:
            logging.info("cookies登录失败")
            pass

    def select_doctor_one_day(self):
        """选择合适的大夫"""
        hospitalId = self.config.hospitalId
        timePeriod = self.config.timePeriod
        logging.debug("当前挂号日期: " + self.config.date)

        payload = {
            'hosCode': hospitalId,
            'firstDeptCode': self.config.firstDeptCode,
            'secondDeptCode': self.config.secondDeptCode,
            'target': self.config.date
        }
        duty_url = self.duty_url + '?_time=' + str(self.timestamp())
        response = self.browser.post(duty_url, data=payload)
        logging.debug("response data:" + response.text)
        try:
            data = json.loads(response.text)
            if data["resCode"] == 0:
                for duty in timePeriod:
                    for duty_result in data['data']:
                        if (duty_result['dutyCode'] == duty):
                            self.dutys = duty_result['detail']
                            doctor = self.select_doctor_by_vec()
                            if doctor == 'NoDuty' or doctor == 'NotReady':
                                continue
                            return doctor
                return 'NoDuty'
        except Exception as e:
            logging.error(repr(e))
            sys.exit()

    def select_doctor_by_vec(self):
        if len(self.dutys) == 0:
            return "NotReady"
        doctors = self.dutys
        if self.config.assign == 'true':  # 指定医生
            for doctor_conf in self.config.doctorName:
                for doctor in doctors:
                    if self.get_doctor_name(doctor) == doctor_conf:
                        logging.info("选中:" + self.get_doctor_name(doctor))
                        return doctor
            return "NoDuty"
        # 按照配置优先级选择医生
        for doctor_conf in self.config.doctorName:
            for doctor in doctors:
                if self.get_doctor_name(doctor) == doctor_conf and doctor['totalCount'] % 2 != 0:
                    return doctor


        if len(doctors) != 0:
            logging.info("选中:" + self.get_doctor_name(doctors[0]))
            return doctors[0]
        return "NoDuty"

    def get_doctor_name(self, doctor):
        if doctor['doctorName'] is not None:
            return str(doctor['doctorName'])
        else:
            return str(doctor['doctorTitleName'])


    def confirm(self, uniqProductKey):
        payload = {
            "dutyTime": 0,
            "firstDeptCode": self.config.firstDeptCode,
            "hosCode": self.config.hospitalId,
            "secondDeptCode": self.config.secondDeptCode,
            "target": self.config.date,
            "uniqProductKey": uniqProductKey
        }
        response = self.browser.post(self.confirm_url, data=payload)
        data = json.loads(response.text)
        if data["resCode"] == 0:
            return data["data"]["confirmToken"]

    def get_it(self, doctor, confirmToken):
        """
        挂号
        """
        hospitalCardId = self.config.hospitalCardId
        card_type = self.config.cardType
        payload = {
            "cardNo": hospitalCardId,  # 就诊卡号
            "cardType": card_type,
            "confirmToken": confirmToken,
            "uniqProductKey": doctor["uniqProductKey"],
            "smsCode": "",
            "firstDeptCode": self.config.firstDeptCode,
            "hosCode": self.config.hospitalId,
            "secondDeptCode": self.config.secondDeptCode,
            "dutyTime": doctor["period"][0]["dutyTime"],  # 挂最早的号
            "treatmentDay": self.config.date,
            "hospitalCardId": "",
            "phone": self.config.phoneNumber,
            "orderFrom": "OTHER",
            "contactRelType": "CONTACT_OTHER",
        }
        response = self.browser.post(self.save_url, data=payload)
        logging.debug("payload:" + json.dumps(payload))
        logging.debug("response data:" + response.text)

        try:
            data = json.loads(response.text)
            if data["resCode"] == 0:
                logging.info("挂号成功")
                return True
            if data["resCode"] == 8008:
                logging.error(data["msg"])
                return True
            else:
                logging.error(data["msg"])
                return False

        except Exception as e:
            logging.error(repr(e))
            time.sleep(1)

    def timestamp(self):
        return int(round(time.time() * 1000))

    def get_duty_time(self):
        """获取放号时间"""
        duty_time_url = self.query_hospital_url + "?_time=" + str(self.timestamp()) + "&hosCode=" + str(self.config.hospitalId)
        print(duty_time_url)
        response = self.browser.get(duty_time_url, "")
        ret = response.text
        print(ret)
        data = json.loads(ret)
        if data['resCode'] == 0:
            # 放号时间
            refresh_time = data['data']['openTimeView']
            # 放号日期范围
            appoint_day = data['data']['bookingRange']
            today = datetime.date.today()
            # 优先确认最新可挂号日期
            self.stop_date = today + datetime.timedelta(days=int(appoint_day-1))
            logging.info("今日可挂号到: " + self.stop_date.strftime("%Y-%m-%d"))
            # 自动挂最新一天的号
            if self.config.date == 'latest':
                self.config.date = self.stop_date.strftime("%Y-%m-%d")
                logging.info("当前挂号日期变更为: " + self.config.date)
            # 生成放号时间和程序开始时间
            con_data_str = self.config.date + " " + refresh_time + ":00"
            self.start_time = datetime.datetime.strptime(con_data_str, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(
                days=1-int(appoint_day))
            logging.info("放号时间: " + self.start_time.strftime("%Y-%m-%d %H:%M"))


    def lazy(self):
        cur_time = datetime.datetime.now() + datetime.timedelta(seconds=int(time.timezone + 8 * 60 * 60))
        if self.start_time > cur_time:
            seconds = (self.start_time - cur_time).total_seconds()
            logging.info("距离放号时间还有" + str(seconds) + "秒")
            hour = seconds // 3600
            minute = (seconds % 3600) // 60
            second = seconds % 60
            logging.info(
                "距离放号时间还有" + str(int(hour)) + " h " + str(int(minute)) + " m " + str(int(second)) + " s")

            sleep_time = seconds - 60
            if sleep_time > 0:
                logging.info("程序休眠" + str(sleep_time) + "秒后开始运行")
                if sleep_time > 3600:
                    sleep_time -= 60
                    for i in trange(1000):
                        for j in trange(int(sleep_time / 1000), leave=False, unit_scale=True):
                            time.sleep(1)
                else:
                    for i in tqdm(range(int(sleep_time) - 60)):
                        time.sleep(1)

                # 自动重新登录
                self.auth_login()

    def run(self):
        """主逻辑"""
        self.get_duty_time()
        self.auth_login()  # 1. 登录
        self.lazy()  # 2. 等待抢号
        while True:
            doctor = self.select_doctor_one_day()  # 3. 选择医生
            if doctor == "NoDuty":
                # 如果当前时间 > 放号时间 + 30s
                if self.start_time + datetime.timedelta(seconds=30) < datetime.datetime.now():
                    # 确认无号，终止程序
                    logging.info("没号了,亲~,休息一下继续刷")
                    time.sleep(1)
                else:
                    # 未到时间，强制重试
                    logging.debug("放号时间: " + self.start_time.strftime("%Y-%m-%d %H:%M"))
                    logging.debug("当前时间: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
                    logging.info("没号了,但截止时间未到，重试中")
                    time.sleep(1)
            elif doctor == "NotReady":
                logging.info("好像还没放号？重试中")
                time.sleep(1)
            else:
                confirmToken = self.confirm(doctor["uniqProductKey"])
                result = self.get_it(doctor, confirmToken)  # 4.挂号
                if result:
                    break  # 挂号成功


if __name__ == "__main__":
    guahao = Guahao()
    guahao.run()
