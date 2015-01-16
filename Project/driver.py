#!/usr/bin/python
# -*- coding: utf-8 -*-
#/home/larionovpa/fuse-driver/Project/FS

import flickrapi
import hashlib
import xml.dom.minidom
import sys
import os

from collections import deque
import threading
import ConfigParser
#import tempfile

from urllib import urlopen, urlencode
import time

import fuse
import stat
#from fs.expose import fuse as fp

#-----------------------------------------------------------------------ФОТОГРАФИЯ
class Photo:
	def __init__(self, IDnumber):
		self.ID=IDnumber	#идентификатор фотографии
		self.title = ""		#заголовок
		self.posted=""		#дата загрузки
		self.taken=""		#дата сьемки
		self.lastupdate=""	#дата обновления
		self.url = "" 		#URL
		#----Структуры и дескрипторы
		self.tags = [] 		#список тегов

		self.sets = []		#список сетов
		self.length = 0 	#размер файла
		self.data = '' 		#содержимое файла

		pass

	def __str__(self):
		return str(self.title)

	def ParseXML(self, Photo):
		nodes = Photo.getElementsByTagName("title")
		self.title = unicode(nodes[0].firstChild.nodeValue).encode('utf-8') 

		nodes = Photo.getElementsByTagName("dates")
		self.posted=unicode(nodes[0].getAttribute("posted")).encode('utf-8') 
		self.taken=unicode(nodes[0].getAttribute("taken")).encode('utf-8') 
		self.lastupdate=unicode(nodes[0].getAttribute("lastupdate")).encode('utf-8') 
		
		nodes = Photo.getElementsByTagName("url")
		self.url = unicode(nodes[0].firstChild.nodeValue).encode('utf-8') 
		
		nodes = Photo.getElementsByTagName("tag")
		for i in nodes:
			self.tags.append(unicode(i.firstChild.nodeValue).encode('utf-8'))	
		pass

	def write(self, buf, offset):
		if offset < len(self.data):
			before = self.data[:offset]
			after = self.data[offset+len(buf):]
		else:
			if offset > len(self.data):
				self.truncate(offset)
		before = self.data
		after = ''
		self.data = before + buf + after
		self.length = len(self.data)	
		return len(buf)

	def read(self, size, offset):
		return self.data[offset:offset+size]

	def truncate(self, size):
		if size < len(self.data):
			self.data = self.data[:size]
			self.stat.st_size = size
		elif size > len(self.data):
			self.data = self.data + '\0'*(size-len(self.data))
			self.stat.st_size = size



#-----------------------------------------------------------------------ТЕГ
class Tag:
	def __init__(self):
		self.title = ""
		pass

	def  __str__(self):
		return self.title

	def ParseXML(self, pTag):
		self.title = unicode(pTag.firstChild.nodeValue).encode('utf-8')
		pass



#-----------------------------------------------------------------------СЕТ
class PhotoSet:
	def __init__(self):

		self.ID=""		#идентификатор тега
		self.date_create = ""	#дата создания
		self.date_update = ""	#дата обновления
		self.title = ""		#заголовок
		self.description = ""	#описание
		pass

	def __str__(self):
		return self.title

	def ParseXML(self, Photoset):
		self.ID=unicode(Photoset.getAttribute("id")).encode('utf-8')
		self.date_create = unicode(Photoset.getAttribute("date_create")).encode('utf-8')
		self.date_update = unicode(Photoset.getAttribute("date_update")).encode('utf-8')

		t = Photoset.getElementsByTagName('title')
		if t:
			self.title = unicode(t[0].firstChild.nodeValue).encode('utf-8')

		# Описания может и не быть/ Если понядобится - сделаем
		pass



class FileSystem(fuse.Fuse):	#Класс файловой системы (наследуется от fuse.Fuse):

	api_key = '*'
	api_secret = '*'

	FS = dict()		#Файловая система
	Photos = dict()		#Множество всех фотографий
	PhotosURL = dict()	#Словарь, содрежащий списки URL на разные разрешения для каждой фотографии
	PhotosType = dict()     #Словарь, содержащий расширения фотографий

	UpdateIsInProgress = False
	UThread = 0
	UploadPhotos = list()	#Множество всех фотографий
	Tags = list()		#Множество всех тегов
	PhotoSets = list()	#Множество всех сетов

	cachedir='/tmp/Flickr'	#Путь для кэша
	UploadQ = deque()	#Очередь загрузки

	cachedir=''	#Путь для кэша
	log_path=''     #Путь для лог файла
	config = ConfigParser.RawConfigParser()
	def __init__(self, *args, **kw):
		self.__CreateConfig__()
		self.__ReadConfig__()
		self.__RunLogFile__()

		self.__CreateTempDir__()	
		self.__CleanTempDir__()
		self.__ConnectToFlickr__()
	
		self.__GetUserID__()
		self.__GetTags__()
		self.__GetPhotos__()

		self.__GetPhotoSets__()
		self.__ScanPhotoSetsForPhotos__()
		
		self.__ConstructFS__()

		fuse.fuse_python_api = (0, 2)
		self.block_size = 1024
		self.block_count = 4

		self.currentDirectory = os.getcwd()
		
		print "----------------------------------------------------------" 
		print "-                FUSE-driver for FLICKR.COM              -" 
		print "- Driver started successfuly, see details in log-file:   -"
		print "- " + str(self.log_path)+' '*(55-len(self.log_path))+"-"
 		print "----------------------------------------------------------" 

		fuse.Fuse.__init__(self, *args, **kw)

		pass


	def __del__(self):
		self.__StopLogFile__()


	def __CreateConfig__(self):	
		self.config.add_section('Section1')
		self.config.set('Section1', 'tmp_path', '/tmp/Flickr')
		self.config.set('Section1', 'log_path', os.path.abspath(os.curdir)+'/'+'log.txt')
		self.config.set('Section1', 'api_key', '*')
		self.config.set('Section1', 'api_secret', '*')
		if os.path.exists('config.cfg')==False:
			with open('config.cfg', 'wb') as configfile:
				self.config.write(configfile)


	def __ReadConfig__(self):
		self.config.read('config.cfg')
		self.cachedir=self.config.get('Section1', 'tmp_path')
		self.log_path=self.config.get('Section1', 'log_path')
		self.api_key=self.config.get('Section1', 'api_key')
		self.api_secret=self.config.get('Section1', 'api_secret')

	def __CleanTempDir__(self):					#при запуске очищаем устаревшие данные в кэше
		i=1
		while i<7:
			for root, dirs, files in os.walk(os.path.join(self.cachedir, str(i)), topdown=False):
				for name in files:
					os.remove(os.path.join(root, name))
			i=i+1


	def __CreateTempDir__(self):					#создаем дирректорию в tmp для кэша
		try:
			os.mkdir(self.cachedir)
			i=1
			while i<7: 
				os.mkdir(os.path.join(self.cachedir, str(i)))
				i=i+1
		except OSError as ex:

			self.__ToLog__("__init__: Cash dir already exists.")
		except Exception as ex:
			self.__ToLog__("__init__: Make cash dir error: " + str(ex.args[0]))



	def __RunLogFile__(self):
		self.Log = open (self.log_path, 'w')

		self.__ToLog__("----------- Logging is started -----------")



	def __ToLog__(self, Message):

		self.Log.write(str(time.time()) + ":	" + Message + "\r\n")
		self.Log.flush()	



	def __StopLogFile__(self):
		self.__ToLog__("----------- Logging is stoped -----------")
		self.Log.flush()
		self.Log.close()		



	#------------------------------ВЗАИМОДЕЙСТВИЕ С FLICKR.COM
	def __ConnectToFlickr__(self):
		if self.api_key=='*' or self.api_secret=='*':
			self.__ToLog__("Flickr Connection Error: : please write api_key and api_secret in config.cfg")
			sys.exit(-1)
		self.flickr = flickrapi.FlickrAPI(self.api_key, self.api_secret) 	#загрузка ключей

		#print flickr
		try:
			(self.token, frob) = self.flickr.get_token_part_one(perms='write')
		except Exception as ex:
			print "Flickr Connection Error: " + ex.args[0]
			sys.exit(-1)
		#print "token: ", self.token
		if not self.token:
			raw_input("Press <ENTER> after you authorized on FLICK.COM")

		self.flickr.get_token_part_two((self.token, frob))			#запоминание токена и последующее его использование при вызове API

		#print '	Connected to Flickr'
		pass



	def __DoFlickrMethod__(self, method, **params):					#Возвращает XML структуру dom после её парсинга.
		sortedParamsList=[]							#список параметров метода

		urlEncodeList = []
		for key in sorted(params.iterkeys()):
    			sortedParamsList.append(key)
			sortedParamsList.append(params[key])
			urlEncodeList.append(urlencode({key:params[key]}))
		urlEncodeStr = '&'.join(urlEncodeList)
		#вычисляем значение параметра api_sig используемого в выше описанной ссылке, как ключ доступа к фс пользователя
	    	api_sig=hashlib.md5(self.api_secret+'api_key'+self.api_key+'auth_token'+self.token+'method'+method+''.join(sortedParamsList)).hexdigest()
		#формируем ссылку
	    	url='http://www.flickr.com/services/rest/?api_key='+self.api_key+'&auth_token='+self.token+'&method='+method+'&'+urlEncodeStr+'&api_sig='+api_sig
		#print url
		resp = urlopen(url)

		#print resp
	    	dom = xml.dom.minidom.parse(resp) 					#получаем ответ и выполняем его парсинг

		nodes = dom.getElementsByTagName('rsp')
		stat = nodes[0].getAttribute("stat").upper()
		#print stat
		if stat!='OK':
			nodes = dom.getElementsByTagName('err')
			if nodes!=[]:
				stat=nodes[0].getAttribute("msg")
			raise ValueError(stat)
		else:
		    	return dom



	def __GetUserID__(self):
		method = 'flickr.urls.getUserPhotos'
		try:
			dom = self.__DoFlickrMethod__(method)
		except Exception as ex:
			sys.exit(-1)

		nodes = dom.getElementsByTagName("user")

		FileSystem.user_id = nodes[0].getAttribute("nsid")
		#print FileSystem.user_id
		pass



	def __GetPhotoSets__(self):
		method = 'flickr.photosets.getList'
		try:
			dom = self.__DoFlickrMethod__(method)
		except Exception as ex:
			sys.exit(-1)

		nodes = dom.getElementsByTagName("photoset")

		for i in nodes:
			iSet = PhotoSet()
			iSet.ParseXML(i)
			#print iSet.ID
			#print iSet.date_create
			#print iSet.title
			self.PhotoSets.append(iSet)
		pass



	def __GetTags__(self):
		method = 'flickr.tags.getListUser'
		try:
			dom = self.__DoFlickrMethod__(method)
		except Exception as ex:
			print ex.args[0]
			sys.exit(-1)

		nodes = dom.getElementsByTagName("tag")

		for i in nodes:
			iTag = Tag()
			iTag.ParseXML(i)
			#print iTag.pTag
			self.Tags.append(iTag)
		pass



	def __GetPhotos__(self, pTag = ""):		
		method = 'flickr.photos.search'
		if self.user_id==False:
			return
		pPage = "1"

		iCount = 1
		bContinue = True	#, page=pPage

		while bContinue:
			try:
				dom = self.__DoFlickrMethod__(method,page=pPage,user_id=self.user_id)
			except Exception as ex:
				print ex.args[0]
				sys.exit(-1)		
	
			nodes = dom.getElementsByTagName("photos")
			if iCount==1:
				try:
					iPages = int(nodes[0].getAttribute("pages"))
					#print iPages
				except ValueError:
					print ex.args[0]
					sys.exit(-1)
			
			nodes = dom.getElementsByTagName("photo")
			for i in nodes:
				ID = i.getAttribute("id")
				#print ID
				if (self.Photos.get(ID, -1)==-1):
					self.Photos[ID] = Photo(ID)
					self.Photos[ID].ParseXML(self.__GetPhotoInfo__(ID))
					self.PhotosURL[ID],self.PhotosType[ID]=self.__PhotosSizesFromIds__(ID)		#получение ссылок на все разрешения изображения по его ID
			iCount+=1			
			pPage = str(iCount)
			if iCount>iPages: bContinue=False
		pass	



	def __GetPhotoInfo__(self, ID):
		method = 'flickr.photos.getInfo'
		try:
			dom = self.__DoFlickrMethod__(method, photo_id=ID)
		except Exception as ex:
			print ex.args[0]
			sys.exit(-1)

		return dom



	def __ScanPhotoSetsForPhotos__(self):
		method = 'flickr.photosets.getPhotos'
		for i in self.PhotoSets:
			try:
				dom = self.__DoFlickrMethod__(method, photoset_id=i.ID)
			except Exception as ex:
				print ex.args[0]
				sys.exit(-1)

			nodes = dom.getElementsByTagName("photo")
			for j in nodes:
				photoID = unicode(j.getAttribute("id")).encode('utf-8')
				self.Photos[photoID].sets.append(i)



	def __PhotosSizesFromIds__(self, ID): 				#в функцию передается id фотографии
		method = 'flickr.photos.getSizes'			#вызов метода для получения ссылок на все размеры данного изображения

		dom = self.__DoFlickrMethod__(method, photo_id=ID)
		url_nodes = dom.getElementsByTagName("size")
		urls_id=[]	
		for el in url_nodes:
			urls_id.append(el.getAttribute("source").encode('utf-8'))
		list_tmp=list()		
		list_tmp=urls_id[0].split(".")
		return urls_id , list_tmp[-1]			 			#возвращаем список со всеми ссылками на разрешения изображения



	def __PhotosSizesFromResolut__(self, photo_resol, urls_id):		#в функцию передается список ссылок для фотографии и требуемое разрешение
		if photo_resol==0:		 				#если стоит разрешение по умолчанию, то берем максимальное
			return urls_id[len(urls_id)-1] , str(len(urls_id))   	#возвращаем ссылку и номер выбранного разрешения
		elif len(urls_id)<photo_resol:					#выбрасываем исключение если запрашиваемого разрешения нет

			raise Exception("No such resolution!")
		return urls_id[photo_resol-1], str(photo_resol)  		#возвращаем ссылку (на запрошенное разрешение) и номер разрешения



	def __ConstructFS__(self):
		self.FS['Tags'] = dict() 
		t = self.FS['Tags']
		for i in self.Tags:
			t[i.title] = dict()		
		
		self.FS['Sets'] = dict()
		s = self.FS['Sets']
		for i in self.PhotoSets:
			s[i.title] = dict()

		self.FS['Upload'] = dict()

		self.FS['Resolutions'] = dict()	

		#для каждой папки разрешения формируем свой словарь
		resDictionarySq = dict ()
		resDictionaryTh = dict ()
		resDictionarySm = dict ()
		resDictionaryMe5 = dict ()
		resDictionaryMe6 = dict ()
		resDictionaryLar = dict ()


		for i in self.Photos.keys():
			#изображение попадает или не попадает в словарь, в зависимости от того, солько разрешений содержится для него в списке self.PhotosURL
			for r in range(0,len(self.PhotosURL.get(i))):
				if r==0:
					resDictionarySq[self.Photos[i].title + '['+str(i)+'].'+self.PhotosType[i]] = self.Photos[i]  #имя изображения формируется из title и id
				if r==1:
					resDictionaryTh[self.Photos[i].title + '['+str(i)+'].'+self.PhotosType[i]] = self.Photos[i]  #имя изображения формируется из title и id
				if r==2:
					resDictionarySm[self.Photos[i].title + '['+str(i)+'].'+self.PhotosType[i]] = self.Photos[i]  #имя изображения формируется из title и id
				if r==3:
					resDictionaryMe5[self.Photos[i].title + '['+str(i)+'].'+self.PhotosType[i]] = self.Photos[i]  #имя изображения формируется из title и id
				if r==4:
					resDictionaryMe6[self.Photos[i].title + '['+str(i)+'].'+self.PhotosType[i]] = self.Photos[i]  #имя изображения формируется из title и id
				if r==5:
					resDictionaryLar[self.Photos[i].title + '['+str(i)+'].'+self.PhotosType[i]] = self.Photos[i]  #имя изображения формируется из title и id

		(self.FS['Resolutions'])['Square'] = resDictionarySq
		(self.FS['Resolutions'])['Thumbnail'] = resDictionaryTh
		(self.FS['Resolutions'])['Small'] = resDictionarySm
		(self.FS['Resolutions'])['Medium 500'] = resDictionaryMe5
		(self.FS['Resolutions'])['Medium 640'] = resDictionaryMe6
		(self.FS['Resolutions'])['Large'] = resDictionaryLar


		for i in self.Photos.keys():
			photoTitle = self.Photos[i].title + '['+str(i)+'].'+self.PhotosType[i]		#имя изображения формируется из title и id
			photoObj = self.Photos[i]

			if photoObj.tags == []:
				t[photoTitle] = photoObj
			else:
				for iT in photoObj.tags:
					if(t.get(str(iT), -1)==-1): print "Tag error! ",iT
					else: (t[str(iT)])[photoTitle] = photoObj

			if self.Photos[i].sets == []:
				s[photoTitle] = self.Photos[i]
			else:
				for iS in photoObj.sets:
					if(s.get(str(iS), -1)==-1): print "Set error! ", iS
					else: (s[str(iS)])[photoTitle] = photoObj
		pass



	def __PrintFSToLog__(self, Folder, j):
		for i in Folder.keys():
			if type(Folder[i]) == type(dict()):
				self.__ToLog__(str("		"*j + "-" + i))				
			else:
				self.__ToLog__(str("		"*j + "-" + Folder[i]))




	def __UpdateFS__(self):
		self.__ToLog__("__UpdateFS__: ")

		self.FS = dict()	#Файловая система

		self.Photos = dict()	#Множество всех фотографий
		self.UploadPhotos = list()	#Множество всех фотографий
		self.Tags = list()	#Множество всех тегов
		self.PhotoSets = list()	#Множество всех сетов


		self.__GetTags__()
		self.__GetPhotos__()

		self.__GetPhotoSets__()
		self.__ScanPhotoSetsForPhotos__()
		
		self.__ConstructFS__()
		self.__ToLog__("__UpdateFS__: FINISHED")



	def __UploadNewV__(self):
		while (True):			
			time.sleep(2)
			self.UThread = 1

			#self.__ToLog__("		UploadMonitor is active.")
			if len(self.UploadQ)>0:
				count = 0
				#self.__ToLog__("		UpdateIsInProgress = True")
				self.UpdateIsInProgress = False

				#self.__ToLog__("		Upload is !!!")
				while len(self.UploadQ)>0:
					i = self.UploadQ.popleft()
					self.__ToLog__("		UploadingPhoto:  " + str(i))
					try:
						result = self.flickr.upload(filename=str(i), is_public=u'1', is_family=u'1', is_friend=u'1')
						photo_id = result.find('photoid').text
					except Exception as ex:
						self.__ToLog__("	"+str(ex))

					if (photo_id != ''):
						#self.__ToLog__("		UploadPhoto: OK " + i)
						count=count+1
						pass
					time.sleep(0.5)	
				
				try:
					#self.__ToLog__("		UpdateIsInProgress = True")
					#self.UpdateIsInProgress = True

					self.__UpdateFS__()
	
				except Exception as ex:
					self.UpdateIsInProgress = False
					
				self.UpdateIsInProgress = False
				#self.__ToLog__("		UpdateIsInProgress = False")
				self.__ToLog__("		UploadPhoto: FINISHED, "+str(count))


	def __GetDataImage__(self, t, url, el, r):					#получаем изображение из кэша, либо загружаем с flickr
		tfile=os.path.join(self.cachedir, str(r) ,str(t)+'['+str(el)+']') 	#получаем путь к изображению в кешэ исходя из запрашиваемого разрешения, имени файла и его id
		try:
			fr = open (tfile, 'r')
		except IOError as ex:							#если изображения в кэше нет, то загружаем с flickr
			data = urlopen(str(url)).read()	
			self.__ToLog__("read: Read from flickr")		
			try:
				fw = open (tfile, 'w')					#пишем результат в кэш
			except IOError as ex:
				self.__ToLog__("read: Write to cash error: " + str(ex.args[0]))
			else:
				fw.write(data)
				fw.close()
				self.__ToLog__("read: Write to cash succes")
		else:
			data = fr.read()						#если изображение есть в кэше , то читаем оттуда
			fr.close()
			self.__ToLog__("read: Read from cash")
		return data



	def __UploadPhoto__(self, path):

		self.__ToLog__("		UploadPhoto Started Thread: " + path)
		result = self.flickr.upload(filename=path, is_public=u'1', is_family=u'1', is_friend=u'1')
		photo_id = result.find('photoid').text
		if (photo_id != ''):
			self.__ToLog__("		UploadPhoto: OK " + photo_id)
			#self.__ToLog__("		UpdateIsInProgress = True")
			#self.UpdateIsInProgress = False #Пока не будем использовать запрет обращения при обновлении
			try:
				self.__UpdateFS__()	
			except Exception as ex:
				#self.UpdateIsInProgress = False
				pass

		#self.__ToLog__("		UpdateIsInProgress = False")
		#self.UpdateIsInProgress = False

		
	
	#------------------------------ИНТЕРФЕЙС FUSE

	def getattr(self, path):	# получение информации об объекте через fuse.Stat()

		if (self.UpdateIsInProgress):
			self.__ToLog__("Access denied while update.")
			return -errno.ENOENT

		if (self.UThread == 0):
			try:			
				threading.Thread(target = self.__UploadNewV__).start()

			except Exception as errtxt:
				self.__ToLog__("	"+str(errtxt))

			self.UThread = 1
			self.__ToLog__("Thread started.")
	

		#self.__ToLog__("getattr: path = " + path)
		st = fuse.Stat()
		st.st_mode = stat.S_IFDIR | 0755
		st.st_ino = 0
		st.st_dev = 0
		st.st_nlink = 2
		st.st_uid = 0
		st.st_gid = 0
		st.st_size = 0

		st.st_atime = int(time.time())
		st.st_mtime = st.st_atime
		st.st_ctime = st.st_atime

		t = self.FS
		pr=0
		r=0
		for i in path[1:].split('/'):
			if (i!='' and t!=-1):
				t = t.get(i, -1)
			if pr==0 and i=='Resolutions':	#если встречаем в пути Resolutions
				pr=1
			if pr==1:			#если встречаем в пути после Resolutins папку с разрешением
				if i=='Large':
					r=6
				if i=='Medium 640':
					r=5
				if i=='Medium 500':
					r=4
				if i=='Small':
					r=3
				if i=='Thumbnail':
					r=2
				if i=='Square':
					r=1
	

		if path.find("/Upload/")!=-1 and path.find("/.")==-1 and len(path)>8:
			if t!=(-1):
				st.st_mode = stat.S_IFREG | 0666
				st.st_nlink = 1
				st.st_size = t.length
				return st
			else:
				fPath = str(path)
				fName = fPath.split("/")[2]
				newPhoto = Photo(fName)
				(self.FS['Upload'])[fName] = newPhoto
				newPhoto.title = fName

				st.st_mode = stat.S_IFREG | 0666
				st.st_nlink = 1
				st.st_size = 0
				self.__ToLog__("	/upload/ new photo: " + path + " size: " +  str(st.st_size))
				return st
								
		if t!=-1:
			if type(t) == type(dict()):
				st.st_mode = stat.S_IFDIR | 0755
				st.st_nlink = 3
				#self.__ToLog__("	folder")
				return st
			
			else:
				st.st_mode = stat.S_IFREG | 0444
				st.st_nlink = 1
				for el in self.Photos.keys():
					if self.Photos.get(el)==t:
						try:
							(url,r) = self.__PhotosSizesFromResolut__(r,self.PhotosURL.get(el)) #получаем ссылку на искомое разрешение (по умолчанию r=0 - максимальное разрешение)
						except Exception as ex:
							#self.__ToLog__("getattr: return ENOENT" + str(ex.args[0]))		
							return -errno.ENOENT
						fileURL = urlopen(url)
						stOfFile = fileURL.info().get('Content-Length')
						if stOfFile is None:
							sizeOfFile = 0
						else:
							sizeOfFile = int(stOfFile)
				st.st_size = sizeOfFile
				#self.__ToLog__("	file")
				return st

		#self.__ToLog__("	no entry")		
		return -errno.ENOENT



	def statfs(self): #запрос информации о ФС

		self.__ToLog__("statfs:")
		st = fuse.StatVfs()
		# Размер блока
		st.f_bsize = self.block_size
		st.f_bfree = 1024
		st.f_bavail = 1024
		st.f_frsize = 1024
		# Количество блоков
		st.f_blocks = self.block_count
		# Количество файлов
		st.f_files = self.Photos.keys().count()
		return st



	def readdir(self, path, offset):# просмотр содержимого каталога.
			self.__ToLog__("readdir: path = " + str(path) + " offset = " + str(offset))
													
			dirents = ['.', '..']

			if (self.UpdateIsInProgress):
				self.__ToLog__("Access denied while update.")
				
			else:
				t = self.FS
				strPath = str(path)

				if strPath=='/':
					dirents.extend(t.keys())

				else:
					for i in strPath.split('/'):
						if (i!=''):
							t = t.get(i, -1)
	
					if (t!=-1):
						#self.__ToLog__("readdir: " + str(t))
						if type(t) == type(dict()):
							dirents.extend(t.keys())
			for i in dirents:
				#self.__ToLog__("	" + i)
				yield fuse.Direntry(i)
	  


	#------------------------------------------FUSE FILE OPERATIONS

	def open(self, path, flags):
		if (self.UpdateIsInProgress):
			self.__ToLog__("Access denied while update.")
			return -errno.ENOENT

		self.__ToLog__("open:"+ " path = " + str(path)+ " flags =" + str(flags))

		if path.find("/Upload/")!=-1 and path.find("/.")==-1 and len(path)>8:
			self.__ToLog__("	/Upload/")
			return True

		check=0
		t = self.FS
		for i in path[1:].split('/'):
			if (i!=''):
				t = t.get(i, -1)
		if (t!=-1):
			if type(t) != type(dict()):
				for el in self.Photos.keys():
					if self.Photos.get(el)==t:
						check=1
		if check!=1:
			self.__ToLog__("	ENOENT")
			return -errno.ENOENT
		else:
			return True



	def read(self, path, length, offset, fh=None):
		if (self.UpdateIsInProgress):
			self.__ToLog__("Access denied while update.")
			return -errno.ENOENT

		self.__ToLog__("read: "+ "path = " + str(path)+ " length = " + str(length)+ " offset = " + str(offset))

		if path.find("/Upload/")!=-1 and len(path)>8:
			fPath = str(path)
			fName = fPath.split("/")[2]
			t = (self.FS['Upload'])[fName]
			retVal = t.read(length, offset)
			self.__ToLog__("	/Upload/: " + str(len(retVal)))		
			return retVal

		pr=0
		r=0
		t = self.FS
		check=0
		for i in path[1:].split('/'):
			if (i!=''):
				t = t.get(i, -1)
			if pr==0 and i=='Resolutions':	#если встречаем в пути Resolutions
				pr=1
			if pr==1:			#если встречаем в пути после Resolutins папку с разрешением
				if i=='Large':
					r=6
				if i=='Medium 640':
					r=5
				if i=='Medium 500':
					r=4
				if i=='Small':
					r=3
				if i=='Thumbnail':
					r=2
				if i=='Square':
					r=1
		if (t!=-1):
			if type(t) != type(dict()):
				for el in self.Photos.keys():
					if self.Photos.get(el)==t:

						check=1
						try:
							(url,r) = self.__PhotosSizesFromResolut__(r,self.PhotosURL.get(el))	#получаем ссылку на разрешение (по умолчанию запрашивается максимальное разрешение r=0) и номер разрешения которое получили в итоге

						except Exception as ex:
							self.__ToLog__("read: return ENOENT" + str(ex.args[0]))		
							return -errno.ENOENT
						self.__ToLog__(str(url))
						data = self.__GetDataImage__(t, url, el, r)				
						slen = len(data)
						if offset < slen:
							if offset + length > slen:
								length = slen - offset
							buf = data[offset:offset+length]
						else:
							buf=''	

		if check!=1:
		#Ошибка чтения
			self.__ToLog__("	ENOENT")	
			return -errno.ENOENT
		self.__ToLog__("	" + str(len(buf)))		
		return buf



	def write(self, path, buf, offset, fh=None):
		if (self.UpdateIsInProgress):
			self.__ToLog__("Access denied while update.")
			return -errno.EACCES
			

		self.__ToLog__("write: path = " + str(path)+ " offset =" + str(offset) + " buf =" + str(len(buf)))

		if path.find("/Upload/")!=-1 and path.find("/.")==-1 and len(path)>8:
			t = self.FS
			strPath = str(path)
			for i in strPath.split('/'):
				if (i!=''):
					t = t.get(i, -1)
			if t!=-1:
				if type(t)==type(Photo(-1)):
					retVal = t.write(buf, offset)					

					if (len(buf)<self.block_size*self.block_count):

						path = self.currentDirectory +"/"+sys.argv[1]+path

						self.__ToLog__("		UploadPhoto: " + path)

						self.UploadQ.append(str(path))


					self.__ToLog__("	" + str(retVal))

					return retVal
		self.__ToLog__("	EACCES")
		return -errno.EACCES

	def unlink(self, path):
		pass
#---------------------------------------------------------------------------------------------------EX


	def access(self, path, amode):
		self.__ToLog__("	~access path="+path)
		return 0
	    
	def chmod(self, path, mode):
		self.__ToLog__("	~chmod path="+path)
	    
	def chown(self, path, uid, gid):
		self.__ToLog__("	~chown path="+path)
		raise FuseOSError(EROFS)
	    
	def create(self, path, mode, fi=None):
		self.__ToLog__("	~create path="+path)		
		raise FuseOSError(EROFS)
	    
	def destroy(self, path):
		self.__ToLog__("	~destroy path="+path)	
		pass
	    
	def flush(self, path, fh):
		self.__ToLog__("	~flush path="+path)	
		return 0
	    
	def fsync(self, path, datasync, fh):
		self.__ToLog__("	~fsync path="+path)
		return 0
	    
	def fsyncdir(self, path, datasync, fh):
		self.__ToLog__("	~fsyncdir path="+path)
		return 0
	
	def link(self, target, source):
		self.__ToLog__("	~link target="+target)
		raise FuseOSError(EROFS)
	    
	def mkdir(self, path, mode):
		self.__ToLog__("	~path path="+path)
		raise FuseOSError(EROFS)
	    
	def mknod(self, path, mode, dev):
		self.__ToLog__("	~mknod path="+path)
		raise FuseOSError(EROFS)
	    

	def rename(self, old, new):
		self.__ToLog__("	~rename path="+old)
		raise FuseOSError(EROFS)
	    
	def rmdir(self, path):
		self.__ToLog__("	~rmdir path="+path)
		raise FuseOSError(EROFS)
	    
	def truncate(self, path, length, fh=None):
		self.__ToLog__("	~truncate path="+path)
		if (self.UpdateIsInProgress):
			self.__ToLog__("Access denied while update.")
			return -errno.EACCES
		
		if path.find("/Upload/")!=-1 and path.find("/.")==-1 and len(path)>8:
			t = self.FS
			strPath = str(path)
			for i in strPath.split('/'):
				if (i!=''):
					t = t.get(i, -1)
			if t!=-1:
				if type(t)==type(Photo(-1)):
					t.truncate(length)
					return 0

		return -errno.EACCES
	    

#--------------------------------------------------MAIN
if __name__ == '__main__':
	sUsage='FileSystem ' + fuse.Fuse.fusage
	FS = FileSystem(version="%prog " + fuse.__version__, usage=sUsage, dash_s_do='setsingle', )
	FS.parse(errex=1)
	FS.main()





