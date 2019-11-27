import asyncio
import socket
import ssl
import threading
import time

t1=time.time()

request_headers = "GET {url} HTTP/1.1\r\nHost: {host}\r\nConnection: {connection_mode}\r\nUser-Agent: curl/7.55.1\r\nAccept: *\r\n{extra}\r\n\r\n"
data_recv={}
pause = False

async def download(socket, url, addr, host, id=0, begin=None, length=None):
    socket.connect(addr)
    if not ((begin is None) and (length is None)):
        socket.send(request_headers.format(**{"url":url,"host": host, "connection_mode": "keep-alive", "extra": "range: bytes=" + str(begin) + "-" + str(begin+length-1)}).encode("utf-8"))
    else:
        socket.send(request_headers.format(**{"url":url,"host": host, "connection_mode": "close", "extra": ""}).encode("utf-8"))
    data_recv_temp = b""
    while True:
        temp = socket.recv(65535)
        if not temp:
            break
        data_recv_temp += temp
        if b"\r\n\r\n" in data_recv_temp:
            if length and len(data_recv_temp.split(b"\r\n\r\n")[1])>=length:
                break
    socket.close()
    data_recv[id]=data_recv_temp.split(b"\r\n\r\n")[1][:length]

def download_main(url, save_file):
    if not save_file:
        save_file =url.rsplit("/",1)[1]
    host = url.split("//",1)[1].split("/",1)[0]
    if url.startswith("http://"):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_init = "socket.socket(socket.AF_INET, socket.SOCK_STREAM)"
        addr=(host,80)
    elif url.startswith("https://"):
        s = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        s_init = "ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))"
        addr=(host,443)
    elif url.startswith("ftp://"):
        pass
    s.connect(addr)
    s.send(request_headers.format(**{"url":url,"host": host, "connection_mode": "close", "extra": ""}).encode("utf-8"))
    data = s.recv(10).decode("utf-8")
    while True:
        if "\r\n\r\n" in data:
            data=data.split("\r\n\r\n")[0]
            break
        data += s.recv(10).decode("utf-8")
    s.close()
    if "HTTP/1.1 200 OK" in data:
        if "Content-Length:" in data:
            length = eval(data.split("Content-Length:")[1].split("\r\n", 1)[0])
            if length < 83886080:  #80Mb
                max_workers=4
            elif length > 524288000:#500Mb
                max_workers=16
            else:
                max_workers = 8
            step = length // max_workers
            task_list = []
            for i in range(max_workers):
                if i == max_workers - 1:
                    task_list.append(download(eval(s_init), url, addr, host, i, i * step, step + length % max_workers))
                else:
                    task_list.append(download(eval(s_init), url, addr, host, i, i * step,step))
            asyncio.get_event_loop().run_until_complete(asyncio.wait(task_list))
        else:
            download(eval(s_init), url, save_file, addr, host)
        with open(save_file, "wb") as f:
            f.write(b"".join([data_recv[k] for k in sorted(data_recv)]))
        print("Download Completed")

if __name__ == "__main__":
    #url = input("Enter the File URL")
    #file_name = input("Enter the File Name")
    url="https://www.baidu.com/img/baidu_jgylogo3.gif"
    file_name=""
    download_main(url, file_name)
    print(time.time()-t1)
