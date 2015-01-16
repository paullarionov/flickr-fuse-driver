#!/usr/bin/python
# -*- coding: utf-8 -*-

#установка flickrapi происходит следующим образом:
#sudo apt-get install python-flickrapi
#после установки становится доступной библиотека подключаемая ниже

import flickrapi
import hashlib
from urllib import urlopen, urlencode

#необходимо ввести ключи для приложения, которое получает доступ к flickr
#ключи можно получить тут http://www.flickr.com/services/apps/create/apply 
#ключи привязываются к вашему аккаунту
#после первой попытки аутентификации  с помощью данного приложения, открывается страница, где необходимо подтвердить аутентификацию
#после подтверждения необходимо нажать ENTER в консоли, откуда была вызвана программа. На этом аутентификация приложения завершается.

api_key = 'd1a53660e6e03b91bf96f67a1a0c417e'
api_secret = '73dcd179dfc0d89f'
token=''

class FlickrAPI:
    def __init__(self):
        self.photo_id=[]
        self.photo_name=[]
        self.photo_tags=[]
        self.set_id=[]
        self.set_name=[]
        self.photo_in_sets_id=[]
        self.photo_in_sets_name=[]
        self.photo_in_sets_tags=[]

    def getPhotosNotInSetsIds(self):
        method = 'flickr.photos.getNotInSet'
        xml = _doget(method)
        xml_list=xml.split(' ')
        for xml_el in xml_list:
            if xml_el[0:2]=='id':
                xml_el_list=xml_el.split('"')
                self.photo_id.append(xml_el_list[1])
        #print_list (self.photo_id)
        pass

    def getPhotosNotInSetsNamesAndTags(self):
        photo_tags_temp=[]
        st=0
        method = 'flickr.photos.getInfo'
        for id_el in self.photo_id:    
            xml = _doget(method, photo_id=id_el)
            xml_list=xml.split('<')
            for xml_el in xml_list:
                if xml_el[0:5]=='title':
                        xml_el_list=xml_el.split('>')
                        if xml_el[0:7]=='title /':
                            xml_el_list[1]='NoName'                           
                        self.photo_name.append(xml_el_list[1])
            for xml_el in xml_list:
                if xml_el[0:4]=='tag ':
                    xml_el_list=xml_el.split('"')
                    photo_tags_temp.append(xml_el_list[5])               
            self.photo_tags.append([])
            for tag_el in photo_tags_temp:
                self.photo_tags[st].append(tag_el)
            photo_tags_temp=[]     
            st=st+1
        print_list (self.photo_name)
        print_list (self.photo_tags)
        pass

    def getSets(self):
        method = 'flickr.photosets.getList'
        xml = _doget(method)
        xml_list=xml.split(' ')
        for xml_el in xml_list:
            if xml_el[0:2]=='id':
                xml_el_list=xml_el.split('"')
                self.set_id.append(xml_el_list[1])
        xml_list=xml.split('<')

        for xml_el in xml_list:
            if xml_el[0:5]=='title':
                xml_el_list=xml_el.split('>')
                if xml_el[0:7]=='title /':
                    xml_el_list[1]='NoName'      
                self.set_name.append(xml_el_list[1])
        #print_list (self.set_id)
        print_list (self.set_name)
        pass

    def getPhotosFromSetsIds(self):
        method = 'flickr.photosets.getPhotos'
        st=0
        for id_el in self.set_id:    
            xml = _doget(method, photoset_id=id_el)
            xml_list=xml.split('<')
            self.photo_in_sets_id.append([])
            for xml_el in xml_list:
                if xml_el[0:6]=='photo ':
                    xml_el_list=xml_el.split('"')
                    self.photo_in_sets_id[st].append(xml_el_list[1])
            st=st+1
        #print_list (self.photo_in_sets_id)
        pass

    def getPhotosFromSetsNamesAndTags(self):
        st=0
        photo_tags_temp=[]
        method = 'flickr.photos.getInfo'
        for id_el_2 in self.photo_in_sets_id: 
            self.photo_in_sets_tags.append([])
            self.photo_in_sets_name.append([])
            st2=0
            for id_el in id_el_2:   
                xml = _doget(method, photo_id=id_el)
                xml_list=xml.split('<')

                for xml_el in xml_list:
                    if xml_el[0:5]=='title':
                            xml_el_list=xml_el.split('>')
                            if xml_el[0:7]=='title /':
                                xml_el_list[1]='NoName'      
                            self.photo_in_sets_name[st].append(xml_el_list[1])
                for xml_el in xml_list:
                    if xml_el[0:4]=='tag ':
                        xml_el_list=xml_el.split('"')
                        photo_tags_temp.append(xml_el_list[5])                    
                self.photo_in_sets_tags[st].append([])
                for tag_el in photo_tags_temp:
                    self.photo_in_sets_tags[st][st2].append(tag_el)
                photo_tags_temp=[]
                st2=st2+1
            st=st+1
        print_list (self.photo_in_sets_name)
        print_list (self.photo_in_sets_tags)
        pass


def print_list(list_el):
    print '_______________________________________________________________'
    print list_el

def _doget(method, **params):
    api_params=[]
    for chocolate in params.items():
        api_params.append(chocolate[0])
        api_params.append(chocolate[1])
    api_sig=hashlib.md5(api_secret+'api_key'+api_key+'auth_token'+token+'method'+method+''.join(api_params)).hexdigest()
    url='http://www.flickr.com/services/rest/?api_key='+api_key+'&auth_token='+token+'&method='+method+'&api_sig='+api_sig+'&'+urlencode(params)
    xml = urlopen(url).read()
    return xml

#происходит загрузка ключей
flickr = flickrapi.FlickrAPI(api_key, api_secret)
#print flickr
#данная функция делает многое, помимо прочего проверяет наличие на диске токена в хэше, если токен уже создан, значит аутентификация уже была произведена, а если нет, то открывается страница для подтверждения.
#путь к токену по умолчанию ~/.flickr/
(token, frob) = flickr.get_token_part_one(perms='write')
#print token
#print frob
if not token: raw_input("Press ENTER after you authorized this program")
#данная функция служит для запоминания токена и последующего его использования при вызове API
flickr.get_token_part_two((token, frob))


s = FlickrAPI()
s.getPhotosNotInSetsIds()
s.getPhotosNotInSetsNamesAndTags()
s.getSets()
s.getPhotosFromSetsIds()
s.getPhotosFromSetsNamesAndTags()

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

