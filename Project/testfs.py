#! /usr/bin/python
# -*- coding: utf-8 -*-


#Стратегия разработки драйвера проста - необходимо реализовать некоторый набор функций с определенными прототипами, указатели на которых передать модулю ядра (с помощью вызова некоторой функции - т.к. fuse_main) - после чего при обращении к ФС будут вызываться именно те функции из драйвера, указатели на которые были переданы в fuse_main. 

#Для установки библиотек fuse выполняем sudo apt-get install python-fuse
#В процессе установки видим, что устанавливается версия пакета 2:0.2.1-5, где 0.2 - это версия fuse-python

#Первым делом мы импортируем нужные модули:
import os,stat
import fuse, sys
import flickr_v2
import sys
#Теперь необходимо сообщить fuse-python какую ее версию мы используем:
fuse.fuse_python_api = (0, 2)


#Теперь давайте определимся с тем, что будет представлять из себя наша ФС:
#    2 каталога - '/' и '/simple' - оба с правами 0555 и root.root в качестве пользователя.группы_пользователя
#    1 файл - '/README' (0444 root.root)

#Описываем базовый для нашего драйвера класс (он будет наследовать класс fuse.Fuse):
class simpleFS(fuse.Fuse):

  #конструктор класса simpleFS

  def __init__(self, *args, **kw):
    #вызов конструктора базового класса fuse.Fuse со всеми переданными в конструктор simpleFS аргументами (а self.README - содержимое файла '/README'):
    fuse.Fuse.__init__(self, *args, **kw)
    self.README = 'This is simple FS\n'
  #Пользовательские действия с ФС (системные вызовы и прочее):

  # getattr вызывается при получении информации об объекте ФС. Например, при использовании команды ls
  def getattr(self, path):
    # В объекте fuse.Stat() вернем интересующую информацию
    st = fuse.Stat()
    # "Режим" - права доступа, тип объекта
    st.st_mode = 0
    # Номер inode
    st.st_ino = 0
    st.st_dev = 0
    # Количество ссылок на объект
    st.st_nlink = 0
    # ID владельца объекта
    st.st_uid = 0
    # ID группы владельца объекта
    st.st_gid = 0
    # Размер объекта
    st.st_size = 0
    # Временные штампы
    st.st_atime = 0
    st.st_mtime = 0
    st.st_ctime = 0
    if path == '/' or path == '/tags' or path == '/sets' or path == '/resolution':
      # Каталоги
      st.st_mode = stat.S_IFDIR | 0755
      st.st_nlink = 3
    elif path == '/config.txt':
      # Файлы
      st.st_mode = stat.S_IFREG | 0444
      st.st_nlink = 1
      st.st_size = len(self.README)
    elif path=='/resolution/Square' or path=='/resolution/Thumbnail' or path=='/resolution/Small' or path=='/resolution/Medium 500' or path=='/resolution/Medium 640' or path=='/resolution/Large':
      st.st_mode = stat.S_IFDIR | 0755
      st.st_nlink = 3      
    else:
      ch=0
      if s.set_name!=[]:
        for el_set in s.set_name:
          if path=='/sets/'+el_set:
            st.st_mode = stat.S_IFDIR | 0755
            st.st_nlink = 3
            ch=1
      if tags_list!=[]:
        for el_photo in tags_list:
          if el_photo!=[]:
            path_tags='/tags/'
            for el_tag in el_photo:
              if path==path_tags+el_tag:
                st.st_mode = stat.S_IFDIR | 0755
                st.st_nlink = 3
                ch=1
              path_tags=path_tags+el_tag+'/'   
      if ch==0:    
        return -errno.ENOENT
    return st

  # readdir вызывается при попытке просмотра содержимого каталога. Например, при использовании ls
  def readdir(self, path, offset):
    # В каждом каталоге есть '.' и '..'
    yield fuse.Direntry('.')
    yield fuse.Direntry('..')
    if path == '/':
      # Кроме того, в '/' есть еще и 'README' и 'simple'
      yield fuse.Direntry('config.txt')
      yield fuse.Direntry('tags')
      yield fuse.Direntry('resolution')
      yield fuse.Direntry('sets')
    elif path=='/sets':
      if s.set_name!=[]:
        for el_set in s.set_name:
          yield fuse.Direntry(el_set)
    elif path=='/resolution':
      yield fuse.Direntry('Square')
      yield fuse.Direntry('Thumbnail')
      yield fuse.Direntry('Small')
      yield fuse.Direntry('Medium 500')
      yield fuse.Direntry('Medium 640')
      yield fuse.Direntry('Large')
    else:    
      if tags_list!=[]:  
        ch_photo=0  #!!!!!
        for el_photo in tags_list:
          if el_photo!=[]:
            path_tags='/tags/'
            ch=0
            if path=='/tags':
              yield fuse.Direntry(el_photo[0])
            else:
              for el_tag in el_photo:
                if path==path_tags+el_tag:
                  if el_photo[len(el_photo)-1]!=el_photo[ch]:
                    yield fuse.Direntry(el_photo[ch+1])
                  #else: !!!!!!!!!!!!!!!
                    #yield fuse.Direntry(ids_list[ch_photo])!!!!!!!!!!!!!!
                path_tags=path_tags+el_tag+'/'
                ch=ch+1 
          ch_photo=ch_photo+1  #!!!!           
                 

  # open вызывается при попытки открыть файл. Мы должны проверить флаги доступа - наш единственный файл '/README' доступен только на чтение
  def open(self, path, flags):
    #if path != '/config.txt':
    #  return -errno.ENOENT
    accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
    if (flags & accmode) != os.O_RDONLY:
      # Ошибка доступа
      return -errno.EACCES

  # read вызывается при попытки прочитать данные из файла
  # offset - смещение в читаемом файле
  # size - размер считываемого ("запрощенного") блока
  # read возвращает считанные символы
  def read(self, path, size, offset):
    #!!!!!!!!!!!url = s.getPhotosSizesFromIds(!!!)
    if path != '/config.txt':
      return -errno.ENOENT
    slen = len(self.README)
    if offset < slen:
      if offset + size > slen:
        size = slen - offset
      buf = self.README[offset:offset+size]
    else:
      buf = ''
    return buf

  # statfs вызывается в ответ на запрос информации о ФС
  def statfs(self):
    # Вернем информацию в объекте класса fuse.StatVfs
    st = fuse.StatVfs()
    # Размер блока
    st.f_bsize = 1024
    st.f_frsize = 1024
    st.f_bfree = 0
    st.f_bavail = 0
    # Количество файлов
    st.f_files = 5
    # Количество блоков
    # Если f_blocks == 0, то 'df' не включит ФС в свой список - понадобится сделать 'df -a'
    st.f_blocks = 4
    st.f_ffree = 0
    st.f_favail = 0
    st.f_namelen = 255
    return st



#Описываем функцию, которая будет "запускать" наш драйвер:
def runSimpleFS():
  usage='Simple FS ' + fuse.Fuse.fusage
  #Вызов конструктора класса fuse.Fuse (с правильным списком аргументов)
  fs = simpleFS(version="%prog " + fuse.__version__,usage=usage,dash_s_do='setsingle')
  fs.parse(errex=1)
  #Вызов той самой fuse_main
  fs.main()

#Вызов запуска драйвера
s = flickr_v2.FlickrAPI()
s.getPhotosNotInSetsIds()
s.getPhotosNotInSetsNamesAndTags()
s.getSets()
s.getPhotosFromSetsIds()
s.getPhotosFromSetsNamesAndTags()

tags_list=[]
tags_list=s.photo_tags
for el_set in s.photo_in_sets_tags:
  tags_list=tags_list+el_set
print tags_list

ids_list=[]
ids_list=s.photo_id
for el_set in s.photo_in_sets_id:
  ids_list=ids_list+el_set
print ids_list


runSimpleFS()

#Для запуска данной программы необходимо создать дирректорию, которая будет представлять собой файловую систему с любым именем (допустим smpfs):
# mkdir smpfs
#Затем запустить саму программу с полным именем дирректории smpfs в качестве аргумента(в данном случае программа лежит в той же дирректории, что и smpfs):
# python testfs.py smpfs
#В итоге получаем в папке smpfs файловую систему. Данная папка даже отображается в проводнике в меню слева как отдельная ФС. В ней содержатся два каталога и файл README. 

