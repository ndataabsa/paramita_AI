import urllib.request
import datetime
from dateutil.relativedelta import relativedelta
import time
from bs4 import BeautifulSoup
import random

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys

from pyvirtualdisplay import Display
import subprocess
import platform

import os
from selenium.webdriver.support.ui import Select
import pandas as pd
import requests
import traceback
import subprocess

def is_port_in_use(port):
    result = subprocess.run(['ss', '-tuln'], stdout=subprocess.PIPE)
    output = result.stdout.decode('utf-8')
    return f":{port}" in output  # 포트가 사용 중인지 확인

def find_free_port(start_port=9222, end_port=9300):
    for port in range(start_port, end_port + 1):
        if not is_port_in_use(port):
            return port
    return None  # 사용할 수 있는 포트가 없을 경우


class engine:
    def __init__(self):
        self.drivers = {}
        self.download_path = '/sele_download'
        
    def start(self,url='',silent=False,dis=False,profile='/tmp/selenium-profile',profile_name='Default'): 
        try:         
            if url=='': url=f'https://www.google.com'
            
            if dis:
                try:               
                    display = Display(visible=0, size=(1920, 1080))
                    display.start()     
                    free_port = find_free_port()
                    if not free_port :
                        print('사용 가능한 포트가 없습니다.')
                        return None
                    
                    # 2. Chrome 브라우저 수동 실행 (9222 디버깅 모드)
                    chrome_page=subprocess.Popen([
                        "google-chrome",
                        f"--remote-debugging-port={free_port}",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        f"--user-data-dir={profile}", 
                        f"--profile-directory={profile_name}",
                        "--window-size=1920,1080",
                        "--start-maximized",
                        f"{url}" 
                    ])
                    
                    
                    time.sleep(3)  # 브라우저 시작 대기
                    
                    # 3. Selenium으로 실행 중인 브라우저에 연결
                    chrome_options = webdriver.ChromeOptions()
                    chrome_options.debugger_address = f"127.0.0.1:{free_port}"
                    
                    driver = webdriver.Chrome(options=chrome_options)
                    
                    # 4. 탐지 우회용 자바스크립트 삽입 (Selenium 흔적 제거)
                    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                        "source": """
                            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
                            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
                            Object.defineProperty(navigator, 'connection', { get: () => ({ downlink: 10, effectiveType: '4g' }) });
                            window.chrome = { runtime: {} };
                        """
                    })
                    driver_num = len(self.drivers)
                    self.drivers[driver_num] = {
                        'driver': driver,
                        'display': display,
                        'chrome_page': chrome_page
                    }
                    return driver
                except Exception as E:
                    print(f'오류 발생\n\n{E}')
                    chrome_page.terminate()
                    return None
            else:
                option=webdriver.ChromeOptions()
                if str(platform.platform()).find('Window')>-1:
                    option.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36")
                    option.add_argument("lang=ko-KR,ko,en-US,en")
                    option.add_argument("disable-blink-features=AutomationControlled")  
                    option.add_experimental_option("excludeSwitches", ["enable-automation"]) 
                    option.add_experimental_option('useAutomationExtension', False)  
                    option.add_argument("referer=https://www.google.com/")
                    option.add_argument("--incognito")
                    option.headless = False
                    pass
                else:
                    option.add_argument('--headless')
                    option.add_argument('--no-sandbox')
                    option.add_argument("--disable-dev-shm-usage")
                    option.add_argument('headless')
                    option.add_argument('window-size=1920,1080')
                    option.add_argument("disable-gpu")
                    option.add_argument('--headless=new')
                    option.add_argument('--no-sandbox')
                    option.add_argument("--disable-dev-shm-usage")
                    option.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36")
                    option.add_argument("lang=ko-KR,ko,en-US,en")
                    option.add_argument('incognito')
                    option.add_argument('--silent')
                    
                if str(platform.platform()).find('Window')>-1:
                    option.add_experimental_option('prefs',{'download.default_directory':r'C:\CW_DOWNLOAD',"download.prompt_for_download": False,"download.directory_upgrade": True,"safebrowsing.enabled": True})  
                    driver = webdriver.Chrome("chromedriver.exe",options=option)
                    driver.maximize_window()
                else:
                    if not os.path.exists(self.download_path):os.makedirs(self.download_path)
                        
                    option.add_experimental_option('prefs',{'download.default_directory':self.download_path,"download.prompt_for_download": False,"download.directory_upgrade": True,"safebrowsing.enabled": True})  
                    #driver = webdriver.Chrome(os.getcwd()+"/chromedriver",options=option)
                    driver = webdriver.Chrome(options=option)
                    
                
                driver.get(f'https://www.google.com')
                driver.execute_script("""window.performance = {}; window.chrome = { runtime: {} };""")
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
                WebDriverWait(driver, 2) 
                driver.get(url)
                driver_num = len(self.drivers)
                self.drivers[driver_num] = {
                    'driver': driver,
                    'display': None,
                    'chrome_page': None
                }
                
                if not silent:print(f'엔진 :{driver_num}:으로 지정됨')
                return driver
        except Exception as E:
            print('selenium driver를 불러오는데 실패했습니다.')
            traceback.print_exc()
            
    
    def wait(self,num,time=2):
        WebDriverWait(self.drivers[num]['driver'], time) 
    
    def wait_xpath(self,num,xpath,time=2):
        WebDriverWait(self.drivers[num]['driver'], time).until(EC.presence_of_element_located((By.XPATH, xpath)))




    
    def find_element(self, driver_num, find_item, option='xpath'):
        if not isinstance(find_item, str):
            return find_item
            
        if option == 'xpath':
            if not find_item.startswith('/'):
                find_item = '//' + find_item
            return self.drivers[driver_num]['driver'].find_element(By.XPATH, find_item)
        elif option == 'class':
            return self.drivers[driver_num]['driver'].find_element(By.CLASS_NAME, find_item)
        elif option == 'id':
            return self.drivers[driver_num]['driver'].find_element(By.ID, find_item)
        elif option == 'css':
            return self.drivers[driver_num]['driver'].find_element(By.CSS_SELECTOR, find_item)
        elif option == 'text':
            return self.drivers[driver_num]['driver'].find_element(By.XPATH, f"//*[text()='{find_item}']")
        else:
            print('fail to select: invalid option')
            return None

    def do_click(self,driver_num,find_item,option='xpath'):
        find_item = self.find_element(driver_num, find_item, option)
        if find_item is None:
            return False
        actions = ActionChains(self.drivers[driver_num]['driver'])
        actions.move_to_element(find_item).pause(0.5).click().perform()
        return True
    
    def do_clear(self, num, find_item, option='xpath', speed=0.1):
        element = self.find_element(num, find_item, option)
        if element is None:
            return False
            
        if not self.do_click(num, find_item, option):
            return False
            
        current_text = element.get_attribute('value')
        if current_text:
            for _ in range(len(current_text)):
                actions = ActionChains(self.drivers[num]['driver'])
                actions.send_keys(Keys.BACKSPACE)
                actions.perform()
                time.sleep(random.uniform(speed * 0.8, speed * 1.2))
        
        return True

    def do_text(self, num, find_item, text, option='xpath', speed=0.1):
        element = self.find_element(num, find_item, option)
        if element is None:
            return False
            
        if not self.do_clear(num, find_item, option, speed):
            return False
        
        for char in text:
            actions = ActionChains(self.drivers[num]['driver'])
            actions.send_keys(char)
            actions.perform()
            time.sleep(random.uniform(speed * 0.8, speed * 1.2))
            
        return True
    
    def do_enter(self, num):
        actions = ActionChains(self.drivers[num]['driver'])
        actions.send_keys(Keys.RETURN)
        actions.perform()
        return True
    
    def do_click_bak(self,driver_num,find_item,option='xpath'):
        find_item = self.find_element(driver_num, find_item, option)
        if find_item is None:
            return False
            
        find_item.click()
        return True
    
    def do_select(self,driver_num,find_item,find_data,option='xpath'):
        find_item = self.find_element(driver_num, find_item, option)
        if find_item is None:
            return False
            
        select = Select(find_item)
        
        if isinstance(find_data,int):
            select.select_by_index(find_data) 
        elif isinstance(find_data,str):
            try:
                select.select_by_value(find_data) 
            except:
                try:
                    select.select_by_visible_text(find_data) 
                except:
                    print('there are no select item')
                    return False
        return True

    def switch(self,num,xpath=''):
        if xpath!='':self.drivers[num]['driver'].switch_to.frame(self.drivers[num]['driver'].find_element(By.XPATH,xpath))
        else: self.drivers[num]['driver'].switch_to.default_content()

    def scroll(self,num,sleep=0.5,max_time=3):
        do=0
        last_height=0
        new_height=0
        while do<max_time:
            last_height = self.drivers[num]['driver'].execute_script("return document.documentElement.scrollHeight")
            self.drivers[num]['driver'].execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            WebDriverWait(self.drivers[num]['driver'], sleep*0.8) 
            time.sleep(sleep*0.2)
            new_height = self.drivers[num]['driver'].execute_script("return document.documentElement.scrollHeight")
            do+=1
            
        if new_height == last_height:return False
        return True
    
    
    def smooth_scroll(self, num, sleep=0.1, max_time=3, speed_variation=0.05):
        start_scroll = self.drivers[num]['driver'].execute_script("return window.scrollY")
        end_scroll = self.drivers[num]['driver'].execute_script("return document.documentElement.scrollHeight")
        
        steps = int(max_time / sleep)
        scroll_distance = (end_scroll - start_scroll) / steps
        
        for step in range(steps):
            self.drivers[num]['driver'].execute_script(f"window.scrollBy(0, {scroll_distance});")
            rand_sleep = random.uniform(sleep - speed_variation, sleep + speed_variation)
            time.sleep(rand_sleep)
        
        final_scroll = self.drivers[num]['driver'].execute_script("return window.scrollY")
        return final_scroll < end_scroll - 1
    
    def scroll_px(self, num,size=50):
        self.drivers[num]['driver'].execute_script(f"window.scrollBy(0, -{size});")
        return True
    
    def scroll_to_element(self, num, find_item, option='xpath'):
        element = self.find_element(num, find_item, option)
        if element is None:
            return False
            
        self.drivers[num]['driver'].execute_script("arguments[0].scrollIntoView(true);", element)
        return True

    def smooth_scroll_to_element(self, num, find_item, option='xpath', sleep=0.1, speed=300, speed_variation=0.05, max_time=100000):
        element = self.find_element(num, find_item, option)
        if element is None:
            return False
            
        element_position = element.location['y']
        start_scroll = self.drivers[num]['driver'].execute_script("return window.scrollY")
        current_scroll = start_scroll
        page_height = self.drivers[num]['driver'].execute_script("return document.documentElement.scrollHeight")
        
        direction = 1 if element_position > current_scroll else -1
        scroll_distance = speed * random.uniform(0.8, 1.2) * direction
        
        for vv in range(max_time):
            self.drivers[num]['driver'].execute_script(f"window.scrollBy(0, {scroll_distance});")
            rand_sleep = random.uniform(sleep - speed_variation, sleep + speed_variation)
            time.sleep(rand_sleep)
    
            current_scroll = self.drivers[num]['driver'].execute_script("return window.scrollY")
            
            if current_scroll <= 0 and direction == -1:
                return True
            
            if direction == 1 and current_scroll + self.drivers[num]['driver'].execute_script("return window.innerHeight") >= page_height:
                return True

            if (direction == 1 and current_scroll >= element_position) or (direction == -1 and current_scroll <= element_position):
                return True

        return False

#     def smooth_scroll_to_element(self, num, xpath, sleep=0.1, max_time=3, speed_variation=0.05):
#     # 요소를 XPath로 찾아 그 위치를 구합니다.
#         element = self.drivers[num].find_element(By.XPATH, xpath)
        
#         # 요소의 Y 위치를 얻습니다.
#         element_position = element.location['y']
        
#         # 현재 스크롤 위치를 가져옵니다.
#         start_scroll = self.drivers[num].execute_script("return window.scrollY")
#         end_scroll = self.drivers[num].execute_script("return document.documentElement.scrollHeight")
        
#         # 목표 시간 동안 일정한 간격으로 스크롤을 내리기 위한 단계를 계산합니다.
#         steps = int(max_time / sleep)  # sleep에 따라 스크롤의 횟수와 속도 조절
        
#         # 스크롤 한 번에 내려갈 거리 (전체 페이지 스크롤을 나눔)
#         scroll_distance = (end_scroll - start_scroll) / steps
        
#         # 요소가 현재 스크롤보다 위에 있는지 아래에 있는지 확인합니다.
#         if element_position > start_scroll:
#             # 요소가 현재 스크롤보다 아래에 있으면 아래로 스크롤
#             direction = 1  # 1이면 아래로 스크롤
#         else:
#             # 요소가 현재 스크롤보다 위에 있으면 위로 스크롤
#             direction = -1  # -1이면 위로 스크롤
        
#         # 스크롤이 특정 요소에 도달할 때까지 반복합니다.
#         for step in range(steps):
#             # 매 스텝마다 스크롤을 내리되, 랜덤한 오차를 넣어줍니다
#             self.drivers[num].execute_script(f"window.scrollBy(0, {direction * scroll_distance});")
            
#             # speed_variation에 따라 속도를 미세하게 변화시킵니다
#             rand_sleep = random.uniform(sleep - speed_variation, sleep + speed_variation)
            
#             # 일정한 간격으로 sleep을 주어 사람이 스크롤하는 것처럼 보이게 합니다
#             time.sleep(rand_sleep)
    
#             # 현재 스크롤 위치를 가져옵니다
#             current_scroll = self.drivers[num].execute_script("return window.scrollY")
            
#             # 요소가 화면에 나타났다면 종료
#             if (direction == 1 and current_scroll >= element_position) or (direction == -1 and current_scroll <= element_position):
#                 print(f"Element found at scroll position {current_scroll}, stopping scroll.")
#                 return True
        
#     # 만약 최대 시간 동안 요소가 보이지 않으면 실패
#         print("Element not found within the scroll duration.")
#         return False
    
    
    
    
    
    def scroll_end(self,num,sleep=0.5,max_time=1000000):
        do=0
        checker=2;
        last_height = self.drivers[num]['driver'].execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        html = self.drivers[num]['driver'].find_element(By.TAG_NAME,'body')
        while do<max_time:
            self.drivers[num]['driver'].execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            html.send_keys(Keys.PAGE_DOWN)
            time.sleep(sleep)
            new_height = self.drivers[num]['driver'].execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                checker-=1;
                if checker==0:return False
            else: checker=5
            last_height = new_height  # 마지막 높이를 업데이트
            do+=1
        return True
            
    def scroll_end2(self,num,sleep=0.5,max_time=1000000):
        try:
            do=1
            while do<max_time:
                if do%10000==0:print()
                if do%1000==0:print(do,end='')
                # 현재 스크롤 위치
                scroll_position = self.drivers[num]['driver'].execute_script("return window.scrollY")
                # 전체 페이지 높이
                total_height = self.drivers[num]['driver'].execute_script("return document.body.scrollHeight")
                
                # 현재 뷰포트 높이
                viewport_height = self.drivers[num]['driver'].execute_script("return window.innerHeight")
                print(f"Total Height: {total_height}, Scroll Position: {scroll_position}, Viewport Height: {viewport_height}")
                # 스크롤 가능한지 확인
                if scroll_position + viewport_height < total_height:
                    self.drivers[num]['driver'].execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(sleep)  # 페이지 로드 대기
                else:
                    break
                do+=1
        
        except KeyboardInterrupt:
            print("스크롤 중단")
            
    def get_element_xpath(self,num,xpath):
        return self.drivers[num]['driver'].find_element(By.XPATH,xpath)
        
    def end(self,driver):
        if isinstance(driver,int):
            try:
                self.drivers[driver]['driver'].quit()
                if self.drivers[driver]['display']:
                    self.drivers[driver]['display'].stop()
                if self.drivers[driver]['chrome_page']:
                    self.drivers[driver]['chrome_page'].terminate()
                del self.drivers[driver]
            except:
                print(f'엔진 :{driver}:종료 실패')
        else:
            for driver_num, driver_info in self.drivers.items():
                if driver_info['driver'] == driver:
                    driver_info['driver'].quit()
                    if driver_info['display']:
                        driver_info['display'].stop()
                    if driver_info['chrome_page']:
                        driver_info['chrome_page'].terminate()
                    del self.drivers[driver_num]
                    break
    
    def quit(self):
        for driver_num in list(self.drivers.keys()):
            self.drivers[driver_num]['driver'].quit()
            if self.drivers[driver_num]['display']:
                self.drivers[driver_num]['display'].stop()
            if self.drivers[driver_num]['chrome_page']:
                self.drivers[driver_num]['chrome_page'].terminate()
            del self.drivers[driver_num]