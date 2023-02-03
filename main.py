import os
from Parsing import my_env
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as E_C
from selenium.webdriver.chrome.options import Options
from time import sleep
from datetime import date, timedelta
from pymongo import MongoClient

# Для обработки даты в почтовом ящике создаём переменные сегодня и вчера.
_today = date.today()
_yesterday = date.today() - timedelta(days=1)

c = Service('./chromedriver.exe')
chromeOptions = Options()
chromeOptions.add_argument('start-maximized')
driver = webdriver.Chrome(service=c, options=chromeOptions)

client = MongoClient('127.0.0.1:27017')
db = client.parse['mail']

driver.get('https://account.mail.ru/login')
login = driver.find_element(By.XPATH, '//input[@class="input-0-2-77"]')
login.send_keys(os.environ.get('mail_login'))
login.send_keys(Keys.ENTER)

wait = WebDriverWait(driver, 10)
wait.until(E_C.element_to_be_clickable((By.XPATH, '//input[@name="password"]')))
pass_word = driver.find_element(By.XPATH, '//input[@name="password"]')
pass_word.send_keys(os.environ.get('mail_pass'))
sleep(1)
pass_word.send_keys(Keys.ENTER)

def clean_text(obj:str): # Функция очистки текста.
    return ' '.join(obj.split())

def clean_date(obj:str): # Функция очистки даты
    if obj.split(',')[0] == 'Вчера':
        return ''.join([str(_yesterday.day), ' ', str(_yesterday.month), ', ', obj[-5:]])
    elif obj.split(',')[0] == 'Сегодня':
        return ''.join([str(_today.day), ' ', str(_today.month),', ', obj[-5:]])
    else:
        return obj

def letter_parse(): # Функция для обработки писем, собираем - складываем в словарь - вставляем в mongo.
    letter_dict = dict()
    driver.implicitly_wait(10)
    # wait = WebDriverWait(driver, 10)
    # wait.until(E_C.visibility_of_element_located((By.XPATH, '//span[@class = "letter-contact"]')))

    letter_dict['header'] = driver.find_element(By.XPATH, '//h2[@class="thread-subject thread-subject_pony-mode"]').text
    letter_dict['sender'] = driver.find_element(By.XPATH, '//div[@class="letter__author"]/span').text
    letter_dict['sender_address'] = driver.find_element(By.XPATH, '//div[@class="letter__author"]/span').get_attribute('title')
    letter_dict['letter_date'] = clean_date(driver.find_element(By.XPATH, '//div[@class="letter__author"]/div').text)
    letter_dict['letter_body'] = clean_text(driver.find_element(By.XPATH, '//div[@class = "letter__body"]').text)
    db.insert_one(letter_dict)
    # print(letter_dict)

''' Сначала была идея собирать список писем-ссылок, прокручивая экран. Далее обрабатывать этот список.
Но... Позднее на страничке письма обнаружил кнопки "Следующее" - "Предыдущее". Т.о. мы находим первое письмо,
заходим в него, обрабатываем, далее путешествуем по письмам нажимая на кнопку "Следующее". В цикле стоит проверка на доступность
этой кнопки - это условие остановки (либо набор определенного количества писем.) 
    Возможная причина сбоя - нет проверки на наличие в почтовом ящике хотя бы одного письма.'''

wait.until(E_C.element_to_be_clickable((By.XPATH, '//div[@class="ReactVirtualized__Grid__innerScrollContainer"]/a')))
letter_first = driver.find_element(By.XPATH, '//div[@class="ReactVirtualized__Grid__innerScrollContainer"]/a')

driver.get(letter_first.get_attribute('href'))
letter_parse()
next_letter = driver.find_element(By.XPATH, '//span[@title = "Следующее"] | //span[@data-title = "Следующее"]')
n = 1
while not next_letter.get_attribute('disabled') and n < 50:
    n += 1
    next_letter.click()
    # Тут пришлось использовать sleep не смог подобрать функцию из E_C.
    sleep(2)
    letter_parse()
    next_letter = driver.find_element(By.XPATH, '//span[@title = "Следующее"] | //span[@data-title = "Следующее"]')
