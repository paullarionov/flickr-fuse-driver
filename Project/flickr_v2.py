#!/usr/bin/python
# -*- coding: utf-8 -*-

#установка flickrapi происходит следующим образом:
#sudo apt-get install python-flickrapi
#после установки становится доступной библиотека подключаемая ниже

import flickrapi
import hashlib
from urllib import urlopen, urlencode
import xml.dom.minidom
import sys

#необходимо ввести ключи для приложения, которое получает доступ к flickr
#ключи можно получить тут http://www.flickr.com/services/apps/create/apply 
#ключи привязываются к вашему аккаунту
#после первой попытки аутентификации  с помощью данного приложения, открывается страница, где необходимо подтвердить аутентификацию
#после подтверждения необходимо нажать ENTER в консоли, откуда была вызвана программа. На этом аутентификация приложения завершается.

api_key = 'd1a53660e6e03b91bf96f67a1a0c417e'
api_secret = '73dcd179dfc0d89f'
token=''

class FlickrAPI:
    def __init__(self):                 #Конструктор класса, инициализирует списки, которые будут содержать:
        self.photo_id=[]                #id всех фотографий, не входящих в сеты
        self.photo_name=[]              #имена всех фотографий не входящих в сеты
        self.photo_tags=[]              #списки тегов для всех фотографий не входящих в сеты (вложенный список)
        self.set_id=[]                  #id всех сетов пользовтеля
        self.set_name=[]                #имена всех сетов пользователя
        self.photo_in_sets_id=[]        #списки id фотографий для всех сетов (вложенный список)
        self.photo_in_sets_name=[]      #списки имен фотографий для всех сетов (вложенный список)
        self.photo_in_sets_tags=[]      #списки тегов для всех фотографий для всех сетов (двойной уровень вложенности списков)

    def getPhotosNotInSetsIds(self):            #функция получения id фотографий не содержащихся в сетах
        method = 'flickr.photos.getNotInSet'    #API запрос на информацию о фотографиях не содержащихся в сетах
        dom = _doget(method)
        photo_nodes = dom.getElementsByTagName("photo") #получаем список узлов для тега photo
        for el in photo_nodes:
            self.photo_id.append(el.getAttribute("id").encode('utf-8')) #получаем атрибут id из тега photo
        print_list (self.photo_id)
        pass

    def getPhotosNotInSetsNamesAndTags(self):   #функция получения имен и тегов фотографий не входящих в сеты
        st=0
        method = 'flickr.photos.getInfo'        #API запрос на полную информацию о фотографиии
        for id_el in self.photo_id:    
            dom = _doget(method, photo_id=id_el)
            nodelist = dom.getElementsByTagName("title")[0].childNodes #получаем содержимое узла title
            title_content = self.getContentOfTags(nodelist)            #вызываем нашу функцию по получению содержимого узла
            self.photo_name.append(title_content.encode('utf-8'))
            tag_nodes = dom.getElementsByTagName("tag")  
            self.photo_tags.append([])
            for el in tag_nodes:
                nodelist = el.childNodes        #получаем список узлов содержащихся в узле tag
                tag_content = self.getContentOfTags(nodelist)
                self.photo_tags[st].append(tag_content.encode('utf-8'))  
            st=st+1
        print_list (self.photo_name)
        print_list (self.photo_tags)
        pass

    def getContentOfTags(self,nodelist):        #функция по получению содержимого узла
        rc=[]
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)                                    
        return ''.join(rc)

    def getSets(self):                          #получаем id всех сетов пользователя                  
        method = 'flickr.photosets.getList'
        dom = _doget(method)
        photoset_nodes = dom.getElementsByTagName("photoset")
        for el in photoset_nodes:
            self.set_id.append(el.getAttribute("id").encode('utf-8'))

        title_nodes = dom.getElementsByTagName("title")
        for el in title_nodes:
            nodelist = el.childNodes
            title_content = self.getContentOfTags(nodelist)
            self.set_name.append(title_content.encode('utf-8'))                              
        print_list (self.set_id)
        print_list (self.set_name)
        pass

    def getPhotosFromSetsIds(self):             #получаем id всех фотографий для всех сетов пользователя 
        method = 'flickr.photosets.getPhotos'
        st=0
        for id_el in self.set_id:
            dom = _doget(method, photoset_id=id_el)
            photo_nodes = dom.getElementsByTagName("photo")
            self.photo_in_sets_id.append([])
            for el in photo_nodes:
                self.photo_in_sets_id[st].append(el.getAttribute("id").encode('utf-8'))              
            st=st+1
        print_list (self.photo_in_sets_id)
        pass

    def getPhotosFromSetsNamesAndTags(self):  #получаем именя и теги всех фотографий для всех сетов пользователя 
        st=0
        method = 'flickr.photos.getInfo'
        for id_el in self.photo_in_sets_id:
            self.photo_in_sets_tags.append([])
            self.photo_in_sets_name.append([])
            st2=0
            for id_el_2 in id_el:    
                dom = _doget(method, photo_id=id_el_2)
                nodelist = dom.getElementsByTagName("title")[0].childNodes
                title_content = self.getContentOfTags(nodelist)
                self.photo_in_sets_name[st].append(title_content.encode('utf-8'))
                tag_nodes = dom.getElementsByTagName("tag")
                self.photo_in_sets_tags[st].append([])
                for el in tag_nodes:
                    nodelist = el.childNodes
                    tag_content = self.getContentOfTags(nodelist)
                    self.photo_in_sets_tags[st][st2].append(tag_content.encode('utf-8'))    
                st2=st2+1
            st=st+1
        print_list (self.photo_in_sets_name)
        print_list (self.photo_in_sets_tags)
        pass

    def getPhotosSizesFromIds(self, id_el): #в функцию передается id фотографии
        method = 'flickr.photos.getSizes'   #вызов метода для получения ссылок на все размеры данного изображения
        dom = _doget(method, photo_id=id_el)
        url_nodes = dom.getElementsByTagName("size")
        urls_id=[]
        for el in url_nodes:
            urls_id.append(el.getAttribute("source").encode('utf-8'))
        
        return urls_id[len(urls_id)-1]     #возвращаем последнюю ссылку (на самое большое изображения Large)      
        

def print_list(list_el):                      #выводим список
    print '_______________________________________________________________'
    print list_el

def _doget(method, **params):                 #функция выполнения API методов, возвращает xml структуру dom после её парсинга.
    api_params=[]
#заполняем список api_params параметрами, которые будут использоваться для создания ссылки
#ссылка будет выполнять запрос, соответствующий API методу передаваемому аргументом method
    for chocolate in params.items():
        api_params.append(chocolate[0])
        api_params.append(chocolate[1])
#вычисляем значение параметра api_sig используемого в выше описанной ссылке, как ключ доступа к фс пользователя
    api_sig=hashlib.md5(api_secret+'api_key'+api_key+'auth_token'+token+'method'+method+''.join(api_params)).hexdigest()
#формируем саму ссылку
    url='http://www.flickr.com/services/rest/?api_key='+api_key+'&auth_token='+token+'&method='+method+'&api_sig='+api_sig+'&'+urlencode(params)
#получаем ответ на запрос по полученной ссылке и выполняем его парсинг
    dom = xml.dom.minidom.parse(urlopen(url))
#возвращаем полученную после парсинга структуру, с которой будем работать методами библиотеки xml.dom.minidom
    return dom

#происходит загрузка ключей
flickr = flickrapi.FlickrAPI(api_key, api_secret)
#print flickr
#данная функция делает многое, помимо прочего проверяет наличие на диске токена в хэше, если токен уже создан, значит аутентификация уже была произведена, а если нет, то открывается страница для подтверждения.
#путь к токену по умолчанию ~/.flickr/
try:
	(token, frob) = flickr.get_token_part_one(perms='write')
except Exception as ex:
	print "Error Type: " + ex.args[0]
	sys.exit(-1)
if not token: raw_input("Press ENTER after you authorized this program")
#данная функция служит для запоминания токена и последующего его использования при вызове API
flickr.get_token_part_two((token, frob))


#непосредственно вызов наших функций

















#НИЖЕ ПОКА НЕ ИСПОЛЬЗУЕМЫЙ КОД:


#вызов функции загрузки изображения на flickr
#filename - полный путь к изображению
#среди параметров также есть:
#   title - The title of the photo

#   description - The description of the photo

#   tags - Space-delimited list of tags. Tags that contain spaces need to be quoted. For example: tags='''Amsterdam "central station"'''

#   is_public - "1" if the photo is public, "0" if it is private. The default is public.

#   is_family - "1" if the private photo is visible for family, "0" if not. The default is not.

#   is_friend - "1" if the private photo is visible for friends, "0" if not. The default is not.


#ДАННЫЙ ПАРАМЕТР ЗАСТАВИТЬ РАБОТАТЬ НЕ УДАЛОСЬ. НО ОН ПО СУТИ НАФИГ НЕ НУЖЕН НАМ.
#   callback - This should be a method that receives two parameters, progress and done. The callback method will be called every once in a while during uploading. Example:
#def func(progress, done):
#    if done:
#        print "Done uploading"
#    else:
#        print "At %s%%" % progress
#flickr.upload(filename='test.jpg', callback=func) 


#   format - The response format. This must be either rest or one of the parsed formats etree / xmlnode.

#!!!!!!!!!!!!!!!!!!!flickr.upload(filename='test.jpg',title='Муж и жена', description='Хочет тачилу', tags='Отношения')

#результат можно посмотреть по ссылке http://www.flickr.com/photos/68941900@N02/ 
#если загружать несколько раз, то изображение на сайте просто дублируется
#изменять параметры уже загруженного тоже можно, но это пока на не нужно

