from base64 import b64decode
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
from os import chdir, listdir, makedirs, rmdir
from os import unlink
from os.path import getsize as path_isfile
from os.path import isfile as path_isfile
from os.path import join as path_join
from socket import socket
from ssl import wrap_socket
from threading import Lock as ThreadLock
from urllib import parse

import time

t1=time.time()


class download_manager(object):
    def __init__(self, url, save_file):

        self.request_headers = "GET {url} HTTP/1.1\r\nHost: {host}\r\nConnection: {connection_mode}\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36\r\nAccept: *\r\n{extra}\r\n\r\n"
        self.task_list = []
        self.pause_data = []
        self.pause = False
        self.lock = ThreadLock()
        self.BUFFERSIZE = 65535

        if url.lower().startswith("thunder://"):
            url = b64decode(url[10:])[2:-2].decode("utf-8")
        elif url.lower().startswith("Flashget://"):
            url = b64decode(url[11:].rsplit("&", 1)[0])[10:-10].decode("utf-8")
        elif url.lower().startswith("qqdl://"):
            url = b64decode(url[7:]).decode("utf-8")
                
        if url.lower().startswith("https://"):
            self.s = wrap_socket(socket())
            self.s_init = "wrap_socket(socket())"
            self.host = url.split("//", 1)[1].split("/", 1)[0]
            self.addr = (self.host, 443)
        elif url.lower().startswith("http://"):
            self.s=socket()
            self.s_init = "socket()"
            self.host = url.split("//", 1)[1].split("/", 1)[0]
            self.addr = (self.host, 80)
        elif url.lower().startswith("ftp://"):
            url=""

        self.url = url
        self.file_url = "/" + url.split("//", 1)[1].split("/", 1)[1]
        if not save_file:
            save_file = parse.unquote(url.rsplit("/", 1)[1])
        self.save_file=save_file

    def run(self):
        self.s.connect(self.addr)
        self.s.send(self.request_headers.format(**{"url": self.file_url ,"host": self.host,"connection_mode": "close","extra": ""}).encode("utf-8"))
        self.data = self.s.recv(100)
        while True:
            if b"\r\n\r\n" in self.data:
                self.data = self.data.split(b"\r\n\r\n")[0]
                break
            self.data += self.s.recv(100)
        self.s.close()
        self.data=self.data.decode("utf-8")
        if "HTTP/1.1 200 OK" in self.data:
            if "Content-Length:" in self.data:
                length = eval(
                    self.data.split("Content-Length:")[1].split("\r\n", 1)[0])
                if length < 20971520:  #20Mb
                    max_workers = 1
                else:
                    if length < 83886080:  #80Mb
                        max_workers = 4
                    elif length > 1048576000:  #1Gb
                        max_workers = 32
                    elif length > 524288000:  #500Mb
                        max_workers = 16
                    else:
                        max_workers = 8
            else:
                max_workers = 1
            executor = ThreadPoolExecutor(max_workers=max_workers)
            step = length // max_workers
            makedirs(self.save_file.rsplit(".", 1)[0])
            for i in range(max_workers):
                if i == max_workers - 1:
                    self.task_list.append(executor.submit(self.download, eval(self.s_init),i,i * step, step + length % max_workers))
                else:
                    self.task_list.append(executor.submit(self.download, eval(self.s_init),i,i * step, step))
            wait(self.task_list, return_when=ALL_COMPLETED)
            download_finished = True
            for task in self.task_list:
                result = task.result()
                if not result[0]:
                    download_finished = False
                    self.pause_data.append(result[1])
            if not download_finished:
                with open(path_join(self.save_file.rsplit(".", 1)[0],self.save_file.rsplit(".", 1)[0] + ".temp"), "wb") as f:
                    f.write(str((self.url, self.save_file)) + "\r\n" + str(self.pause_data))
                return (False,(self.url, self.save_file),self.pause_data)
            else:
                with open(self.save_file, "wb") as f_all:
                    for temp_file in listdir(self.save_file.rsplit(".", 1)[0]):
                        if not (temp_file == self.save_file or temp_file == self.save_file.rsplit(".", 1)[0] + ".temp"):
                            with open(path_join(self.save_file.rsplit(".", 1)[0],temp_file), "rb") as f:
                                f_all.write(f.read())
                        unlink(path_join(self.save_file.rsplit(".", 1)[0],temp_file))
                rmdir(self.save_file.rsplit(".", 1)[0])
                print("Download Completed")
                return (True,)
        elif "HTTP/1.1 400 Bad Request" in self.data:
            return (False, "400 Bad Request")

    def download(self, tcpsocket, id=0, begin=None, length=None, recieved = 0):
        try:
            tcpsocket.connect(self.addr)
            if not ((begin is None) and (length is None)):
                tcpsocket.send(self.request_headers.format(**{"url":self.file_url ,"host":self.host,"connection_mode":"keep-alive","extra":"range: bytes=" + str(begin) + "-" + str(begin + length - 1)}).encode("utf-8"))
            else:
                tcpsocket.send(self.request_headers.format(**{"url": self.file_url ,"host": self.host,"connection_mode": "close","extra": ""}).encode("utf-8"))
            if recieved and path_isfile(self.save_file) and path_isfile(self.save_file + "_" + str(id)) == recieved:
                f = open(path_join(self.save_file.rsplit(".", 1)[0],self.save_file+ "_" + str(id)), "ab")
            else:
                f = open(path_join(self.save_file.rsplit(".", 1)[0],self.save_file+ "_" + str(id)), "wb")
            try:
                temp = tcpsocket.recv(self.BUFFERSIZE)
            except:
                raise(AssertionError)
            if b"\r\n\r\n" in temp:
                temp=temp.split(b"\r\n\r\n")[1]
            while temp:
                recieved+=len(temp)
                f.write(temp)
                if length and recieved >= length:
                    temp=temp[:length-recieved]
                    break
                assert (not self.pause)
                try:
                    temp = tcpsocket.recv(self.BUFFERSIZE)
                except:
                    raise(AssertionError)
            return (True,)
        except AssertionError:
            return (False, {"id":id,"begin": begin,"recieved": recieved,"length": length})
        finally:
            tcpsocket.close()
            f.close()


    def download_continue(self, pause_data):
        executor = ThreadPoolExecutor(max_workers=len(pause_data))
        for items in pause_data:
            self.task_list.append(executor.submit(self.download,eval(self.s_init),id=items["id"],begin=items["begin"]+items["recieved"],length=items["length"]))
        wait(self.task_list, return_when=ALL_COMPLETED)
        download_finished = True
        for task in self.task_list:
            result = task.result()
            if not result[0]:
                download_finished = False
                self.pause_data.append(result[1])
        if not download_finished:
            with open(path_join(self.save_file,self.save_file.rsplit(".", 1)[0] + ".temp"), "wb") as f:
                f.write(str((self.url, self.save_file)) + "\r\n" + str(self.pause_data))
            return (False,(self.url, self.save_file),self.pause_data)
        else:
            with open(self.save_file, "wb") as f_all:
                for temp_file in listdir(self.save_file.rsplit(".", 1)[0]):
                    if not (temp_file == self.save_file or temp_file == self.save_file.rsplit(".", 1)[0] + ".temp"):
                        with open(path_join(self.save_file.rsplit(".", 1)[0],temp_file), "rb") as f:
                            f_all.write(f.read())
                    unlink(path_join(self.save_file.rsplit(".", 1)[0],temp_file))
            rmdir(self.save_file.rsplit(".", 1)[0])
            print("Download Completed")
            return (True,)


    def download_pause(self):
        self.pause = True


if __name__ == "__main__":
    #url = input("Enter the File URL")
    #file_name = input("Enter the File Name")
    url = "thunder://QUFodHRwOi8veHVubGVpLnp1aWRheHVubGVpLmNvbS8xOTA4L+elnuebvuWxgOeJueW3peesrOWFreWtoy0xMS5tcDRaWg=="
    file_dir = r"."
    pause = False
    chdir(file_dir)
    file_name = ""
    result = download_manager(url, file_name).run()
    if not result[0]:
        if result[1]=="400 Bad Request":
            print("文件不存在")
        elif not download_manager(result[1]).download_continue(result[2])[0]:
            print("Download Failed")

    print(time.time()-t1)
