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

import platform
if platform.system() != 'Windows':
    from pyvirtualdisplay import Display
import subprocess
import os
from selenium.webdriver.support.ui import Select
import pandas as pd
import requests
import traceback
import socket
import re
import sys
import psutil

from CLASS.data_result import DATA_Result

def is_port_in_use(port):
    if platform.system() == 'Windows':
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return False
            except socket.error:
                return True
    else:
        result = subprocess.run(['ss', '-tuln'], stdout=subprocess.PIPE)
        output = result.stdout.decode('utf-8')
        return f":{port}" in output

def find_free_port(start_port=9222, end_port=9300):
    for port in range(start_port, end_port + 1):
        if not is_port_in_use(port):
            return port
    return None  # 사용할 수 있는 포트가 없을 경우


class engine:
    def __init__(self):
        self.drivers = {}
        self.download_path = '/sele_download'
        
    def start(self,url='',silent=False,dis=False,profile='/tmp/selenium-profile',profile_name='Default',timeout=1440): 
        try:
            print("A")
            if url=='': url=f'https://www.google.com'
            if dis:
                print("B")
                try:
                    # Windows가 아닐 경우에만 virtual display 사용
                    display = None
                    if platform.system() != 'Windows':
                        display = Display(visible=0, size=(1920, 1080))
                        display.start()
                    free_port = find_free_port()
                    if not free_port:
                        return None
                    print("D")
                    # 2. Chrome 브라우저 수동 실행 (9222 디버깅 모드)
                    if platform.system() == 'Windows':
                        # Windows에서 Chrome 실행 파일 찾기
                        chrome_paths = [
                            os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google\\Chrome\\Application\\chrome.exe'),
                            os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google\\Chrome\\Application\\chrome.exe'),
                            os.path.join(os.environ.get('LOCALAPPDATA', 'C:\\Users\\%USERNAME%\\AppData\\Local'), 'Google\\Chrome\\Application\\chrome.exe')
                        ]
                        
                        chrome_exe = None
                        for path in chrome_paths:
                            if os.path.exists(path):
                                chrome_exe = path
                                break
                                
                        if not chrome_exe:
                            raise Exception("Chrome 실행 파일을 찾을 수 없습니다.")
                            
                        chrome_options = [
                            chrome_exe,
                            f"--remote-debugging-port={free_port}",
                            f"--user-data-dir={profile}", 
                            f"--profile-directory={profile_name}",
                            "--window-size=1920,1080",
                            "--start-maximized",
                            f"{url}"
                        ]
                    else:
                        chrome_options = [
                            "google-chrome",
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            f"--remote-debugging-port={free_port}",
                            f"--user-data-dir={profile}", 
                            f"--profile-directory={profile_name}",
                            "--window-size=1920,1080",
                            "--start-maximized",
                            "--lang=ko-KR",
                            f"{url}"
                        ]
                    chrome_page = subprocess.Popen(chrome_options,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                        preexec_fn=os.setsid )
                    timer_process = None
                    max_retries = 10
                    retry_count = 0
                    
                    while retry_count < max_retries:
                        try:
                            # 크롬 옵션 설정
                            chrome_options = webdriver.ChromeOptions()
                            chrome_options.debugger_address = f"127.0.0.1:{free_port}"
                            
                            # 연결 시도
                            driver = webdriver.Chrome(options=chrome_options)
                            break
                        except Exception as e:
                            retry_count += 1
                            if retry_count == max_retries:
                                raise Exception(f"크롬 연결 실패: {str(e)}")
                            time.sleep(1)  # 1초 대기 후 재시도
                    
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
                        'chrome_page': chrome_page,
                        'timer_process': timer_process
                    }
                    return driver
                except Exception as E:
                    if 'chrome_page' in locals():
                        chrome_page.terminate()
                    if 'display' in locals() and display:
                        display.stop()
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
                    'chrome_page': None,
                    'timer_process':None
                }
                
                return driver
        except Exception as E:
            traceback.print_exc()
            
    def wait(self,num,time=2):
        try:
            WebDriverWait(self.drivers[num]['driver'], time)
            return DATA_Result(result=True)
        except Exception as e:
            return DATA_Result(message=str(e))
    
    def wait_xpath(self,num,xpath,time=2):
        try:
            WebDriverWait(self.drivers[num]['driver'], time).until(EC.presence_of_element_located((By.XPATH, xpath)))
            return DATA_Result(result=True)
        except Exception as e:
            return DATA_Result(message=str(e))




    
    def find_element(self, driver_num, find_item, option='xpath'):
        if not isinstance(find_item, str):
            return find_item
            
        try:
            if option == 'xpath':
                if not re.match(r"^(\/|\/\/|\.\/|\.\.\/)", find_item):
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
        except:
            return None

    def do_click(self,driver_num,find_item,option='xpath'):
        try:
            element = self.find_element(driver_num, find_item, option)
            if element is None: 
                return DATA_Result(message="Element not found")
                
            actions = ActionChains(self.drivers[driver_num]['driver'])
            actions.move_to_element(element).pause(0.5).click().perform()
            return DATA_Result(result=True)
        except Exception as e:
            return DATA_Result(message=str(e))
    
    def do_clear(self, num, find_item,max_time=0,  option='xpath', speed=0.1):
        try:
            if find_item is None:element = self.drivers[num]['driver'].switch_to.active_element
            else: element = self.find_element(num, find_item, option)
            if element is None: 
                return DATA_Result(message="Element not found")
                
            if not self.do_click(num, element, option).get_result(): 
                return DATA_Result(message="Click failed")
                
            if max_time == 0:
                value = element.get_attribute('value')
                if not value:value = element.text  
                max_time = len(value or "")

            for _ in range(max_time):
                actions = ActionChains(self.drivers[num]['driver'])
                actions.send_keys(Keys.BACKSPACE)
                actions.perform()
                time.sleep(random.uniform(speed * 0.2, speed * 0.5))
                actions.send_keys(Keys.DELETE)
                actions.perform()
                time.sleep(random.uniform(speed * 0.8, speed * 1.2))
            
            return DATA_Result(result=True)
        except Exception as e:
            return DATA_Result(message=str(e))

    def do_text(self, num, find_item, text, option='xpath', speed=0.1):
        try:
            if find_item is None:element = self.drivers[num]['driver'].switch_to.active_element
            else: element = self.find_element(num, find_item, option)
            if element is None:
                return DATA_Result(message="Element not found")
                
            for char in text:
                actions = ActionChains(self.drivers[num]['driver'])
                actions.send_keys(char)
                actions.perform()
                time.sleep(random.uniform(speed * 0.8, speed * 1.2))
                
            return DATA_Result(result=True)
        except Exception as e:
            return DATA_Result(message=str(e))
    
    def do_enter(self, num):
        try:
            actions = ActionChains(self.drivers[num]['driver'])
            actions.send_keys(Keys.RETURN)
            actions.perform()
            return DATA_Result(result=True)
        except Exception as e:
            return DATA_Result(message=str(e))
    
    def do_pagedown(self, num,find_item, option='xpath', count=1, speed=0.1):
        if num not in self.drivers:
            return DATA_Result(message=str('not found driver'))
             
        if find_item==None:
            driver = self.drivers[num]['driver']
            actions = ActionChains(driver)
            
            for _ in range(count):
                actions.send_keys(Keys.PAGE_DOWN).perform()
                time.sleep(random.uniform(speed * 0.8, speed * 1.2))
            
        else:
            element = self.find_element(num, find_item, option)
            if element is None:
                return DATA_Result(message=str('not found element'))

            # 포커스 주고 PAGE_DOWN 키 입력 반복
            for _ in range(count):
                element.send_keys(Keys.PAGE_DOWN)
                time.sleep(random.uniform(speed * 0.8, speed * 1.2))
        return DATA_Result(result=True)
    
    def do_select(self,driver_num,find_item,find_data,option='xpath'):
        try:
            element = self.find_element(driver_num, find_item, option)
            if element is None:
                return DATA_Result(message="Element not found")
                
            select = Select(element)
            
            if isinstance(find_data,int):
                select.select_by_index(find_data) 
            elif isinstance(find_data,str):
                try:
                    select.select_by_value(find_data) 
                except:
                    try:
                        select.select_by_visible_text(find_data) 
                    except:
                        return DATA_Result(message="No matching select item found")
            return DATA_Result(result=True)
        except Exception as e:
            return DATA_Result(message=str(e))

    def do_radio(self,driver_num,find_item,value=None,option='xpath'):
        try:
            if value is not None:
                # value로 라디오 버튼 찾기
                if option == 'xpath':
                    if not find_item.startswith('/'):
                        find_item = '//' + find_item
                    element = self.drivers[driver_num]['driver'].find_element(By.XPATH, f"{find_item}[@value='{value}']")
                else:
                    element = self.find_element(driver_num, find_item, option)
                    if element.get_attribute('value') != value:
                        return DATA_Result(message="Value mismatch")
            else:
                element = self.find_element(driver_num, find_item, option)
                
            if element is None: 
                return DATA_Result(message="Element not found")
                
            input_type = element.get_attribute('type')
            if input_type not in ['checkbox', 'radio']: 
                return DATA_Result(message="Element is not a checkbox or radio button")
                
            is_selected = element.is_selected()
            actions = ActionChains(self.drivers[driver_num]['driver'])
            actions.move_to_element(element).pause(0.5).click().perform()
            
            time.sleep(0.5)
            new_state = element.is_selected()
            return DATA_Result(result=new_state != is_selected)
        except Exception as e:
            return DATA_Result(message=str(e))
        
    def switch(self,num,xpath=''):
        try:
            if xpath!='':
                self.drivers[num]['driver'].switch_to.frame(self.drivers[num]['driver'].find_element(By.XPATH,xpath))
            else: 
                self.drivers[num]['driver'].switch_to.default_content()
            return DATA_Result(result=True)
        except Exception as e:
            return DATA_Result(message=str(e))

    def scroll(self,num,sleep=0.5,max_time=3):
        try:
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
                
            if new_height == last_height:
                return DATA_Result(message="No more content to scroll")
            return DATA_Result(result=True)
        except Exception as e:
            return DATA_Result(message=str(e))
    
    def smooth_scroll(self, num, sleep=0.1, max_time=3, speed_variation=0.05):
        try:
            start_scroll = self.drivers[num]['driver'].execute_script("return window.scrollY")
            end_scroll = self.drivers[num]['driver'].execute_script("return document.documentElement.scrollHeight")
            
            steps = int(max_time / sleep)
            scroll_distance = (end_scroll - start_scroll) / steps
            
            for step in range(steps):
                self.drivers[num]['driver'].execute_script(f"window.scrollBy(0, {scroll_distance});")
                rand_sleep = random.uniform(sleep - speed_variation, sleep + speed_variation)
                time.sleep(rand_sleep)
            
            final_scroll = self.drivers[num]['driver'].execute_script("return window.scrollY")
            if final_scroll < end_scroll - 1:
                return DATA_Result(result=True)
            return DATA_Result(message="Scroll did not reach the end")
        except Exception as e:
            return DATA_Result(message=str(e))

    def scroll_px(self, num,size=50):
        try:
            self.drivers[num]['driver'].execute_script(f"window.scrollBy(0, -{size});")
            return DATA_Result(result=True)
        except Exception as e:
            return DATA_Result(message=str(e))

    def scroll_to_element(self, num, find_item, option='xpath'):
        try:
            element = self.find_element(num, find_item, option)
            if element is None:
                return DATA_Result(message="Element not found")
                
            self.drivers[num]['driver'].execute_script("arguments[0].scrollIntoView(true);", element)
            return DATA_Result(result=True)
        except Exception as e:
            return DATA_Result(message=str(e))

    def smooth_scroll_to_element(self, num, find_item, option='xpath', sleep=0.1, speed=300, speed_variation=0.05, max_time=100000):
        try:
            element = self.find_element(num, find_item, option)
            if element is None:
                return DATA_Result(message="Element not found")
                
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
                    return DATA_Result(result=True)
                
                if direction == 1 and current_scroll + self.drivers[num]['driver'].execute_script("return window.innerHeight") >= page_height:
                    return DATA_Result(result=True)

                if (direction == 1 and current_scroll >= element_position) or (direction == -1 and current_scroll <= element_position):
                    return DATA_Result(result=True)

            return DATA_Result(message="Scroll timeout")
        except Exception as e:
            return DATA_Result(message=str(e))

    def scroll_end(self,num,sleep=0.5,max_time=1000000):
        try:
            do=0
            checker=2
            last_height = self.drivers[num]['driver'].execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            html = self.drivers[num]['driver'].find_element(By.TAG_NAME,'body')
            while do<max_time:
                self.drivers[num]['driver'].execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                html.send_keys(Keys.PAGE_DOWN)
                time.sleep(sleep)
                new_height = self.drivers[num]['driver'].execute_script("return document.documentElement.scrollHeight")
                if new_height == last_height:
                    checker-=1
                    if checker==0:
                        return DATA_Result(result=True)
                else: 
                    checker=5
                last_height = new_height
                do+=1
            return DATA_Result(message="Scroll timeout")
        except Exception as e:
            return DATA_Result(message=str(e))

    def scroll_end2(self,num,sleep=0.5,max_time=1000000):
        try:
            do=1
            while do<max_time:
                if do%10000==0:print()
                if do%1000==0:print(do,end='')
                scroll_position = self.drivers[num]['driver'].execute_script("return window.scrollY")
                total_height = self.drivers[num]['driver'].execute_script("return document.body.scrollHeight")
                viewport_height = self.drivers[num]['driver'].execute_script("return window.innerHeight")
                print(f"Total Height: {total_height}, Scroll Position: {scroll_position}, Viewport Height: {viewport_height}")
                
                if scroll_position + viewport_height < total_height:
                    self.drivers[num]['driver'].execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(sleep)
                else:
                    return DATA_Result(result=True)
                do+=1
            return DATA_Result(message="Scroll timeout")
        except Exception as e:
            return DATA_Result(message=str(e))

    def get_element_xpath(self,num,xpath):
        try:
            element = self.drivers[num]['driver'].find_element(By.XPATH,xpath)
            return DATA_Result(result=True, message=element)
        except Exception as e:
            return DATA_Result(message=str(e))
        
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
            if self.drivers[driver_num]['driver']:
                self.drivers[driver_num]['driver'].quit()
            if self.drivers[driver_num]['display']:
                self.drivers[driver_num]['display'].stop()
            if self.drivers[driver_num]['chrome_page']:
                self.drivers[driver_num]['chrome_page'].terminate()
            if self.drivers[driver_num]['timer_process']:
                self.drivers[driver_num]['timer_process'].terminate()
            del self.drivers[driver_num]

    def getdriver(self, num):
        """지정된 번호의 driver를 반환합니다."""
        if num not in self.drivers:
            return None
        return self.drivers[num]['driver']
    
    def ctrl_service_stop(self, num):
        try:
            # 드라이버만 종료하고 크롬 프로세스는 유지
            self.drivers[num]['driver'].quit()
            # 드라이버 객체만 삭제하고 display와 chrome_page는 유지
            driver = self.drivers[num]['driver']
            self.drivers[num]['driver'] = None
            return True
        except:
            print(f'엔진 :{num}: service stop 실패')
            return False

    def do_screen_shot(self, driver_num, filename=None):
        """
        현재 페이지의 스크린샷을 찍어서 현재 경로에 저장
        
        Args:
            driver_num: 드라이버 번호
            filename: 저장할 파일명 (기본값: timestamp_screenshot.png)
        
        Returns:
            DATA_Result: 성공/실패 결과
        """
        try:
            driver = self.getdriver(driver_num)
            if not driver:
                return DATA_Result(result=False, message=f"드라이버 {driver_num}를 찾을 수 없습니다.")
            
            # 파일명이 없으면 타임스탬프로 생성
            if not filename:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_screenshot.png"
            
            # 현재 작업 디렉토리에 저장
            current_dir = os.getcwd()
            filepath = os.path.join(current_dir, filename)
            
            # 스크린샷 촬영
            driver.save_screenshot(filepath)
            
            # 파일 생성 후 그룹 쓰기 권한 설정
            try:
                os.chmod(filepath, 0o664)  # rw-rw-r--
            except Exception:
                pass  # 권한 설정 실패시 무시
            
            return DATA_Result(
                result=True, 
                message=f"스크린샷이 저장되었습니다: {filepath}",
                data=filepath
            )
            
        except Exception as e:
            return DATA_Result(
                result=False, 
                message=f"스크린샷 촬영 실패: {str(e)}"
            )
