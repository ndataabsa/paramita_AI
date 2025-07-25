from lxml import html,etree

import requests
import traceback
import re
import pandas as pd

class Tag:
    def __init__(self, name, text='', attributes=None):
        self.name = name
        self.text = text
        self.attributes = attributes if attributes else {}
        self.children = []
        self.parent=None

        self.text_all=self.get_text_all()
        
    def children_tag(self,tag=None):
        if tag==None:return [x for x in self. children if not isinstance(x,str)]
        return [x for x in self. children if not isinstance(x,str) and tag==x.name]
    def children_str(self):return [x for x in self. children if isinstance(x,str)]

    def __repr__(self):
    
        # element = etree.Element(self.name, **self.attributes)
        # element.text = self.text
        # for child in self.children_tag():
        #     child_element = etree.Element(child.name, **child.attributes)
        #     child_element.text = child.text
        #     element.append(child_element)
        
        # # Convert the element to a string
        # return etree.tostring(element, pretty_print=True, encoding='unicode')
        return (f"Tag(name={self.name}, text={self.text}, "
                f"attributes={self.attributes}, children={self.children_tag()})")

    def to_html(self):
        result='<'+self.name
        for i in self.attributes.keys():result=result+' '+i+'="'+self.attributes[i]
        result=result+'">'
        result=result+self.text

        for i in self.children:
            if isinstance(i,str):result=result+i
            else: result=result+i.to_html()
        
        result=result+'</'+self.name+'>'
        return result
        
    def to_xpath(self):
        if self.parent==None: return '/'+self.name
        temp_lst=self.parent.children_tag(self.name)
        if len(temp_lst)>1:
            for i in range(len(temp_lst)):
                if temp_lst[i]==self:
                    return f'''{self.parent.to_xpath()}/{self.name}[{str(i+1)}]'''
            raise Exception('xpath 생성 오류')
        return self.parent.to_xpath()+'/'+self.name

    def to_dataframe(self):
        if self.name!='table':return None
        return pd.read_html(self.to_html())
#------------------------------------------------------find_type: name
    def find_element_name(self,name):
        for i in self.children_tag():
            if i.name==name : return i
                
    def find_elements_name(self,name):
        result=[]
        for i in self.children_tag():
            if i.name==name : result.append(i)
        return result
                
    def find_element_name_all(self,name):
        if self.name==name:return self
        for i in self.children_tag():
            result=i.find_element_name_all(name)
            if result !=None: return result
        
    def find_elements_name_all(self,name):
        result=[]
        if self.name==name:result.append(self)
        for i in self.children_tag():
            result.extend(i.find_elements_name_all(name))
        return result
#------------------------------------------------------find_type: text
    def find_element_text(self,text):
        if self.text==text:return self
        for i in self.children_tag():
            if i.text==text: return i
                
    def find_elements_text(self,text):
        result=[]
        for i in self.children_tag():
            if i.text==text: result.append(i)
        return result
        
    def find_element_text_all(self,text):
        if self.text==text:return self
        for i in self.children_tag():
            result=i.find_element_text_all(text)
            if result !=None: return result
                
    def find_elements_text_all(self,text):
        result=[]
        if self.text==text:result.append(self)
        for i in self.children_tag():
            result.extend(i.find_elements_text_all(text))
        return result
   
    def find_elements_text_all_in(self,text):
        result=[]
        if self.text_all().find(text)>-1:result.append(self)
            
        for i in self.children_tag():
            result.extend(i.find_elements_text_all_in(text))
        return result
        
    def find_element_text_all_par(self,text):
        for i in self.children_tag():
            if i.text==text:return self
                
        for i in self.children_tag():
            result=i.find_element_text_all_par(text)
            if result !=None: return result
#------------------------------------------------------find_type: class

    def find_element_class(self,class_name):
        if 'class' in self.attributes:
            if self.attributes['class']==class_name:return self
                
        for i in self.children_tag():
            if 'class' in i.attributes:
                if i.attributes['class']==class_name:return i
                
    def find_elements_class(self,class_name):
        result=[]
        for i in self.children_tag():
            if 'class' in i.attributes:
                if i.attributes['class']==class_name:result.append(i)
        return result
                
    def find_element_class_all(self,class_name):
        if 'class' in self.attributes:
            if self.attributes['class']==class_name:return self
        
        for i in self.children_tag():
            result=i.find_element_class_all(class_name)
            if result!=None: return result

    def find_elements_class_all(self,class_name):
        datas=[]
        if 'class' in self.attributes:
            if self.attributes['class']==class_name: datas.append(self)
        
        for i in self.children_tag():
            result=i.find_elements_class_all(class_name)
            if result!=None: datas.extend(result)
        return datas
    
    def find_element_class_all_contain(self,class_name):
        for i in self.children_tag():
            if 'class' in i.attributes:
                if i.attributes['class'].find(class_name)>-1:return i
        
        for i in self.children_tag():
            result=i.find_element_class_all_contain(class_name)
            if result!=None: return result

#------------------------------------------------------find_type: id

    def find_element_id(self,id_name):
        if 'id' in self.attributes:
            if self.attributes['id']==id_name:return self
                
        for i in self.children_tag():
            if 'id' in i.attributes:
                if i.attributes['id']==id_name:return i
                
    def find_elements_id(self,id_name):
        result=[]
        for i in self.children_tag():
            if 'id' in i.attributes:
                if i.attributes['id']==id_name:result.append(i)
        return result
                
    def find_element_id_all(self,id_name):

        
        if 'id' in self.attributes:
            if self.attributes['id']==id_name:return self
        
        for i in self.children_tag():
            result=i.find_element_id_all(id_name)
            if result!=None: return result

    def find_elements_id_all(self,id_name):
        datas=[]
        if 'id' in self.attributes:
            if self.attributes['id']==id_name: datas.append(self)
        
        for i in self.children_tag():
            result=i.find_elements_id_all(id_name)
            if result!=None: datas.extend(result)
        return datas
    
    
    def find_element_id_all_contain(self,id_name):
        for i in self.children_tag():
            if 'id' in i.attributes:
                if i.attributes['id'].find(id_name)>-1:return i
        
        for i in self.children_tag():
            result=i.find_element_id_all_contain(id_name)
            if result!=None: return result

#------------------------------------------------------find_type: attributes

    
    def find_element_attribute(self,type,name):
        if type in self.attributes:
            if self.attributes[type]==name:return self
                
        for i in self.children_tag():
            if type in i.attributes:
                if i.attributes[type]==name:return i
                
    def find_elements_attribute(self,type,name):
        result=[]
        for i in self.children_tag():
            if type in i.attributes:
                if i.attributes[type]==name:result.append(i)
        return result
                
    def find_element_attribute_all(self,type,name):
        results=[]
        if type in self.attributes:
            if self.attributes[type]==name:results.append(self)
        
        for i in self.children_tag():
            results.extend(i.find_element_attribute_all(type,name))
        return results


    
    def find_element_attribute_all_contain(self,type,name):
        results=[]
        if type in self.attributes:
            if self.attributes[type].find(name)>-1:results.append(self)
        
        for i in self.children_tag():
            results.extend(i.find_element_attribute_all_contain(type,name))
            
        return results
#------------------------------------------------------find_type: xpath

    def _process_xpath_part(self, xpath_part, current):
        tag_name = None
        i = 0
        while i < len(xpath_part):
            if i+1 < len(xpath_part) and xpath_part[i:i+2] == '..':
                current = current.parent
                i += 2
            elif i+1 < len(xpath_part) and xpath_part[i:i+2] == '//':
                while current.parent:
                    current = current.parent
                i += 2
            elif xpath_part[i] == '/':
                while current.parent:
                    current = current.parent
                i += 1
            elif xpath_part[i] == '.':
                i += 1
            elif xpath_part[i] == '*':
                tag_name = '*'
                i += 1
            else:
                # 태그 이름 파싱
                tag = ''
                while i < len(xpath_part) and xpath_part[i] not in ['/', '.', '*']:
                    tag += xpath_part[i]
                    i += 1
                if tag:
                    tag_name = tag
                    current = current.find_element_name(tag)
        return current, tag_name

    def find_element_xpath_sub(self, xpath):
        if xpath == '': return self
        
        current = self
        
        # 대괄호를 기준으로 3부분으로 나누기
        before = xpath[:xpath.find('[')]
        inside = xpath[xpath.find('[')+1:xpath.find(']')]
        after = xpath[xpath.find(']')+1:]
        parts = [before, inside, after]
        
        # before 처리
        current, tag_name = self._process_xpath_part(before, current)
                    
        # 속성 처리
        if inside:
            if inside.startswith('text()='):
                text_value = inside[7:].strip("'")
                elements = current.find_elements_text_all(text_value)
                if elements:
                    current = elements[0]
            else:
                attr_name = inside.split('=')[0].strip('@')
                attr_value = inside.split('=')[1].strip("'")
                elements = current.find_elements_attribute_all(attr_name, attr_value)
                if elements:
                    current = elements[0]
                    
        # after 처리
        if after:
            current, _ = self._process_xpath_part(after, current)
            
        return current

    def find_element_xpath(self,xpath):
        if xpath=='':return self
        if xpath.startswith("/html") or (xpath.startswith("/") or xpath.startswith("/body")  and not xpath.startswith("//")):  # full xpath인 경우
            if xpath[0]=='/': xpath=xpath[1:]
            if xpath[:5]=='html/': xpath=xpath[5:]
            if xpath[-1]=='/':xpath=xpath[:-1]
            if(xpath.find('/'))==-1:
                left_xpath=xpath
                right_xpath=''
            else:
                left_xpath=xpath.split('/')[0]
                right_xpath=xpath[len(xpath.split('/')[0]):]
                
            try:
                if left_xpath.find('[')>-1:
                    tag=left_xpath[:left_xpath.find('[')]
                    num=int(left_xpath[left_xpath.find('[')+1:-1])
                    return self.find_elements_name(tag)[num-1].find_element_xpath(right_xpath)
                else:
                    return self.find_element_name(left_xpath).find_element_xpath(right_xpath)
                    
            except Exception as E:
                traceback.print_exc()
                print(left_xpath,end=': 해당 태그에 문제가 있는것 같습니다 확인해주세요')
        else:  # 일반 xpath인 경우
            return self.find_element_xpath_sub(xpath)




    






#----------------------------------------------------------------------------------------------------------------------------------------------------#
#----------------------------------------------------------------find data---------------------------------------------------------------------------#
#----------------------------------------------------------------------------------------------------------------------------------------------------#
    

#------------------------------------------------------get_type: href
    # def get_href(self):
    #     if 'href' in self.attributes:
    #         return self.attributes['href']
        
    #     for i in self.children:
    #         data=i.get_href()
    #         if data!=None: return data
        
    def get_href(self):
        if 'href' in self.attributes:
            return self.attributes['href']
        
        for i in self.children_tag():
            data=i.get_href()
            if data!=None: return data
        
    def get_hrefs(self):
        results=[]
        if 'href' in self.attributes:
            results.append(self.attributes['href'])
        
        for i in self.children_tag():
            results.extend(i.get_hrefs())
        return results
#------------------------------------------------------get_type: text
    def get_text_all(self,max_depth=3,depth=1):
        if max_depth>0 and depth>max_depth: return ''
        result=self.text
        for i in self.children:
            if isinstance(i,str):result+=i
            else:result=result+i.get_text_all(max_depth,depth+1)

        return result

    def get_texts_all(self,max_depth=3,depth=1):
        if max_depth>0 and depth>max_depth: return ''
        result=[]
        result.append(self.text)
        for i in self.children:
            if isinstance(i,str):result.append(i)
            else:result.extend(i.get_texts_all(max_depth,depth+1))

        return result
    
    def get_text_all_tagonly(self,max_depth=3,depth=1):
        if max_depth>0 and depth>max_depth: return ''
        result=self.text

        for i in self.children_tag(): result=result+i.get_text_all_tagonly(max_depth,depth+1)

        return result

    def get_text_all_without_script(self,max_depth=3,depth=1):
        if max_depth>0 and depth>max_depth: return ''
        if self.name=='script':return ''
        result=self.text
        for i in self.children:
            if isinstance(i,str):result+=i
            else:result=result+i.get_text_all_without_script(max_depth,depth+1)

        return result

    def get_next(self):
        SW=False
        if self.parent==None:return None
        for i in range(len(self.parent.children_tag())):
            if SW:return self.parent.children_tag()[i]
            if self.parent.children_tag()[i]==self:SW=True
    

        





#------------------------------------------------------get_type: other

    def find_elements_has_text(self):
        result=[]
        if len(self.children_str())>0:result.append(self)
        elif self.text!='':result.append(self)
        for i in self.children_tag():
            result.extend(i.find_elements_has_text())
        return result

















def parse(element):
    if isinstance(element,str):
        
        comment_pattern = re.compile(r'<!--.*?-->', re.DOTALL)
        data = re.sub(comment_pattern, '', element)
        element = html.fromstring(data)
        #주석 제거
        
    tag = Tag(name=element.tag, attributes=dict(element.attrib))
    tag.text = (element.text or '').strip()

    for child in element:
        temp=parse(child)
        tag.children.append(temp)
        temp.parent=tag
        if child.tail:
            tag.children.append(child.tail)
            
    # for child in element:
    #     tag.children.append(parse_element(child))
    
    return tag




# def parse_element(element):
#     if isinstance(element,str):
        
#         comment_pattern = re.compile(r'<!--.*?-->', re.DOTALL)
#         data = re.sub(comment_pattern, '', element)
#         element = html.fromstring(data)
#         #주석 제거
        
#     tag = Tag(name=element.tag, attributes=dict(element.attrib))
#     tag.text = (element.text or '').strip()
    
#     for child in element:
#         tag.children.append(parse_element(child))
    
#     # Append tail text (text after child elements)
#     if element.tail:
#         tag.text += (element.tail or '').strip()
    
#     return tag







