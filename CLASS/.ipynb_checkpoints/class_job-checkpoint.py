import sys
import os
import traceback
import requests
import json
import pandas as pd

# 상위 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from MODULE.module_engine_parser import parser
import MODULE.connector as DB
import MODULE.elasticconnector as ES
from CLASS.data_result import DATA_Result
from CLASS.class_parser_html import parse

class Job:
    def __init__(self, name, args, data_share_dict):
        self.name = name
        self.args = args
        self.data_share_dict = data_share_dict
        self.driver_number = self.args.get('driver_number', 0)
        self.jobs = []
        
        # SYSTEM_SELENIUM에서 engine 가져오기
        if 'SYSTEM_SELENIUM' in self.data_share_dict:
            self.engine = self.data_share_dict['SYSTEM_SELENIUM']
        else:
            self.engine = None


    def run(self):
        try:
            # selenium이 필요한 타입에서만 element 찾기
            element = None
            if self.args['type'] in ['do', 'find']:
                element = self.find_element()
            if self.args['type'] == 'do':
                if self.args['action'] == 'do_screen_shot':
                    filename = self.args.get('filename')
                    return self.engine.do_screen_shot(self.driver_number, filename)
                if self.args['focus'] == 'current':xpath=None
                elif not element : return DATA_Result(message="Element not found")
                else:xpath = element
                if self.args['action'] == 'click':
                    return self.engine.do_click(self.driver_number, xpath)
                elif self.args['action'] == 'text':
                    return self.engine.do_text(self.driver_number, xpath, self.args['text'], self.args.get('speed',0.1))
                elif self.args['action'] == 'clear':
                    return self.engine.do_clear(self.driver_number, xpath, self.args.get('speed',0.1))
                elif self.args['action'] == 'enter':
                    return self.engine.do_enter(self.driver_number)
                elif self.args['action'] == 'pagedown':
                    return self.engine.do_pagedown(self.driver_number,None)
                elif self.args['action'] == 'radio':
                    return self.engine.do_radio(self.driver_number, xpath, self.args.get('value'))
                elif self.args['action'] == 'scroll':
                    return self.engine.smooth_scroll(self.driver_number, self.args['sleep'], self.args['max_time'], self.args['speed_variation'])
                elif self.args['action'] == 'scroll_to_element':
                    return self.engine.smooth_scroll_to_element(self.driver_number, element, self.args['sleep'], self.args['speed'], self.args['speed_variation'], self.args['max_time'])
                else:
                    return DATA_Result(result=True, message=element.text)
                
            elif self.args['type'] == 'find':
                if not element: 
                    return DATA_Result(message="Element not found")
                
                # 기본 스크래핑 (기존 방식)
                if not self.args.get('find_type'):
                    xpath = element.to_xpath()
                    return self.engine.scrape(self.driver_number, xpath)
                
                if self.args.get('source'):parsed_html = parse(self.args.get('source'))
                else:parsed_html = parse(self.getdriver().page_source)
                
                # find_type 기반 파싱
                if not self.args.get('find_type') or not self.args.get('find_item'):
                    return DATA_Result(result=False, message="find_type과 find_item이 필요합니다")
                
                # attribute 타입인 경우 find_attribute도 필요
                if self.args.get('find_type') == 'attribute' and not self.args.get('find_attribute'):
                    return DATA_Result(result=False, message="attribute 타입의 경우 find_attribute가 필요합니다")
                
                # 함수명 규칙: find_element_{type}_{range} 또는 find_elements_{type}_{range}
                # find_range가 'all'이면 복수형, 아니면 단수형
                find_range = self.args.get('find_ranges', 'self')
                if find_range == 'all':
                    func_name = f"find_elements_{self.args.get('find_type')}_{find_range}"
                else:
                    func_name = f"find_element_{self.args.get('find_type')}_{find_range}"
                
                # 동적 함수 호출
                try:
                    if hasattr(parsed_html, func_name):
                        if self.args.get('find_type') == 'attribute':
                            result_data = getattr(parsed_html, func_name)(self.args.get('find_attribute'), self.args.get('find_item'))
                        else:
                            result_data = getattr(parsed_html, func_name)(self.args.get('find_item'))
                    else:
                        return DATA_Result(result=False, message=f"지원하지 않는 함수: {func_name}")
                except Exception as e:
                    return DATA_Result(result=False, message=f"함수 호출 오류: {str(e)}")
                
                if result_data is None:
                    return DATA_Result(result=False, message=f"{self.args.get('find_type')} '{self.args.get('find_item')}'을 찾을 수 없습니다")
                
                return DATA_Result(result=True, data=result_data)
            
            elif self.args['type'] == 'request':
                request_type = self.args.get('request_type', 'get')
                
                if request_type == 'get':
                    response = requests.get(self.args['url'])
                    if response.status_code == 200:
                        return DATA_Result(result=True, data=response.text)
                    else:
                        return DATA_Result(result=False, message=response.text)
                
                elif request_type == 'post':
                    response = requests.post(self.args['url'], data=self.args['data'])
                    if response.status_code == 200:
                        return DATA_Result(result=True, data=response.text)
                    else:
                        return DATA_Result(result=False, message=response.text)
                
                elif request_type == 'selenium':
                    # Selenium 요청 - engine start 포함
                    url = self.args.get('url', '')
                    wait_time = self.args.get('wait_time', 2)
                    
                    if not url:
                        return DATA_Result(result=False, message="URL이 필요합니다")
                    
                    try:
                        # 기존 SYSTEM_SELENIUM이 있으면 quit하고 새로 생성
                        if 'SYSTEM_SELENIUM' in self.data_share_dict and self.data_share_dict['SYSTEM_SELENIUM'] is not None:
                            try:
                                self.data_share_dict['SYSTEM_SELENIUM'].quit()
                                print("기존 SYSTEM_SELENIUM 엔진이 종료되었습니다.")
                            except:
                                pass
                        
                        # SYSTEM_SELENIUM 새로 생성
                        from MODULE.module_engine_selenium import engine
                        self.data_share_dict['SYSTEM_SELENIUM'] = engine()
                        print("SYSTEM_SELENIUM 엔진이 생성되었습니다.")
                        
                        # engine을 self.engine에 할당
                        self.engine = self.data_share_dict['SYSTEM_SELENIUM']
                        
                        # engine start로 driver 추가 (항상 driver_number 0 사용)
                        self.driver_number = 0
                        new_driver = self.engine.start(url)
                        if new_driver is not None:
                            print(f"드라이버 {self.driver_number}가 {url}로 시작되었습니다.")
                        else:
                            return DATA_Result(result=False, message="드라이버 시작에 실패했습니다.")
                        
                        # 대기 시간
                        if wait_time > 0:
                            import time
                            time.sleep(wait_time)
                        
                        # 페이지 소스 반환
                        page_source = self.getdriver().page_source
                        return DATA_Result(result=True, data=page_source, message=f"Selenium으로 {url} 접속 완료")
                        
                    except Exception as e:
                        return DATA_Result(result=False, message=f"Selenium 요청 실패: {str(e)}")
                
                elif request_type == 'selenium_url_change':
                    # Selenium URL 변경 - 기존 driver 사용
                    url = self.args.get('url', '')
                    wait_time = self.args.get('wait_time', 2)
                    
                    if not url:
                        return DATA_Result(result=False, message="URL이 필요합니다")
                    
                    try:
                        # 기존 SYSTEM_SELENIUM이 있는지 확인
                        if 'SYSTEM_SELENIUM' not in self.data_share_dict or self.data_share_dict['SYSTEM_SELENIUM'] is None:
                            return DATA_Result(result=False, message="기존 Selenium 드라이버가 없습니다. 먼저 'selenium' 요청으로 드라이버를 시작해주세요.")
                        
                        # engine을 self.engine에 할당
                        self.engine = self.data_share_dict['SYSTEM_SELENIUM']
                        
                        # 현재 driver_number 확인 (기본값 0)
                        if not hasattr(self, 'driver_number'):
                            self.driver_number = 0
                        
                        # 기존 driver로 URL 변경
                        driver = self.getdriver()
                        if driver is None:
                            return DATA_Result(result=False, message="드라이버를 찾을 수 없습니다.")
                        
                        # URL로 이동
                        driver.get(url)
                        print(f"드라이버 {self.driver_number}가 {url}로 이동했습니다.")
                        
                        # 대기 시간
                        if wait_time > 0:
                            import time
                            time.sleep(wait_time)
                        
                        # 페이지 소스 반환
                        page_source = driver.page_source
                        return DATA_Result(result=True, data=page_source, message=f"Selenium으로 {url} 이동 완료")
                        
                    except Exception as e:
                        return DATA_Result(result=False, message=f"Selenium URL 변경 실패: {str(e)}")
                
                else:
                    return DATA_Result(result=False, message=f"지원하지 않는 요청 타입: {request_type}")
                
            elif self.args['type'] == 'data':
                try:
                    if 'from' not in self.args: return DATA_Result(result=False, message="'from' 파라미터가 필요합니다")
                    from_value = self.args['from']
                    if from_value not in self.data_share_dict: return DATA_Result(result=False, message=f"'{from_value}' 키가 data_share_dict에 존재하지 않습니다")
                    
                    data_value = self.data_share_dict[from_value]
                    convert_type = self.args.get('convert_type', '')
                    
                    # 변환 타입이 있으면 각 함수별로 처리
                    if convert_type:
                        # key_to_list 변환 처리
                        if convert_type == 'key_to_list':
                            key_count = self.args.get('key_count', 0)
                            if key_count <= 0:
                                return DATA_Result(result=False, message="key_count가 0보다 커야 합니다")
                            
                            result_list = []
                            for i in range(key_count):
                                key_name = self.args.get(f'key_{i}')
                                if not key_name:
                                    return DATA_Result(result=False, message=f"key_{i} 파라미터가 필요합니다")
                                if key_name not in self.data_share_dict:
                                    return DATA_Result(result=False, message=f"'{key_name}' 키가 data_share_dict에 존재하지 않습니다")
                                result_list.append(self.data_share_dict[key_name])
                            
                            if 'to' in self.args:
                                to_key = self.args['to']
                                self.data_share_dict[to_key] = result_list
                                return DATA_Result(result=True, message=f"{key_count}개의 키 값을 리스트로 변환하여 '{to_key}'에 저장 완료", data=result_list)
                            else:
                                return DATA_Result(result=True, message=f"{key_count}개의 키 값을 리스트로 변환 완료", data=result_list)
                        
                        # Tag 객체나 Tag 배열인지 확인
                        is_tag_object = hasattr(data_value, 'to_html')  # Tag 객체 확인
                        is_tag_array = isinstance(data_value, list) and len(data_value) > 0 and hasattr(data_value[0], 'to_html')  # Tag 배열 확인
                        
                        if not (is_tag_object or is_tag_array):
                            return DATA_Result(result=False, message=f"'{from_value}' 데이터가 Tag 객체 또는 Tag 배열이 아닙니다")
                        
                        if is_tag_object:
                            # 단일 Tag 객체
                            if hasattr(data_value, convert_type):
                                # 각 함수별로 인자 처리
                                if convert_type in ['get_href', 'get_hrefs']:
                                    # href 관련 함수는 추가 인자 필요
                                    href_arg = self.args.get('href_arg', '')
                                    if href_arg:
                                        converted_data = getattr(data_value, convert_type)(href_arg)
                                    else:
                                        converted_data = getattr(data_value, convert_type)()
                                elif convert_type in ['get_text_all', 'get_texts_all', 'get_text_all_tagonly', 'get_text_all_without_script']:
                                    # 텍스트 관련 함수는 추가 인자 필요
                                    text_arg = self.args.get('text_arg', '')
                                    if text_arg:
                                        converted_data = getattr(data_value, convert_type)(text_arg)
                                    else:
                                        converted_data = getattr(data_value, convert_type)()
                                else:
                                    # 기본 함수들 (to_html, to_xpath, to_dataframe)
                                    converted_data = getattr(data_value, convert_type)()
                                
                                if 'to' in self.args:
                                    to_key = self.args['to']
                                    self.data_share_dict[to_key] = converted_data
                                    return DATA_Result(result=True, message=f"'{from_value}'을 {convert_type}로 변환하여 '{to_key}'에 저장 완료", data=converted_data)
                                else:
                                    return DATA_Result(result=True, message=f"'{from_value}'을 {convert_type}로 변환 완료", data=converted_data)
                            else:
                                return DATA_Result(result=False, message=f"'{convert_type}' 변환 메서드가 존재하지 않습니다")
                        else:
                            # Tag 배열
                            if hasattr(data_value[0], convert_type):
                                converted_data = []
                                for tag in data_value:
                                    # 각 함수별로 인자 처리
                                    if convert_type in ['get_href', 'get_hrefs']:
                                        href_arg = self.args.get('href_arg', '')
                                        if href_arg:
                                            converted_data.append(getattr(tag, convert_type)(href_arg))
                                        else:
                                            converted_data.append(getattr(tag, convert_type)())
                                    elif convert_type in ['get_text_all', 'get_texts_all', 'get_text_all_tagonly', 'get_text_all_without_script']:
                                        text_arg = self.args.get('text_arg', '')
                                        if text_arg:
                                            converted_data.append(getattr(tag, convert_type)(text_arg))
                                        else:
                                            converted_data.append(getattr(tag, convert_type)())
                                    else:
                                        converted_data.append(getattr(tag, convert_type)())
                                
                                if 'to' in self.args:
                                    to_key = self.args['to']
                                    self.data_share_dict[to_key] = converted_data
                                    return DATA_Result(result=True, message=f"'{from_value}' 배열을 {convert_type}로 변환하여 '{to_key}'에 저장 완료", data=converted_data)
                                else:
                                    return DATA_Result(result=True, message=f"'{from_value}' 배열을 {convert_type}로 변환 완료", data=converted_data)
                            else:
                                return DATA_Result(result=False, message=f"'{convert_type}' 변환 메서드가 존재하지 않습니다")
                    
                    # 변환 타입이 없으면 그대로 복사
                    if 'to' in self.args:
                        to_key = self.args['to']
                        self.data_share_dict[to_key] = data_value
                        return DATA_Result(result=True, message=f"'{from_value}'에서 '{to_key}'로 데이터 복사 완료", data=data_value)
                    else:
                        return DATA_Result(result=True, message=f"'{from_value}' 데이터 조회 완료", data=data_value)
                        
                except Exception as e:
                    return DATA_Result(result=False, message=str(e))
            
            elif self.args['type'] == 'save':
                try:
                    save_type = self.args.get('save_type', 'excel')
                    to_key = self.args.get('to', '')
                    name = self.args.get('name', '')
                    encoding = self.args.get('encoding', 'utf-8')
                    
                    if not to_key or to_key not in self.data_share_dict: return DATA_Result(result=False, message=f"'{to_key}' 키가 data_share_dict에 존재하지 않습니다")
                    data = self.data_share_dict[to_key]
                    if not isinstance(data, pd.DataFrame): return DATA_Result(result=False, message=f"'{to_key}' 데이터가 DataFrame이 아닙니다")
                    
                    if save_type == 'excel':
                        data.to_excel(name, index=False)
                        return DATA_Result(result=True, message=f"Excel 파일 '{name}' 저장 완료")
                    elif save_type in ['csv', 'txt']:
                        data.to_csv(name, index=False, encoding=encoding)
                        return DATA_Result(result=True, message=f"{save_type.upper()} 파일 '{name}' 저장 완료")
                    elif save_type == 'mysql':
                        try: con, engine = DB.connect('file_hk')
                        except Exception as E: print(E); print('DB 접속 실패'); return DATA_Result(result=False, message="DB 접속 실패")
                        data.to_sql(name, con, if_exists='append', index=False)
                        return DATA_Result(result=True, message=f"MySQL 테이블 '{name}' 저장 완료")
                    elif save_type == 'elasticsearch':
                        es_conn = ES.connector()
                        es_conn.dataframe_to_es(data, name)
                        return DATA_Result(result=True, message=f"Elasticsearch 인덱스 '{name}' 저장 완료")
                    else:
                        return DATA_Result(result=False, message=f"지원하지 않는 저장 타입: {save_type}")
                        
                except Exception as e:
                    return DATA_Result(result=False, message=str(e))
            
            elif self.args['type'] == 'load':
                try:
                    load_type = self.args.get('load_type', 'excel')
                    from_key = self.args.get('from', '')
                    name = self.args.get('name', '')
                    encoding = self.args.get('encoding', 'utf-8')
                    
                    if load_type == 'excel':
                        df = pd.read_excel(name)
                        self.data_share_dict[from_key] = df
                        return DATA_Result(result=True, message=f"Excel 파일 '{name}' 로드 완료")
                    elif load_type in ['csv', 'txt']:
                        df = pd.read_csv(name, encoding=encoding)
                        self.data_share_dict[from_key] = df
                        return DATA_Result(result=True, message=f"{load_type.upper()} 파일 '{name}' 로드 완료")
                    elif load_type == 'mysql':
                        try: con, engine = DB.connect('file_hk')
                        except Exception as E: print(E); print('DB 접속 실패'); return DATA_Result(result=False, message="DB 접속 실패")
                        df = pd.read_sql(f"SELECT * FROM {name}", con)
                        self.data_share_dict[from_key] = df
                        return DATA_Result(result=True, message=f"MySQL 테이블 '{name}' 로드 완료")
                    elif load_type == 'elasticsearch':
                        es_conn = ES.connector()
                        df = es_conn.search_data(name, None)
                        self.data_share_dict[from_key] = df
                        return DATA_Result(result=True, message=f"Elasticsearch 인덱스 '{name}' 로드 완료")
                    else:
                        return DATA_Result(result=False, message=f"지원하지 않는 로드 타입: {load_type}")
                        
                except Exception as e:
                    return DATA_Result(result=False, message=str(e))
            
            elif self.args['type'] == 'wait':
                try:
                    wait_type = self.args.get('wait_type', 'fixed_time')
                    
                    if wait_type == 'fixed_time':
                        time_value = self.args.get('time', 1.0)
                        if not isinstance(time_value, (int, float)) or time_value <= 0:
                            return DATA_Result(result=False, message="time 값은 0보다 큰 숫자여야 합니다")
                        
                        # module_engine_selenium의 engine.wait 사용
                        self.engine.wait(self.driver_number, time_value)
                        return DATA_Result(result=True, message=f"{time_value}초 대기 완료")
                    
                    elif wait_type == 'load_time':
                        # TODO: 로딩 완료 대기 구현
                        return DATA_Result(result=False, message="load_time 기능은 아직 구현되지 않았습니다")
                    
                    else:
                        return DATA_Result(result=False, message=f"지원하지 않는 대기 타입: {wait_type}")
                        
                except Exception as e:
                    return DATA_Result(result=False, message=str(e))
            

            elif self.args['type'] == 'test':
                try:
                    test_type = self.args.get('test_type', 'variable')
                    
                    if test_type == 'variable':
                        name = self.args.get('name', 'test_var')
                        value = self.args.get('value', '')
                        print_result = self.args.get('print_result', True)
                        
                        # 변수 저장
                        self.data_share_dict[name] = value
                        
                        # 출력 여부에 따라 메시지 생성
                        if print_result:
                            message = f"변수 '{name}' = '{value}' 저장 및 출력 완료"
                        else:
                            message = f"변수 '{name}' = '{value}' 저장 완료"
                        
                        return DATA_Result(result=True, message=message)
                    
                    elif test_type == 'list':
                        name = self.args.get('name', 'test_list')
                        items_str = self.args.get('items', '')
                        print_result = self.args.get('print_result', True)
                        
                        # 쉼표로 구분된 문자열을 리스트로 변환
                        try:
                            items = [item.strip() for item in items_str.split(',') if item.strip()]
                        except:
                            items = []
                        
                        # 리스트 저장
                        self.data_share_dict[name] = items
                        
                        # 출력 여부에 따라 메시지 생성
                        if print_result:
                            message = f"리스트 '{name}' = {items} 저장 및 출력 완료"
                        else:
                            message = f"리스트 '{name}' = {items} 저장 완료"
                        
                        return DATA_Result(result=True, message=message)
                    
                    elif test_type == 'dict':
                        name = self.args.get('name', 'test_dict')
                        key_value_pairs_str = self.args.get('key_value_pairs', '')
                        print_result = self.args.get('print_result', True)
                        
                        # 키:값 형태의 문자열을 딕셔너리로 변환
                        try:
                            key_value_pairs = {}
                            pairs = [pair.strip() for pair in key_value_pairs_str.split(',') if pair.strip()]
                            for pair in pairs:
                                if ':' in pair:
                                    key, value = pair.split(':', 1)
                                    key_value_pairs[key.strip()] = value.strip()
                        except:
                            key_value_pairs = {}
                        
                        # 딕셔너리 저장
                        self.data_share_dict[name] = key_value_pairs
                        
                        # 출력 여부에 따라 메시지 생성
                        if print_result:
                            message = f"딕셔너리 '{name}' = {key_value_pairs} 저장 및 출력 완료"
                        else:
                            message = f"딕셔너리 '{name}' = {key_value_pairs} 저장 완료"
                        
                        return DATA_Result(result=True, message=message)
                    
                    else:
                        return DATA_Result(result=False, message=f"지원하지 않는 테스트 타입: {test_type}")
                        
                except Exception as e:
                    return DATA_Result(result=False, message=str(e))
            
            elif self.args['type'] == 'python':
                try:
                    import subprocess
                    import json as json_module
                    
                    python_type = self.args.get('python_type', 'file')
                    to_key = self.args.get('to', 'result')
                    
                    if python_type == 'file':
                        # 파일 실행 모드
                        if 'script_path' not in self.args: return DATA_Result(result=False, message="'script_path' 파라미터가 필요합니다")
                        
                        script_path = self.args['script_path']
                        arg_count = self.args.get('arg_count', 0)  # 인자 개수
                        
                        # 스크립트 파일 존재 확인
                        if not os.path.exists(script_path): return DATA_Result(result=False, message=f"스크립트 파일이 존재하지 않습니다: {script_path}")
                        
                        # 인자 준비
                        args = []
                        for i in range(arg_count):
                            from_key = self.args.get(f'from_{i}')
                            if not from_key: return DATA_Result(result=False, message=f"'from_{i}' 파라미터가 필요합니다")
                            if from_key not in self.data_share_dict: return DATA_Result(result=False, message=f"'{from_key}' 키가 data_share_dict에 존재하지 않습니다")
                            
                            # 데이터를 JSON 문자열로 변환
                            data_value = self.data_share_dict[from_key]
                            if isinstance(data_value, pd.DataFrame):
                                args.append(data_value.to_json(orient='records', force_ascii=False))
                            else:
                                args.append(json_module.dumps(data_value, ensure_ascii=False))
                        
                        # Python 스크립트 실행
                        result = subprocess.run([sys.executable, script_path] + args, 
                                              capture_output=True, text=True, encoding='utf-8')
                        
                        if result.returncode != 0:
                            return DATA_Result(result=False, message=f"스크립트 실행 오류: {result.stderr}")
                        
                        # 결과 처리
                        output = result.stdout.strip()
                        if output:
                            try:
                                # JSON 형태로 파싱 시도
                                parsed_output = json_module.loads(output)
                                self.data_share_dict[to_key] = parsed_output
                            except json_module.JSONDecodeError:
                                # 일반 텍스트로 저장
                                self.data_share_dict[to_key] = output
                        else:
                            self.data_share_dict[to_key] = None
                        
                        return DATA_Result(result=True, message=f"Python 파일 실행 완료, 결과를 '{to_key}'에 저장", data=self.data_share_dict[to_key])
                    
                    elif python_type == 'code':
                        # 코드 직접 실행 모드
                        if 'code' not in self.args: return DATA_Result(result=False, message="'code' 파라미터가 필요합니다")
                        
                        code = self.args['code']
                        
                        try:
                            import io
                            import sys
                            
                            # 출력을 캡처하기 위한 StringIO 객체
                            output_capture = io.StringIO()
                            original_stdout = sys.stdout
                            sys.stdout = output_capture
                            
                            try:
                                # data_share_dict 변수를 네임스페이스에 추가 (무한 참조 방지)
                                self.data_share_dict['data_share_dict'] = {k: v for k, v in self.data_share_dict.items() if k != 'data_share_dict'}
                                # 커널의 네임스페이스에서 직접 코드 실행
                                exec(code, globals(), self.data_share_dict)
                                
                                # 캡처된 출력 가져오기
                                captured_output = output_capture.getvalue()
                                
                            finally:
                                # stdout 복원
                                sys.stdout = original_stdout
                                output_capture.close()
                            
                            # 결과 메시지 구성
                            message_parts = []
                            
                            # 캡처된 출력이 있으면 메시지에 포함
                            if captured_output.strip():
                                message_parts.append(f"출력:\n{captured_output.strip()}")
                            
                            # 결과 저장 (to_key가 data_share_dict에 있으면 저장됨)
                            if to_key in self.data_share_dict:
                                message_parts.append(f"결과를 '{to_key}'에 저장")
                                return DATA_Result(result=True, message="\n".join(message_parts), data=self.data_share_dict[to_key])
                            else:
                                if message_parts:
                                    return DATA_Result(result=True, message="\n".join(message_parts))
                                else:
                                    return DATA_Result(result=True, message="Python 코드 실행 완료")
                                
                        except Exception as e:
                            return DATA_Result(result=False, message=f"코드 실행 오류: {str(e)}")
                    
                    else:
                        return DATA_Result(result=False, message=f"지원하지 않는 Python 실행 타입: {python_type}")
                        
                except Exception as e:
                    return DATA_Result(result=False, message=str(e))
            

        except AttributeError as e:
            # engine이 None일 때 발생하는 AttributeError 처리
            if "NoneType" in str(e) and "engine" in str(e):
                return DATA_Result(result=False, message="SYSTEM_SELENIUM이 data_share_dict에 없습니다. engine을 먼저 초기화해주세요.")
            else:
                error_msg = traceback.format_exc()
                print(error_msg)
                return DATA_Result(result=False, message=error_msg)
        except Exception as e: 
            error_msg = traceback.format_exc()
            print(error_msg)
            return DATA_Result(result=False, message=error_msg)

    def find_element(self):
        try:
            if 'focus' in self.args and self.args.get('focus'):
                if self.args['focus'].get('xpath'):
                    return self.args['focus']['xpath']
                    # return self.engine.find_element_xpath(self.args['focus']['xpath'])
                elif self.args['focus'].get('selector'):
                    return self.args['focus']['selector']
                    # return self.engine.find_element_xpath(self.args['focus']['selector'])
                elif self.args['focus'] == 'current':
                    driver = self.getdriver()
                    if driver:
                        return driver.switch_to.active_element
        except: return None
        return None

    def getdriver(self):
        """현재 driver_number에 해당하는 driver를 반환합니다."""
        if self.engine is None:
            return None
        return self.engine.getdriver(self.driver_number)
    
    def refresh(self):
        self.driver_number = self.args.get('driver_number', 0)
        return True

  