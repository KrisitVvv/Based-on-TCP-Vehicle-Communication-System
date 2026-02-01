# -*- coding: UTF-8 -*-
import sys
import time

import cv2
import struct
import socket
import numpy as np
import threading
import gc

from queue import Queue

IP_ADDRESS_BIND = '192.168.62.117'
# IP_ADDRESS_BIND = "127.0.0.1"
PORT_BIND = 30301
# PORT_BIND = 8081

IP_ADDRESS = '192.168.62.199'
# IP_ADDRESS = "127.0.0.1"
PORT = 30300
# PORT = 8080

# PACKETUNIT = 3900
PACKETUNIT = 2850
WIDTH = 640
HEIGHT = 480

NTPHEAD = 50500

def print_log(is_error: bool = False, content: str = " "):
    content = content + '\n'
    if is_error:
        sys.stderr.write(content)
    else:
        sys.stdout.write(content)


def display(end_event, data):
    # 显示图像
    cv2.imshow('Recv Video', data[...,::-1])
    if cv2.waitKey(1) == 27: # 按下ESC键盘退出
        cv2.destroyAllWindows()
        end_event.set()


def receive(sock, queue: Queue, end_event: threading.Event):
    image_total = b''
    img_packet_dict = {}
    total_size = 0
    start_time = 0.0
    while not end_event.is_set():
        try:
            data, addr = sock.recvfrom(PACKETUNIT)
        except Exception:
            print_log(content='Recv timeout')
            raise IOError
        else:
            fhead_size = struct.unpack('i', data[:4])[0]
            count = struct.unpack('i', data[4:8])[0]
            recv_time = struct.unpack('d',data[8:16])[0]
            img_packet = data[16:]
            img_packet_dict[count] = img_packet
            if count == 1:
                start_time += recv_time
            recvd_size = len(img_packet)
            total_size += recvd_size
            now_time = time.time()
            print_log(content=f'Fhead:{fhead_size}, Count:{count}, ' 
                              f'PackageDelay:{now_time-recv_time}, Recv:{recvd_size}, SumRecv:{total_size}')
            # count 为 表示收到最后一个包，发送方包从1开始计数， 计数0表示最后一个包
            if count == 0:
                # 没有丢包， 将数据包重组为图片，放进展示队列
                if total_size == fhead_size:
                    end_packet = img_packet_dict[count]
                    del img_packet_dict[count]
                    for i in sorted(img_packet_dict):
                        image_total += img_packet_dict[i]
                    image_total += end_packet
                    nparr = np.frombuffer(image_total, np.uint8)
                    img_decode = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    now_time = time.time()
                    # cv2.putText(img_decode, "Delay: " + str(now_time - start_time)[0:5], (5, 50),
                    #             cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)

                    print_log(content='Add a new frame')
                    queue.put(img_decode)
                    image_total = b''
                    img_packet_dict.clear()
                    total_size = 0
                    gc.collect()


                    print("The last Delay: ",now_time-start_time)
                    start_time = 0
                else:  # 说明有丢包，丢弃前面接收的所有数据包，该图片包不完整
                    image_total = b''
                    img_packet_dict.clear()
                    total_size = 0
                    now_time = 0


def display_thread_wrapper(queue: Queue, end_event: threading.Event, wait_timeout: int, total_timeout: int):
    total_wait_time = 0
    cv2.namedWindow('Recv Video', cv2.WINDOW_AUTOSIZE)
    wait_img = cv2.imread("waitImg.png")
    wait_bg = cv2.resize(wait_img, (WIDTH,HEIGHT))
    while not end_event.is_set():
        if total_wait_time >= total_timeout:
            print_log(is_error=True, content='Display wait timeout, quit!')
            break
        try:
            data = queue.get(block=True, timeout=wait_timeout)
        except Exception:
            print_log(content='No data in display queue\n')
            display(end_event, wait_bg)
            total_wait_time += wait_timeout
        else:
            # display
            display(end_event, data)
            total_wait_time = 0
    print_log(content='Display thread quit')


def receive_thread_wrapper(queue: Queue, end_event: threading.Event, timeout: int, total_timeout: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP_ADDRESS_BIND, PORT_BIND))

    #-------------NTP-Begin------------#
    count = 0
    while count < 100:
        try:
            data, addr = sock.recvfrom(28)
            time_2 = time.time()
        except Exception:
            print('Recv timeout')
            raise IOError
        else:
            
            time_1 = struct.unpack('d', data[4:12])[0]
            time_3 = time.time()
            send_data = struct.pack('i',NTPHEAD) + struct.pack('d', time_1) + struct.pack('d', time_2) + struct.pack('d', time_3)
            sock.sendto(send_data, (IP_ADDRESS, PORT))
            count += 1
    #-------------NTP--End-------------#

    sock.settimeout(timeout)
    print("Bind Up on 30301")
    print('Start Receiving ...')

    total_wait_time = 0
    while not end_event.is_set():
        if total_wait_time >= total_timeout:
            print_log(is_error=True, content='Receive wait timeout, quit!')
            break
        try:
            receive(sock, queue, end_event)
        except IOError:
            total_wait_time += timeout
        else:
            total_wait_time = 0

    sock.close()
    print_log(content='Receive thread quit')


def main_thread(ip: str,port: int):
    global IP_ADDRESS_BIND
    global PORT_BIND
    IP_ADDRESS_BIND = ip
    PORT_BIND = port

    timeout = 1  # 阻塞线程秒数
    max_wait_time = 100
    kill_event = threading.Event()
    display_queue = Queue()
    display_thread = threading.Thread(target=display_thread_wrapper,
                                      args=(display_queue, kill_event, timeout, timeout * max_wait_time))
    receive_thread = threading.Thread(target=receive_thread_wrapper,
                                      args=(display_queue, kill_event, timeout, timeout * max_wait_time))

    receive_thread.start()
    display_thread.start()

    if cv2.waitKey(1) == 27:
        cv2.destroyAllWindows()
        kill_event.set()

    display_thread.join()
    receive_thread.join()

if __name__ == '__main__':
    main_thread(IP_ADDRESS_BIND,PORT_BIND)
