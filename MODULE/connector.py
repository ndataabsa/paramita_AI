import os

default_directory=os.path.dirname(os.path.abspath(__file__))+'/DB_INFO.txt'

import json
import urllib.request
from sqlalchemy import MetaData, Table, create_engine, select, and_
def info():
    print('''
    #test_info : 83서버연결
    #info      : 82서버연결
    #new_info  : cloude연결
    ''')
def data():
    with open(default_directory,'r') as f:
        return json.load(f)
        
def connect(db_info='test_info'): 
    db=data()['datas'][db_info]

    str_db_password = urllib.parse.quote_plus(db['Password'])
    database_url = "mysql+pymysql://"+db['UserName']+":"+str_db_password+"@"+db['mysqlUrl'] # f : format 
    engine = create_engine(database_url)
    mysqlConn = engine.connect()

    return engine, mysqlConn
    
import pymysql

# 데이터베이스 연결 설정
def connect2(db_info='test_info'):
    db=data()['datas'][db_info]
    connection = pymysql.connect(
        host=db['mysqlUrl'].split(':')[0],
        user=db['UserName'],
        password=db['Password'],  # 실제 비밀번호로 교체

    )
    return connection
def update(query,db_info='test_info'):
    c=connect2(db_info)
    c.cursor().execute(query)
    c.commit()
    c.close()