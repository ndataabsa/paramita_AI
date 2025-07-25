import pandas as pd
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta
import uuid

class connector:
    def __init__(self, es_config=None):
        """
        Elasticsearch 연결을 초기화합니다.
        :param es_config: Elasticsearch 연결 정보 (optional)
        """
        if es_config is None:
            es_config = {
                'type': 'elasticsearch',
                'ip': '35.208.122.72',
                'port': '9200',
                'id': 'elastic',
                'pass': 'LJi8F0+mG8Q2+DyPN+-w',
                'verify_certs': False,
                'scheme': 'https',  # 여기에 scheme을 추가
            }

        self.es = Elasticsearch(
            [f"{es_config['scheme']}://{es_config['ip']}:{es_config['port']}"],
            http_auth=(es_config['id'], es_config['pass']),
            verify_certs=es_config['verify_certs']
        )
        self.index = es_config.get('index', 'default_index')

    def generate_unique_id(self):
        """
        고유한 ID를 생성합니다. 기본적으로 UUID를 사용합니다.
        """
        return str(uuid.uuid4())

    def dataframe_to_es(self, df, index_name):
        """
        DataFrame을 Elasticsearch에 저장합니다.
        :param df: Elasticsearch에 저장할 DataFrame
        :param index_name: 사용할 인덱스 이름
        """
        # 인덱스가 존재하는지 확인하고, 없다면 생성
        if not self.es.indices.exists(index=index_name):
            self.es.indices.create(index=index_name)
            print(f"Index '{index_name}' created!")

        # DataFrame의 각 행에 대해 Elasticsearch 문서 ID를 자동 생성하여 추가
        for _, row in df.iterrows():
            doc = row.to_dict()

            # 자동 생성된 _id를 사용하려면 id를 전달하지 않습니다
            self.es.index(index=index_name, document=doc)  # id를 전달하지 않음

        print(f"Data inserted into {index_name} successfully!")

        
    def delete_index(self, index_name):
        """
        Elasticsearch에서 특정 인덱스를 삭제합니다.
        :param index_name: 삭제할 인덱스 이름
        """
        if self.es.indices.exists(index=index_name):
            self.es.indices.delete(index=index_name)
            print(f"Index '{index_name}' deleted successfully!")
        else:
            print(f"Index '{index_name}' does not exist.")
            
    def delete_document(self, index_name, query):
        """
        Elasticsearch에서 특정 조건을 만족하는 문서를 삭제합니다.
        :param index_name: 삭제할 문서를 포함한 인덱스 이름
        :param query: 삭제할 문서를 찾기 위한 쿼리
        """
        # Delete by query API를 사용하여 쿼리에 맞는 문서들을 삭제합니다.
        response = self.es.delete_by_query(index=index_name, body=query)

        if response['deleted'] > 0:
            print(f"Deleted {response['deleted']} documents from '{index_name}' based on the query.")
        else:
            print(f"No documents deleted from '{index_name}' with the given query.")
            
            
#     def search_data(self, index_name, query=None, size=10):
#         """
#         Elasticsearch에서 데이터를 검색하는 함수입니다. 결과를 DataFrame으로 반환합니다.
#         :param index_name: 검색할 인덱스 이름
#         :param query: Elasticsearch Query DSL을 사용한 검색 쿼리
#         :param size: 검색할 문서 수
#         :return: 검색된 문서들의 DataFrame
#         """
#         if query is None:
#             query = {
#                 "query": {
#                     "match_all": {}  # 모든 문서를 조회하는 기본 쿼리
#                 }
#             }
        
#         # 검색 수행
#         response = self.es.search(index=index_name, body=query, size=size)
        
#         # 검색 결과에서 hits 필드 가져오기
#         hits = response['hits']['hits']
        
#         # 결과를 쉽게 반환할 수 있도록 ID와 _source (실제 데이터)만 가져옵니다
#         results = [{
#             "_id": hit["_id"],
#             "_source": hit["_source"]
#         } for hit in hits]
        
#         # DataFrame으로 변환
#         df_results = pd.DataFrame(results)

#         # _source의 내용을 평탄화해서 컬럼화
#         if "_source" in df_results.columns:
#             # _source 내의 필드를 컬럼화
#             df_flat = pd.json_normalize(df_results["_source"])
#             # _id 컬럼과 합쳐서 반환
#             df_flat["_id"] = df_results["_id"]
            
#             return df_flat
#         else:
#             return df_results

#     def search_data_all(self, index_name, query=None, scroll='2m', size=1000):
#         """
#         Scroll API를 이용해 Elasticsearch에서 모든 데이터를 검색합니다.
#         :param index_name: 인덱스 이름
#         :param query: 검색 쿼리
#         :param scroll: scroll 유지 시간 (예: '2m' = 2분)
#         :param size: 한 번에 가져올 문서 수
#         :return: 전체 결과 DataFrame
#         """
#         if query is None:
#             query = {"query": {"match_all": {}}}
    
#         # 초기 검색
#         response = self.es.search(index=index_name, body=query, scroll=scroll, size=size)
#         scroll_id = response['_scroll_id']
#         hits = response['hits']['hits']
    
#         all_hits = hits.copy()
    
#         while True:
#             response = self.es.scroll(scroll_id=scroll_id, scroll=scroll)
#             hits = response['hits']['hits']
#             if not hits:
#                 break
#             all_hits.extend(hits)
    
#         # 결과 정리
#         results = [{
#             "_id": hit["_id"],
#             "_source": hit["_source"]
#         } for hit in all_hits]
    
#         df_results = pd.DataFrame(results)
#         if "_source" in df_results.columns:
#             df_flat = pd.json_normalize(df_results["_source"])
#             df_flat["_id"] = df_results["_id"]
#             return df_flat
#         else:
#             return df_results
    
#엘라스틱 버전(8.17.4) 변경으로 함수 수정        
    def search_data(self, index_name, query=None, size=10):
        """
        Elasticsearch에서 데이터를 검색하는 함수입니다. 결과를 DataFrame으로 반환합니다.
        :param index_name: 검색할 인덱스 이름
        :param query: Elasticsearch Query DSL을 사용한 검색 쿼리
        :param size: 검색할 문서 수
        :return: 검색된 문서들의 DataFrame
        """
        if query is None:
            query = {
                "match_all": {}  # v8에서는 내부에 'query' 키 없이 전달
            }

        # v8 방식: query 파라미터로 직접 전달
        response = self.es.search(index=index_name, query=query, size=size)

        hits = response['hits']['hits']
        results = [{
            "_id": hit["_id"],
            "_source": hit["_source"]
        } for hit in hits]

        df_results = pd.DataFrame(results)

        if "_source" in df_results.columns:
            df_flat = pd.json_normalize(df_results["_source"])
            df_flat["_id"] = df_results["_id"]
            return df_flat
        else:
            return df_results

#엘라스틱 버전(8.17.4) 변경으로 함수 수정
#     def search_data_all(self, index_name, query=None, scroll='2m', size=1000):
#         """
#         Scroll API를 이용해 Elasticsearch에서 모든 데이터를 검색합니다.
#         :param index_name: 인덱스 이름
#         :param query: 검색 쿼리
#         :param scroll: scroll 유지 시간 (예: '2m' = 2분)
#         :param size: 한 번에 가져올 문서 수
#         :return: 전체 결과 DataFrame
#         """
#         if query is None:
#             query = {"match_all": {}}

#         # 초기 검색
#         response = self.es.search(index=index_name, query=query, scroll=scroll, size=size)
#         scroll_id = response['_scroll_id']
#         hits = response['hits']['hits']
#         all_hits = hits.copy()

#         # Scroll 반복
#         while True:
#             response = self.es.scroll(scroll_id=scroll_id, scroll=scroll)
#             hits = response['hits']['hits']
#             if not hits:
#                 break
#             all_hits.extend(hits)

#         results = [{
#             "_id": hit["_id"],
#             "_source": hit["_source"]
#         } for hit in all_hits]

#         df_results = pd.DataFrame(results)
#         if "_source" in df_results.columns:
#             df_flat = pd.json_normalize(df_results["_source"])
#             df_flat["_id"] = df_results["_id"]
#             return df_flat
#         else:
#             return df_results
        
    def search_data_all(self, index_name, query=None, scroll='2m', size=1000, source_includes=None):
        if query is None:
            query = {"match_all": {}}

        search_kwargs = {
            "index": index_name,
            "query": query,
            "scroll": scroll,
            "size": size
        }
        if source_includes is not None:
            search_kwargs["_source"] = source_includes

        response = self.es.search(**search_kwargs)
        scroll_id = response['_scroll_id']
        hits = response['hits']['hits']
        all_hits = hits.copy()

        while True:
            response = self.es.scroll(scroll_id=scroll_id, scroll=scroll)
            scroll_id = response['_scroll_id']  # scroll_id 갱신
            hits = response['hits']['hits']
            if not hits:
                break
            all_hits.extend(hits)

        results = [{"_id": hit["_id"], "_source": hit["_source"]} for hit in all_hits]

        df_results = pd.DataFrame(results)
        if "_source" in df_results.columns:
            df_flat = pd.json_normalize(df_results["_source"])
            df_flat["_id"] = df_results["_id"]
            return df_flat
        else:
            return df_results

        
        
    def get_data_within_time(self,time_str, cmmt_index='data_cmmt_news', popular_index='data_popular_news', size=10000):
        # 입력받은 시간 기준으로 날짜 전까지의 데이터를 조회
        current_time = datetime.now()
    
        # n 시간 전 계산
        time_n_hours_ago = current_time - timedelta(hours=time_str)
        end_time=time_n_hours_ago.strftime("%Y-%m-%d %H:%M:%S")
        
        # cmmt와 popular 모두 동일한 시간 범위로 조회 (col_dtm 기준)
        query = {
            "query": {
                "range": {
                    "col_dtm": {
                        "gte": end_time  # "YYYY-MM-DD HH:MM:SS" 포맷으로
                    }
                }
            }
        }
        
        query2 = {
            "query": {
                "range": {
                    "COL_DTM": {
                        "gte": end_time  # "YYYY-MM-DD HH:MM:SS" 포맷으로
                    }
                }
            }
        }
        
        # cmmt 데이터를 조회
        df_cmmt = self.search_data_all(index_name=cmmt_index, query=query, size=10000)
    
        # popular 데이터를 조회
        df_popular = self.search_data_all(index_name=popular_index, query=query2, size=10000)
        df_popular=df_popular.drop_duplicates('URL')
        df_popular=df_popular.df_popular = df_popular.dropna(subset=['TITLE'])
        # 'news_id'와 'SERIAL_NO' 기준으로 조인
        df_combined = pd.merge(df_cmmt, df_popular, how='left', left_on='url', right_on='URL')
    
        return df_combined
        
    def get_data_within_time_bak(self,time_str, cmmt_index='data_cmmt_news', popular_index='data_popular_news', size=10):
        # 입력받은 시간 기준으로 날짜 전까지의 데이터를 조회
        current_time = datetime.now()
    
        # n 시간 전 계산
        time_n_hours_ago = current_time - timedelta(hours=time_str)
        end_time=time_n_hours_ago.strftime("%Y-%m-%d %H:%M:%S")
        
        # cmmt와 popular 모두 동일한 시간 범위로 조회 (col_dtm 기준)
        query = {
            "query": {
                "range": {
                    "col_dtm": {
                        "gte": end_time  # "YYYY-MM-DD HH:MM:SS" 포맷으로
                    }
                }
            }
        }
        
        query2 = {
            "query": {
                "range": {
                    "COL_DTM": {
                        "gte": end_time  # "YYYY-MM-DD HH:MM:SS" 포맷으로
                    }
                }
            }
        }
        
        # cmmt 데이터를 조회
        df_cmmt = self.search_data(index_name=cmmt_index, query=query, size=10000)
    
        # popular 데이터를 조회
        df_popular = self.search_data(index_name=popular_index, query=query2, size=10000)
    
        # 'news_id'와 'SERIAL_NO' 기준으로 조인
        df_combined = pd.merge(df_cmmt, df_popular, how='left', left_on='url', right_on='URL')
    
        return df_combined

# Elasticsearch 연결
#connector = ElasticConnector()  # es_config를 전달하지 않으면 기본값 사용

# 예시 DataFrame
#data = {
#    'name': ['Alice', 'Bob', 'Charlie'],
#    'age': [25, 30, 35],
#    'city': ['New York', 'San Francisco', 'Los Angeles']
#}

#df = pd.DataFrame(data)

# Elasticsearch에 데이터 삽입
#connector.dataframe_to_es(df, action="create")  # "create"는 새로 추가
