from selenium import webdriver
import pymysql
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import hashlib
import requests
import time


def send_wx(trans, text, href):
    time.sleep(1)  # 习惯性延迟
    res = requests.post('https://wxpusher.zjiecode.com/api/send/message', json={
        'appToken': 'diaoqiAT_25MuTSIpMdyOoO88l4RVn7jpsu3GwxU9',
        'content': f'<h1>{trans}</h1><p>{text}</p><p>原文链接(国外)：<br/>{href}</p>',
        'summary': trans,
        'contentType': 2,
        'topicIds': [32804],
        'url': href,
        'verifyPayType': 0
    })
    json = res.json()
    try:
        print('微信发送', json['msg'])
    except KeyError:
        print('发送微信失败：', KeyError)


def fanyi(text):  # 百度翻译API
    time.sleep(1)  # 每秒最多调用一次
    appid = '20240821002129160'
    secret = 'diaoqiE93NoddGQ1zG4WX4zhki'
    salt = '123'
    str = f'{appid}{text}{salt}{secret}'
    md5_hash = hashlib.md5()
    md5_hash.update(str.encode('utf-8'))
    sign = md5_hash.hexdigest()
    params = {'q': text, 'from': 'auto', 'to': 'zh', 'appid': appid, 'salt': salt, 'sign': sign}
    res = requests.get('https://fanyi-api.baidu.com/api/trans/vip/translate', params=params)
    json = res.json()
    try:
        translate = json['trans_result'][0]['dst']
    except KeyError:
        translate = text
    print('翻译结果: ', translate)
    return translate


def insert_one(text, href):  # 插入一条数据到数据库
    # 先翻译
    trans = fanyi(text)
    sql = "INSERT INTO message_list (message, time, trans, link) VALUES (%s, %s, %s, %s)"
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 获取当前时间并格式化
    cursor.execute(sql, (text, current_time, trans, href))
    connection.commit()  # 提交事务
    send_wx(trans, text, href)


config = {
    'host': '172.245.156.24',
    'user': 'diaoqi',
    'password': 'd6-',
    'database': 'bloomberg',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor  # 使用字典格式的游标
}

options = Options()

prefs = {"profile.managed_default_content_settings.images": 2}
options.add_experimental_option("prefs", prefs)

# driver = webdriver.Chrome(options=options)
driver = webdriver.Chrome()
url = 'https://www.bloomberg.com/asia'
driver.get(url)

section = driver.find_element(By.CSS_SELECTOR, 'section[data-zoneid="Above the Fold"]')
a_elements = section.find_elements(By.CSS_SELECTOR, 'a[class*="StoryBlock_storyLink_"]')

connection = pymysql.connect(**config)
cursor = connection.cursor()
for a in a_elements:
    # 有些a标签里面的标题不是重要标题，强行获取导致报错则continue进入下一次循环
    try:
        div = a.find_element(By.XPATH,
                             ".//div[contains(@class, 'Headline_large__3__hG') and (contains(@class, 'storyBlockHeadline'))]")
        span = div.find_element(By.TAG_NAME, 'span')
        href = a.get_attribute('href')
        text = span.text

        sql = "SELECT COUNT(*) FROM message_list WHERE message = %s"
        cursor.execute(sql, (text,))  # 注意：参数需要是一个元组
        result = cursor.fetchone()  # 获取查询结果，因为COUNT查询只返回一个值所以使用fetchone
        count = result['COUNT(*)'] if result else 0  # 获取数量，如果结果为空则设为0
        if count == 0:  # 表里没有，插一条
            insert_one(text, href)
        else:
            print('数据已存在库中')
    except Exception as e:
        continue

time.sleep(5)
cursor.close()
connection.close()
driver.quit()
