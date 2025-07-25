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
from CLASS import data_result
from CLASS import class_parser_html
from MODULE import module_engine_selenium as sele

class Job:
    def __init__(self, name, args, data_share_dict):
        self.name = name
        self.args = args
        self.data_share_dict = data_share_dict
        self.driver_number = self.args.get('driver_number', 0)
        self.jobs = []
        
        # SYSTEM_SELENIUM에서 engine 가져오기
        if 'SYSTEM_SELENIUM' in self.data_share_dict:
            self.engine = self.data_share_dict['SYSTEM_SELENIUM']['engine']
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
                elif not element : return data_result.DATA_Result(message="Element not found")
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
                    return data_result.DATA_Result(result=True, message=element.text)
                
            elif self.args['type'] == 'find':
                if not element: 
                    return data_result.DATA_Result(message="Element not found")
                
                # 기본 스크래핑 (기존 방식)
                if not self.args.get('find_type'):
                    xpath = element.to_xpath()
                    return self.engine.scrape(self.driver_number, xpath)
                
                if self.args.get('source'):
                    parsed_html = class_parser_html.parse(self.args.get('source'))
                else:
                    # SYSTEM_REQUEST, SYSTEM_SELENIUM 등에서 html 자동 추출
                    html_source = None
                    for key in ['SYSTEM_REQUEST', 'SYSTEM_SELENIUM']:
                        if key in self.data_share_dict and isinstance(self.data_share_dict[key], dict):
                            if 'html' in self.data_share_dict[key]:
                                html_source = self.data_share_dict[key]['html']
                                break
                    if html_source is not None:
                        parsed_html = class_parser_html.parse(html_source)
                    else:
                        parsed_html = class_parser_html.parse(self.getdriver().page_source)
                
                # find_type 기반 파싱
                if not self.args.get('find_type') or not self.args.get('find_item'):
                    return data_result.DATA_Result(result=False, message="find_type과 find_item이 필요합니다")
                
                # attribute 타입인 경우 find_attribute도 필요
                if self.args.get('find_type') == 'attribute' and not self.args.get('find_attribute'):
                    return data_result.DATA_Result(result=False, message="attribute 타입의 경우 find_attribute가 필요합니다")
                
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
                        return data_result.DATA_Result(result=False, message=f"지원하지 않는 함수: {func_name}")
                except Exception as e:
                    return data_result.DATA_Result(result=False, message=f"함수 호출 오류: {str(e)}")
                
                if result_data is None:
                    return data_result.DATA_Result(result=False, message=f"{self.args.get('find_type')} '{self.args.get('find_item')}'을 찾을 수 없습니다")
                
                return data_result.DATA_Result(result=True, data=result_data)
            
            elif self.args['type'] == 'request':
                request_type = self.args.get('request_type', 'get')
                
                if request_type == 'get':
                    url = self.args['url']
                    params = self.args.get('params')
                    params_dict = None
                    if params:
                        # 1. 이미 dict로 들어온 경우
                        if isinstance(params, dict):
                            params_dict = params
                        else:
                            # 2. JSON string 시도
                            import json
                            try:
                                params_dict = json.loads(params)
                                if not isinstance(params_dict, dict):
                                    params_dict = None
                            except Exception:
                                # 3. key1=value1&key2=value2 형식 시도
                                try:
                                    params_dict = dict(x.split('=', 1) for x in params.split('&') if '=' in x)
                                except Exception:
                                    params_dict = None
                    # 4. 이미 urlencoded string이면 params_dict 대신 params를 직접 사용
                    import requests
                    if params_dict is not None:
                        response = requests.get(url, params=params_dict)
                    elif params:
                        # params가 urlencoded string일 경우
                        response = requests.get(url + ('?' if '?' not in url else '&') + params)
                    else:
                        response = requests.get(url)
                    
                    if response.status_code == 200:
                        # HTML과 CSS 추출 및 저장
                        html_content = response.text
                        
                        # CSS 추출 (리스트로 저장)
                        css_list = self.extract_css_from_html(html_content, url)
                        
                        # SYSTEM_REQUEST에 전체 데이터 저장
                        result_data = {
                            'html': html_content,
                            'css_list': css_list,
                            'url': url,
                            'status_code': response.status_code,
                            'headers': dict(response.headers)
                        }
                        
                        self.data_share_dict['SYSTEM_REQUEST'] = result_data
                        
                        print(f"SYSTEM_REQUEST에 데이터가 저장되었습니다:")
                        print(f"  - HTML 길이: {len(html_content)}")
                        print(f"  - CSS 파일 개수: {len(css_list)}")
                        print(f"  - URL: {url}")
                        
                        return data_result.DATA_Result(result=True, data=response, message=f"HTML과 CSS가 SYSTEM_REQUEST에 저장되었습니다")
                    else:
                        return data_result.DATA_Result(result=False, message="request 실패")
                
                elif request_type == 'post':
                    response = requests.post(self.args['url'], data=self.args['data'])
                    if response.status_code == 200:
                        # HTML과 CSS 추출 및 저장 (get과 동일 포맷)
                        html_content = response.text
                        url = self.args['url']
                        css_list = self.extract_css_from_html(html_content, url)
                        result_data = {
                            'html': html_content,
                            'css_list': css_list,
                            'url': url,
                            'status_code': response.status_code,
                            'headers': dict(response.headers)
                        }
                        self.data_share_dict['SYSTEM_REQUEST'] = result_data
                        print(f"SYSTEM_REQUEST에 데이터가 저장되었습니다:")
                        print(f"  - HTML 길이: {len(html_content)}")
                        print(f"  - CSS 파일 개수: {len(css_list)}")
                        print(f"  - URL: {url}")
                        return data_result.DATA_Result(result=True, data=response)
                    else:
                        return data_result.DATA_Result(result=False, message=response.text)
                
                elif request_type == 'selenium':
                    # Selenium 요청 - engine start 포함
                    url = self.args.get('url', '')
                    wait_time = self.args.get('wait_time', 2)
                    
                    if not url:
                        return data_result.DATA_Result(result=False, message="URL이 필요합니다")
                    
                    try:
                        # 기존 SYSTEM_SELENIUM이 있으면 quit하고 새로 생성
                        if 'SYSTEM_SELENIUM' in self.data_share_dict and self.data_share_dict['SYSTEM_SELENIUM'] is not None:
                            try:
                                self.data_share_dict['SYSTEM_SELENIUM']['engine'].quit()
                            except:
                                pass
                        
                        if not 'SYSTEM_SELENIUM' in self.data_share_dict:
                            self.data_share_dict['SYSTEM_SELENIUM']={}

                        self.data_share_dict['SYSTEM_SELENIUM']['engine'] = sele.engine()
                        self.engine=self.data_share_dict['SYSTEM_SELENIUM']['engine']
                        self.driver_number = 0
                        new_driver = self.engine.start(url, dis=True,profile='/home/PROJECT/SCOOPIE/PROFILE',profile_name='testing',timeout=-1)
                        if new_driver is None:
                            return data_result.DATA_Result(result=False, message="드라이버 시작에 실패했습니다.")
                        
                        # 대기 시간
                        if wait_time > 0:
                            import time
                            time.sleep(wait_time)
                        
                        # 새로운 함수 사용하여 데이터 추출
                        result_data = self.extract_current_page_data()
                        if result_data:
                            # 기존 engine 정보 보존하면서 데이터 업데이트
                            self.data_share_dict['SYSTEM_SELENIUM']['html'] = result_data['html']
                            self.data_share_dict['SYSTEM_SELENIUM']['css'] = result_data['css']
                            self.data_share_dict['SYSTEM_SELENIUM']['url'] = result_data['url']
                            # driver도 저장
                            self.data_share_dict['SYSTEM_SELENIUM']['driver'] = new_driver
                            import json
                            css_list = json.loads(result_data['css'])
                            print(f"SYSTEM_SELENIUM에 데이터가 저장되었습니다:")
                            print(f"  - HTML 길이: {len(result_data['html'])}")
                            print(f"  - CSS 파일 개수: {len(css_list)} (selenium)")
                            print(f"  - URL: {result_data['url']}")
                            print(f"  - Driver: 저장됨")
                        else:
                            print("데이터 추출 실패")
                        
                        return data_result.DATA_Result(result=True, data=self.engine, message=f"Selenium으로 {url} 접속 완료")
                        
                    except Exception as e:
                        return data_result.DATA_Result(result=False, message=f"Selenium 요청 실패: {str(e)}")
                
                elif request_type == 'selenium_url_change':
                    # Selenium URL 변경 - 기존 driver 사용
                    url = self.args.get('url', '')
                    wait_time = self.args.get('wait_time', 2)
                    
                    if not url:
                        return data_result.DATA_Result(result=False, message="URL이 필요합니다")
                    
                    try:
                        # 기존 SYSTEM_SELENIUM이 있는지 확인
                        if 'SYSTEM_SELENIUM' not in self.data_share_dict or self.data_share_dict['SYSTEM_SELENIUM'] is None:
                            return data_result.DATA_Result(result=False, message="기존 Selenium 드라이버가 없습니다. 먼저 'selenium' 요청으로 드라이버를 시작해주세요.")
                        
                        
                        # 현재 driver_number 확인 (기본값 0)
                        if not hasattr(self, 'driver_number'):
                            self.driver_number = 0
                        
                        # 기존 driver로 URL 변경
                        driver = self.data_share_dict['SYSTEM_SELENIUM']['driver']
                        if driver is None:
                            return data_result.DATA_Result(result=False, message="드라이버를 찾을 수 없습니다.")
                        
                        # URL로 이동
                        driver.get(url)

                        
                        # 대기 시간
                        if wait_time > 0:
                            import time
                            time.sleep(wait_time)
                        
                        return data_result.DATA_Result(result=True, data=None, message=f"Selenium으로 {url} 이동 완료")
                        
                    except Exception as e:
                        return data_result.DATA_Result(result=False, message=f"Selenium URL 변경 실패: {str(e)}")
                
                else:
                    return data_result.DATA_Result(result=False, message=f"지원하지 않는 요청 타입: {request_type}")
                
            elif self.args['type'] == 'data':
                try:
                    if 'from' not in self.args: return data_result.DATA_Result(result=False, message="'from' 파라미터가 필요합니다")
                    from_value = self.args['from']
                    if from_value not in self.data_share_dict: return data_result.DATA_Result(result=False, message=f"'{from_value}' 키가 data_share_dict에 존재하지 않습니다")
                    
                    data_value = self.data_share_dict[from_value]
                    convert_type = self.args.get('convert_type', '')
                    
                    # 변환 타입이 있으면 각 함수별로 처리
                    if convert_type:
                        # key_to_list 변환 처리
                        if convert_type == 'key_to_list':
                            key_count = self.args.get('key_count', 0)
                            if key_count <= 0:
                                return data_result.DATA_Result(result=False, message="key_count가 0보다 커야 합니다")
                            
                            result_list = []
                            for i in range(key_count):
                                key_name = self.args.get(f'key_{i}')
                                if not key_name:
                                    return data_result.DATA_Result(result=False, message=f"key_{i} 파라미터가 필요합니다")
                                if key_name not in self.data_share_dict:
                                    return data_result.DATA_Result(result=False, message=f"'{key_name}' 키가 data_share_dict에 존재하지 않습니다")
                                result_list.append(self.data_share_dict[key_name])
                            
                            if 'to' in self.args:
                                to_key = self.args['to']
                                self.data_share_dict[to_key] = result_list
                                return data_result.DATA_Result(result=True, message=f"{key_count}개의 키 값을 리스트로 변환하여 '{to_key}'에 저장 완료", data=result_list)
                            else:
                                return data_result.DATA_Result(result=True, message=f"{key_count}개의 키 값을 리스트로 변환 완료", data=result_list)
                        
                        # Tag 객체나 Tag 배열인지 확인
                        is_tag_object = hasattr(data_value, 'to_html')  # Tag 객체 확인
                        is_tag_array = isinstance(data_value, list) and len(data_value) > 0 and hasattr(data_value[0], 'to_html')  # Tag 배열 확인
                        
                        if not (is_tag_object or is_tag_array):
                            return data_result.DATA_Result(result=False, message=f"'{from_value}' 데이터가 Tag 객체 또는 Tag 배열이 아닙니다")
                        
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
                                    return data_result.DATA_Result(result=True, message=f"'{from_value}'을 {convert_type}로 변환하여 '{to_key}'에 저장 완료", data=converted_data)
                                else:
                                    return data_result.DATA_Result(result=True, message=f"'{from_value}'을 {convert_type}로 변환 완료", data=converted_data)
                            else:
                                return data_result.DATA_Result(result=False, message=f"'{convert_type}' 변환 메서드가 존재하지 않습니다")
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
                                    return data_result.DATA_Result(result=True, message=f"'{from_value}' 배열을 {convert_type}로 변환하여 '{to_key}'에 저장 완료", data=converted_data)
                                else:
                                    return data_result.DATA_Result(result=True, message=f"'{from_value}' 배열을 {convert_type}로 변환 완료", data=converted_data)
                            else:
                                return data_result.DATA_Result(result=False, message=f"'{convert_type}' 변환 메서드가 존재하지 않습니다")
                    
                    # 변환 타입이 없으면 그대로 복사
                    if 'to' in self.args:
                        to_key = self.args['to']
                        self.data_share_dict[to_key] = data_value
                        return data_result.DATA_Result(result=True, message=f"'{from_value}'에서 '{to_key}'로 데이터 복사 완료", data=data_value)
                    else:
                        return data_result.DATA_Result(result=True, message=f"'{from_value}' 데이터 조회 완료", data=data_value)
                        
                except Exception as e:
                    return data_result.DATA_Result(result=False, message=str(e))
            
            elif self.args['type'] == 'save':
                try:
                    save_type = self.args.get('save_type', 'excel')
                    to_key = self.args.get('to', '')
                    name = self.args.get('name', '')
                    encoding = self.args.get('encoding', 'utf-8')
                    
                    if not to_key or to_key not in self.data_share_dict: return data_result.DATA_Result(result=False, message=f"'{to_key}' 키가 data_share_dict에 존재하지 않습니다")
                    data = self.data_share_dict[to_key]
                    if not isinstance(data, pd.DataFrame): return data_result.DATA_Result(result=False, message=f"'{to_key}' 데이터가 DataFrame이 아닙니다")
                    
                    if save_type == 'excel':
                        data.to_excel(name, index=False)
                        # 파일 생성 후 그룹 쓰기 권한 설정
                        try:
                            os.chmod(name, 0o664)  # rw-rw-r--
                        except Exception:
                            pass  # 권한 설정 실패시 무시
                        return data_result.DATA_Result(result=True, message=f"Excel 파일 '{name}' 저장 완료")
                    elif save_type in ['csv', 'txt']:
                        data.to_csv(name, index=False, encoding=encoding)
                        # 파일 생성 후 그룹 쓰기 권한 설정
                        try:
                            os.chmod(name, 0o664)  # rw-rw-r--
                        except Exception:
                            pass  # 권한 설정 실패시 무시
                        return data_result.DATA_Result(result=True, message=f"{save_type.upper()} 파일 '{name}' 저장 완료")
                    elif save_type == 'mysql':
                        try: con, engine = DB.connect('file_hk')
                        except Exception as E: print(E); print('DB 접속 실패'); return data_result.DATA_Result(result=False, message="DB 접속 실패")
                        data.to_sql(name, con, if_exists='append', index=False)
                        return data_result.DATA_Result(result=True, message=f"MySQL 테이블 '{name}' 저장 완료")
                    elif save_type == 'elasticsearch':
                        es_conn = ES.connector()
                        es_conn.dataframe_to_es(data, name)
                        return data_result.DATA_Result(result=True, message=f"Elasticsearch 인덱스 '{name}' 저장 완료")
                    else:
                        return data_result.DATA_Result(result=False, message=f"지원하지 않는 저장 타입: {save_type}")
                        
                except Exception as e:
                    return data_result.DATA_Result(result=False, message=str(e))
            
            elif self.args['type'] == 'load':
                try:
                    load_type = self.args.get('load_type', 'excel')
                    from_key = self.args.get('from', '')
                    name = self.args.get('name', '')
                    encoding = self.args.get('encoding', 'utf-8')
                    
                    if load_type == 'excel':
                        df = pd.read_excel(name)
                        self.data_share_dict[from_key] = df
                        return data_result.DATA_Result(result=True, message=f"Excel 파일 '{name}' 로드 완료")
                    elif load_type in ['csv', 'txt']:
                        df = pd.read_csv(name, encoding=encoding)
                        self.data_share_dict[from_key] = df
                        return data_result.DATA_Result(result=True, message=f"{load_type.upper()} 파일 '{name}' 로드 완료")
                    elif load_type == 'mysql':
                        try: con, engine = DB.connect('file_hk')
                        except Exception as E: print(E); print('DB 접속 실패'); return data_result.DATA_Result(result=False, message="DB 접속 실패")
                        df = pd.read_sql(f"SELECT * FROM {name}", con)
                        self.data_share_dict[from_key] = df
                        return data_result.DATA_Result(result=True, message=f"MySQL 테이블 '{name}' 로드 완료")
                    elif load_type == 'elasticsearch':
                        es_conn = ES.connector()
                        df = es_conn.search_data(name, None)
                        self.data_share_dict[from_key] = df
                        return data_result.DATA_Result(result=True, message=f"Elasticsearch 인덱스 '{name}' 로드 완료")
                    else:
                        return data_result.DATA_Result(result=False, message=f"지원하지 않는 로드 타입: {load_type}")
                        
                except Exception as e:
                    return data_result.DATA_Result(result=False, message=str(e))
            
            elif self.args['type'] == 'wait':
                try:
                    wait_type = self.args.get('wait_type', 'fixed_time')
                    
                    if wait_type == 'fixed_time':
                        time_value = self.args.get('time', 1.0)
                        if not isinstance(time_value, (int, float)) or time_value <= 0:
                            return data_result.DATA_Result(result=False, message="time 값은 0보다 큰 숫자여야 합니다")
                        
                        # module_engine_selenium의 engine.wait 사용
                        self.engine.wait(self.driver_number, time_value)
                        return data_result.DATA_Result(result=True, message=f"{time_value}초 대기 완료")
                    
                    elif wait_type == 'load_time':
                        # TODO: 로딩 완료 대기 구현
                        return data_result.DATA_Result(result=False, message="load_time 기능은 아직 구현되지 않았습니다")
                    
                    else:
                        return data_result.DATA_Result(result=False, message=f"지원하지 않는 대기 타입: {wait_type}")
                        
                except Exception as e:
                    return data_result.DATA_Result(result=False, message=str(e))
            

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
                        
                        return data_result.DATA_Result(result=True, message=message)
                    
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
                        
                        return data_result.DATA_Result(result=True, message=message)
                    
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
                        
                        return data_result.DATA_Result(result=True, message=message)
                    
                    else:
                        return data_result.DATA_Result(result=False, message=f"지원하지 않는 테스트 타입: {test_type}")
                        
                except Exception as e:
                    return data_result.DATA_Result(result=False, message=str(e))
            
            elif self.args['type'] == 'python':
                try:
                    import subprocess
                    import json as json_module
                    
                    python_type = self.args.get('python_type', 'file')
                    to_key = self.args.get('to', 'result')
                    
                    if python_type == 'file':
                        # 파일 실행 모드
                        if 'script_path' not in self.args: return data_result.DATA_Result(result=False, message="'script_path' 파라미터가 필요합니다")
                        
                        script_path = self.args['script_path']
                        arg_count = self.args.get('arg_count', 0)  # 인자 개수
                        
                        # 스크립트 파일 존재 확인
                        if not os.path.exists(script_path): return data_result.DATA_Result(result=False, message=f"스크립트 파일이 존재하지 않습니다: {script_path}")
                        
                        # 인자 준비
                        args = []
                        for i in range(arg_count):
                            from_key = self.args.get(f'from_{i}')
                            if not from_key: return data_result.DATA_Result(result=False, message=f"'from_{i}' 파라미터가 필요합니다")
                            if from_key not in self.data_share_dict: return data_result.DATA_Result(result=False, message=f"'{from_key}' 키가 data_share_dict에 존재하지 않습니다")
                            
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
                            return data_result.DATA_Result(result=False, message=f"스크립트 실행 오류: {result.stderr}")
                        
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
                        
                        return data_result.DATA_Result(result=True, message=f"Python 파일 실행 완료, 결과를 '{to_key}'에 저장", data=self.data_share_dict[to_key])
                    
                    elif python_type == 'code':
                        # 코드 직접 실행 모드
                        if 'code' not in self.args: return data_result.DATA_Result(result=False, message="'code' 파라미터가 필요합니다")
                        
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
                                return data_result.DATA_Result(result=True, message="\n".join(message_parts), data=self.data_share_dict[to_key])
                            else:
                                if message_parts:
                                    return data_result.DATA_Result(result=True, message="\n".join(message_parts))
                                else:
                                    return data_result.DATA_Result(result=True, message="Python 코드 실행 완료")
                                
                        except Exception as e:
                            return data_result.DATA_Result(result=False, message=f"코드 실행 오류: {str(e)}")
                    
                    else:
                        return data_result.DATA_Result(result=False, message=f"지원하지 않는 Python 실행 타입: {python_type}")
                        
                except Exception as e:
                    return data_result.DATA_Result(result=False, message=str(e))
            

        except AttributeError as e:
            # engine이 None일 때 발생하는 AttributeError 처리
            if "NoneType" in str(e) and "engine" in str(e):
                return data_result.DATA_Result(result=False, message="SYSTEM_SELENIUM이 data_share_dict에 없습니다. engine을 먼저 초기화해주세요.")
            else:
                error_msg = traceback.format_exc()
                print(error_msg)
                return data_result.DATA_Result(result=False, message=error_msg)
        except Exception as e: 
            error_msg = traceback.format_exc()
            print(error_msg)
            return data_result.DATA_Result(result=False, message=error_msg)

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
    
    def extract_css_from_html(self, html_content, base_url):
        """HTML에서 CSS를 추출하고 외부 CSS 파일도 다운로드"""
        import re
        import requests
        from urllib.parse import urljoin, urlparse
        
        css_list = []
        
        try:
            # 1. <style> 태그 내부의 CSS 추출
            style_pattern = r'<style[^>]*>(.*?)</style>'
            style_matches = re.findall(style_pattern, html_content, re.DOTALL | re.IGNORECASE)
            for i, style in enumerate(style_matches):
                css_item = {
                    'type': 'internal_style',
                    'index': i,
                    'content': style.strip(),
                    'url': None
                }
                css_list.append(css_item)
            
            # 2. <link> 태그의 외부 CSS 파일 다운로드
            link_pattern = r'<link[^>]*href=["\']([^"\']*\.css[^"\']*)["\'][^>]*>'
            link_matches = re.findall(link_pattern, html_content, re.IGNORECASE)
            
            for css_url in link_matches:
                try:
                    # 상대 URL을 절대 URL로 변환
                    if not css_url.startswith(('http://', 'https://')):
                        css_url = urljoin(base_url, css_url)
                    
                    # CSS 파일 다운로드
                    css_response = requests.get(css_url, timeout=10)
                    if css_response.status_code == 200:
                        css_item = {
                            'type': 'external_css',
                            'url': css_url,
                            'content': css_response.text,
                            'status_code': css_response.status_code
                        }
                        css_list.append(css_item)

                    else:
                        css_item = {
                            'type': 'external_css_failed',
                            'url': css_url,
                            'content': None,
                            'status_code': css_response.status_code,
                            'error': f"HTTP {css_response.status_code}"
                        }
                        css_list.append(css_item)

                except Exception as e:
                    css_item = {
                        'type': 'external_css_error',
                        'url': css_url,
                        'content': None,
                        'error': str(e)
                    }
                    css_list.append(css_item)
                    
            
            # 3. style 속성의 인라인 CSS 추출
            style_attr_pattern = r'style=["\']([^"\']*)["\']'
            style_attr_matches = re.findall(style_attr_pattern, html_content)
            for i, style_attr in enumerate(style_attr_matches):
                css_item = {
                    'type': 'inline_style',
                    'index': i,
                    'content': style_attr,
                    'url': None
                }
                css_list.append(css_item)
            
        except Exception as e:
            pass
        
        return css_list
    
    def _embed_images_to_html_source(self, html_source):
        """확장된 이미지 처리: img 태그, data-bg 속성, CSS background-image를 모두 처리"""
        try:
            driver = self.getdriver()
            import requests
            import base64
            from urllib.parse import urljoin
            
            # 확장된 이미지 URL 수집 스크립트
            img_urls = driver.execute_script("""
                var urls = [];
                
                // 1. img 태그의 src 속성
                var imgs = document.querySelectorAll('img[src]');
                for (var i = 0; i < imgs.length; i++) {
                    var src = imgs[i].src;
                    if (src && !src.startsWith('data:')) {
                        urls.push({url: src, type: 'img_src'});
                    }
                }
                
                // 2. data-bg 속성 (모든 태그에서)
                var dataBgElements = document.querySelectorAll('[data-bg]');
                for (var i = 0; i < dataBgElements.length; i++) {
                    var dataBg = dataBgElements[i].getAttribute('data-bg');
                    if (dataBg && !dataBg.startsWith('data:')) {
                        urls.push({url: dataBg, type: 'data_bg'});
                    }
                }
                
                // 3. data-background 속성
                var dataBackgroundElements = document.querySelectorAll('[data-background]');
                for (var i = 0; i < dataBackgroundElements.length; i++) {
                    var dataBg = dataBackgroundElements[i].getAttribute('data-background');
                    if (dataBg && !dataBg.startsWith('data:')) {
                        urls.push({url: dataBg, type: 'data_background'});
                    }
                }
                
                // 4. CSS background-image (인라인 스타일)
                var elementsWithStyle = document.querySelectorAll('[style*="background-image"]');
                for (var i = 0; i < elementsWithStyle.length; i++) {
                    var style = elementsWithStyle[i].style.backgroundImage;
                    if (style) {
                        var match = style.match(/url\\(['"]?([^'"\\)]+)['"]?\\)/);
                        if (match && match[1] && !match[1].startsWith('data:')) {
                            urls.push({url: match[1], type: 'background_image'});
                        }
                    }
                }
                
                return urls;
            """)
            
            if not img_urls:
                return 0
                
            current_url = driver.current_url
            processed_html = html_source
            success_count = 0
            
            for img_data in img_urls[:10]:  # 최대 10개까지 처리
                try:
                    img_url = img_data['url']
                    img_type = img_data['type']
                    
                    absolute_url = urljoin(current_url, img_url)
                    response = requests.get(absolute_url, timeout=5)
                    
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', 'image/jpeg')
                        img_base64 = base64.b64encode(response.content).decode('utf-8')
                        data_uri = f"data:{content_type};base64,{img_base64}"
                        
                        # 타입별로 다른 방식으로 교체
                        if img_type == 'img_src':
                            processed_html = processed_html.replace(f'src="{img_url}"', f'src="{data_uri}"')
                            processed_html = processed_html.replace(f"src='{img_url}'", f"src='{data_uri}'")
                        elif img_type == 'data_bg':
                            processed_html = processed_html.replace(f'data-bg="{img_url}"', f'data-bg="{data_uri}"')
                            processed_html = processed_html.replace(f"data-bg='{img_url}'", f"data-bg='{data_uri}'")
                        elif img_type == 'data_background':
                            processed_html = processed_html.replace(f'data-background="{img_url}"', f'data-background="{data_uri}"')
                            processed_html = processed_html.replace(f"data-background='{img_url}'", f"data-background='{data_uri}'")
                        elif img_type == 'background_image':
                            processed_html = processed_html.replace(f'url({img_url})', f'url({data_uri})')
                            processed_html = processed_html.replace(f"url('{img_url}')", f"url('{data_uri}')")
                            processed_html = processed_html.replace(f'url("{img_url}")', f'url("{data_uri}")')
                        
                        success_count += 1
                        print(f"이미지 변환 완료: {img_type} - {img_url[:50]}...")
                        
                except Exception as e:
                    print(f"이미지 처리 실패: {img_url[:50]}... - {str(e)}")
                    continue
            
            self._last_processed_html = processed_html
            return success_count
            
        except Exception as e:
            print(f"확장 이미지 처리 실패: {str(e)}")
            return 0
    
    def _extract_css_from_browser(self, base_url):
        """웹드라이버에서 실제 로드된 CSS를 추출"""
        css_list = []
        
        try:
            driver = self.getdriver()
            
            # JavaScript로 브라우저에 로드된 모든 스타일시트 정보 가져오기
            js_script = """
            var cssData = [];
            var styleSheets = document.styleSheets;
            
            for (var i = 0; i < styleSheets.length; i++) {
                var sheet = styleSheets[i];
                var cssText = '';
                var sheetUrl = sheet.href || 'inline';
                
                try {
                    // 스타일시트의 모든 규칙 수집
                    var rules = sheet.cssRules || sheet.rules;
                    if (rules) {
                        for (var j = 0; j < rules.length; j++) {
                            if (rules[j].cssText) {
                                cssText += rules[j].cssText + '\\n';
                            }
                        }
                    }
                } catch (e) {
                    // CORS 제한으로 접근 불가한 외부 CSS
                    cssText = '/* CORS 제한으로 접근 불가: ' + e.message + ' */';
                }
                
                cssData.push({
                    url: sheetUrl,
                    content: cssText,
                    ruleCount: rules ? rules.length : 0
                });
            }
            
            // 인라인 스타일 태그들도 수집
            var styleTags = document.querySelectorAll('style');
            for (var k = 0; k < styleTags.length; k++) {
                cssData.push({
                    url: 'inline-style-' + k,
                    content: styleTags[k].textContent || styleTags[k].innerText,
                    ruleCount: -1
                });
            }
            
            return cssData;
            """
            
            # JavaScript 실행하여 CSS 데이터 가져오기
            css_data = driver.execute_script(js_script)
            
            # 결과를 표준 포맷으로 변환
            for item in css_data:
                css_url = item.get('url', 'unknown')
                css_content = item.get('content', '')
                rule_count = item.get('ruleCount', 0)
                
                if css_url == 'inline' or css_url.startswith('inline-style-'):
                    css_type = 'inline_css'
                elif css_url.startswith('http'):
                    css_type = 'external_css'
                else:
                    css_type = 'browser_css'
                
                css_item = {
                    'type': css_type,
                    'url': css_url,
                    'content': css_content,
                    'status_code': 200,
                    'rule_count': rule_count
                }
                css_list.append(css_item)
            
            print(f"브라우저에서 CSS 추출 완료: {len(css_list)}개")
            
        except Exception as e:
            print(f"브라우저 CSS 추출 실패: {str(e)}")
            # 실패 시 기존 방식으로 폴백
            try:
                page_source = self.getdriver().page_source
                css_list = self.extract_css_from_html(page_source, base_url)
                print(f"HTML 파싱으로 CSS 추출: {len(css_list)}개")
            except Exception as e2:
                print(f"HTML 파싱도 실패: {str(e2)}")
                css_list = []
        
        return css_list

    def extract_current_page_data(self):
        """현재 driver 상태에서 HTML, CSS, 이미지 데이터를 추출"""
        try:
            driver = self.getdriver()
            if not driver:
                return None
                
            # 현재 페이지의 HTML 소스 가져오기
            page_source = driver.page_source
            current_url = driver.current_url
            
            # CSS 추출
            print("셀레니움에서 CSS 추출 중...")
            css_js_code = """
            var css_list = [];
            var styleSheets = document.styleSheets;
            
            for (var i = 0; i < styleSheets.length; i++) {
                try {
                    var sheet = styleSheets[i];
                    var rules = sheet.cssRules || sheet.rules;
                    var cssText = '';
                    
                    if (rules) {
                        for (var j = 0; j < rules.length; j++) {
                            cssText += rules[j].cssText + '\\n';
                        }
                    }
                    
                    if (cssText.trim()) {
                        css_list.push({
                            'content': cssText,
                            'url': sheet.href || 'inline'
                        });
                    }
                } catch (e) {
                    // CORS 제한으로 접근 불가한 스타일시트는 건너뜀
                }
            }
            
            return css_list;
            """
            
            css_list = driver.execute_script(css_js_code)
            if not css_list:
                css_list = []
            
            print(f"셀레니움에서 CSS 추출: {len(css_list)}개")
            
            # 웹폰트 처리 추가
            css_list = self._process_webfonts_in_css(css_list, current_url)
            
            # 이미지를 base64로 변환하여 HTML에 포함
            try:
                images_count = self._embed_images_to_html_source(page_source)
                if images_count > 0:
                    page_source = self._last_processed_html
                    print(f"이미지 {images_count}개를 base64로 변환하여 HTML에 포함했습니다.")
            except Exception as e:
                print(f"이미지 처리 중 오류: {str(e)}")
                print("이미지 없이 계속 진행합니다.")
            
            # CSS 데이터를 JSON 문자열로 직렬화
            import json
            css_json_string = json.dumps(css_list, ensure_ascii=False)
            
            # 결과 데이터 구성
            result_data = {
                'html': page_source,
                'css': css_json_string,
                'url': current_url
            }
            
            return result_data
            
        except Exception as e:
            print(f"데이터 추출 실패: {str(e)}")
            return None

    def refresh_selenium_data(self):
        """SYSTEM_SELENIUM 데이터를 현재 driver 상태로 새로고침"""
        try:
            new_data = self.extract_current_page_data()
            if new_data:
                # 기존 engine과 driver 정보 보존하면서 데이터만 업데이트
                self.data_share_dict['SYSTEM_SELENIUM']['html'] = new_data['html']
                self.data_share_dict['SYSTEM_SELENIUM']['css'] = new_data['css']
                self.data_share_dict['SYSTEM_SELENIUM']['url'] = new_data['url']
                print(f"SYSTEM_SELENIUM 데이터가 새로고침되었습니다:")
                print(f"  - HTML 길이: {len(new_data['html'])}")
                print(f"  - CSS 파일 개수: {len(json.loads(new_data['css']))}")
                print(f"  - URL: {new_data['url']}")
                return True
            else:
                print("데이터 새로고침 실패")
                return False
        except Exception as e:
            print(f"새로고침 실패: {str(e)}")
            return False

    def _process_webfonts_in_css(self, css_list, base_url):
        """CSS에서 웹폰트 파일을 찾아서 base64로 변환 (간단한 버전)"""
        print("웹폰트 처리 시작...")
        processed_css_list = []
        webfont_count = 0
        
        for css_item in css_list:
            css_content = css_item.get('content', '')
            css_url = css_item.get('url', 'inline')
            
            if not css_content:
                processed_css_list.append(css_item)
                continue
            
            # 간단한 웹폰트 탐지 (확장자 기반)
            webfont_extensions = ['.woff2', '.woff', '.ttf', '.eot', '.otf']
            processed_content = css_content
            
            # CSS 내용에서 웹폰트 확장자를 가진 URL 찾기
            import re
            import requests
            import base64
            from urllib.parse import urljoin
            
            # 간단한 패턴으로 url() 구문 찾기
            url_pattern = r'url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)'
            url_matches = re.findall(url_pattern, css_content, re.IGNORECASE)
            
            for url_match in url_matches:
                # 웹폰트 확장자인지 확인
                is_webfont = any(url_match.lower().endswith(ext) for ext in webfont_extensions)
                
                if is_webfont:
                    try:
                        # 상대 URL을 절대 URL로 변환
                        if css_url != 'inline' and not url_match.startswith(('http://', 'https://')):
                            if css_url.startswith('http'):
                                absolute_font_url = urljoin(css_url, url_match)
                            else:
                                absolute_font_url = urljoin(base_url, url_match)
                        elif url_match.startswith(('http://', 'https://')):
                            absolute_font_url = url_match
                        else:
                            absolute_font_url = urljoin(base_url, url_match)
                        
                        print(f"웹폰트 다운로드 중: {absolute_font_url}")
                        response = requests.get(absolute_font_url, timeout=10)
                        
                        if response.status_code == 200:
                            # MIME 타입 결정
                            content_type = response.headers.get('content-type', '')
                            if not content_type:
                                if url_match.endswith('.woff2'):
                                    content_type = 'font/woff2'
                                elif url_match.endswith('.woff'):
                                    content_type = 'font/woff'
                                elif url_match.endswith('.ttf'):
                                    content_type = 'font/ttf'
                                elif url_match.endswith('.eot'):
                                    content_type = 'application/vnd.ms-fontobject'
                                elif url_match.endswith('.otf'):
                                    content_type = 'font/otf'
                                else:
                                    content_type = 'font/woff2'
                            
                            # base64 변환
                            font_base64 = base64.b64encode(response.content).decode('utf-8')
                            data_uri = f"data:{content_type};base64,{font_base64}"
                            
                            # CSS에서 원래 URL을 data URI로 교체
                            patterns_to_replace = [
                                f'url("{url_match}")',
                                f"url('{url_match}')",
                                f'url({url_match})'
                            ]
                            
                            for pattern in patterns_to_replace:
                                if pattern in processed_content:
                                    processed_content = processed_content.replace(pattern, f'url("{data_uri}")')
                            
                            webfont_count += 1
                            print(f"웹폰트 변환 완료: {url_match} -> data URI ({len(font_base64)//1024}KB)")
                            
                        else:
                            print(f"웹폰트 다운로드 실패: {absolute_font_url} (HTTP {response.status_code})")
                            
                    except Exception as e:
                        print(f"웹폰트 처리 실패: {url_match} - {str(e)}")
                        continue
            
            # 처리된 CSS 아이템 추가
            processed_item = css_item.copy()
            processed_item['content'] = processed_content
            processed_css_list.append(processed_item)
        
        if webfont_count > 0:
            print(f"웹폰트 처리 완료: {webfont_count}개 변환됨")
        else:
            print("웹폰트가 발견되지 않았습니다.")
        
        return processed_css_list

  