# -*- coding: UTF-8 -*-
import socket
import time
import sys
import cv2
import numpy as np
import struct
import threading

# import pyrealsense2 as rs
from anomaly_detect_api import anomaly_detect

# UDP相关配置
UDP_IP_ADDRESS = '192.168.20.199'
# UDP_IP_ADDRESS = "127.0.0.1"
UDP_PORT = 30300
# UDP_PORT = 8081

# TCP相关配置
TCP_SERVER_IP = '10.204.9.213'  # TCP服务器IP地址，需要修改为实际接收端IP
TCP_PORT = 8888  # TCP传输端口

# PACKET_UNIT = 3884
PACKET_UNIT = 2834
WIDTH = 1280
HEIGHT = 720
FPS = 30

NTPHEAD = 50500

global delay
global expTime

delay = 0
expTime = 0

global frame_image
global display_image

tcp_socket = None
tcp_connected = False

import threading

sent_pedestrian_ids = set()
id_lock = threading.Lock()  # 用于保护sent_pedestrian_ids的线程锁


def tcp_send_message(message):
    """
    通过TCP发送文本消息
    :param message: 要发送的文本消息
    """
    global tcp_socket, tcp_connected
    
    try:
        # 编码消息为字节
        message_bytes = message.encode('utf-8')
        
        # 使用特殊标识表示这是文本消息（例如，使用负数表示）
        size = len(message_bytes)
        size_bytes = struct.pack('!I', size | (1 << 31))  # 最高位设为1表示文本消息
        
        if tcp_socket and tcp_connected:
            tcp_socket.sendall(size_bytes)
            tcp_socket.sendall(message_bytes)
            print(f"消息已发送: {message}")
        else:
            print("TCP server not connected for message, attempting to connect...")
            # 尝试连接到服务器
            try:
                tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcp_socket.connect((TCP_SERVER_IP, TCP_PORT))
                tcp_connected = True
                print(f"Connected to TCP server {TCP_SERVER_IP}:{TCP_PORT}")
                
                # 发送数据
                tcp_socket.sendall(size_bytes)
                tcp_socket.sendall(message_bytes)
                print(f"消息已发送: {message}")
            except Exception as e:
                print(f"Failed to connect to TCP server for message: {e}")
                tcp_connected = False
                if tcp_socket:
                    tcp_socket.close()
                    tcp_socket = None
    except Exception as e:
        print(f"Error in tcp_send_message: {e}")
        tcp_connected = False
        if tcp_socket:
            tcp_socket.close()
            tcp_socket = None

def udp_send(image, socket_process):
    """
    :param image: 要发送的图片数据
    :param socket_process: socket连接
    :return:
    """
    encoded_image = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 10])[1].tobytes()
    # 将图像分包传输到指定的 IP 地址和端口号
    data_length = len(encoded_image)

    packets = [encoded_image[i: i + PACKET_UNIT] for i in range(0, data_length, PACKET_UNIT)]
    for index, packet in enumerate(packets):
        # 包计数从1开始，将最后一个包的count置为0，设为标志位
        index += 1
        if packet == packets[-1]:
            # 为最后一个包添加结束标志位， 包格式为： 包总长+0+数据包内容
            now_time = time.time()-expTime
            send_data = struct.pack('i', data_length) + struct.pack('i', 0) + struct.pack('d',
                                                                                          now_time) + packet  # 传输加入时间token
            socket_process.sendto(send_data, (UDP_IP_ADDRESS, UDP_PORT))
        else:
            # 为每个包添加包头， 每个包格式为： 图片总长度+包序列号+数据包内容
            now_time = time.time()-expTime
            send_data = struct.pack('i', data_length) + struct.pack('i', index) + struct.pack('d', now_time) + packet
            socket_process.sendto(send_data, (UDP_IP_ADDRESS, UDP_PORT))
            time.sleep(0.001)


def tcp_send(image):
    """
    通过TCP发送图像
    :param image: 要发送的图片数据
    """
    global tcp_socket, tcp_connected
    
    try:
        # 编码图像
        encoded_image = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 80])[1]
        data = np.array(encoded_image)
        image_bytes = data.tobytes()
        
        # 发送图像大小（4字节）+ 图像数据
        size = len(image_bytes)
        size_bytes = struct.pack('!I', size)  # 4字节表示图像大小
        
        if tcp_socket and tcp_connected:
            tcp_socket.sendall(size_bytes)
            tcp_socket.sendall(image_bytes)
        else:
            print("TCP server not connected, attempting to connect...")
            # 尝试连接到服务器
            try:
                tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcp_socket.connect((TCP_SERVER_IP, TCP_PORT))
                tcp_connected = True
                print(f"Connected to TCP server {TCP_SERVER_IP}:{TCP_PORT}")
                
                # 发送数据
                tcp_socket.sendall(size_bytes)
                tcp_socket.sendall(image_bytes)
            except Exception as e:
                print(f"Failed to connect to TCP server: {e}")
                tcp_connected = False
                if tcp_socket:
                    tcp_socket.close()
                    tcp_socket = None
    except Exception as e:
        print(f"Error in tcp_send: {e}")
        tcp_connected = False
        if tcp_socket:
            tcp_socket.close()
            tcp_socket = None


def send_thread(local_img, sock):
    udp_send(local_img, sock)



def resolve_thread(sock):
    while True:  # 以后处理之
        local_img = frame_image.copy()
        # time.sleep(0.04)
        anomaly_detect_img = anomaly_detect(local_img, visualize=False)
        global display_image
        display_image = anomaly_detect_img.copy()
        third_thread = threading.Thread(target=send_thread, args=(anomaly_detect_img, sock))
        third_thread.start()


def main_thread(ip: str, port: int):
    global UDP_IP_ADDRESS
    global UDP_PORT
    UDP_IP_ADDRESS = ip
    UDP_PORT = port

    print("Start Initializing Socket Process")
    # 创建UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 移除了TCP服务器线程，现在作为TCP客户端主动连接服务器

    # -------------NTP-Begin------------#
    # sock.bind((IP_ADDRESS_BIND, PORT_BIND))
    # for i in range(100):
    #     now_time = time.time()
    #     send_data = struct.pack('i', NTPHEAD) + struct.pack('d', now_time)
    #     sock.sendto(send_data, (IP_ADDRESS,PORT))
    #
    #     try:
    #         data, addr = sock.recvfrom(28)
    #         time_4 = time.time()
    #         print("Receive: ",end = "")
    #         print(i)
    #     except Exception:
    #         print('Recv timeout')
    #         raise IOError
    #     else:
    #         time_1 = struct.unpack('d', data[4:12])[0]
    #         time_2 = struct.unpack('d', data[12:20])[0]
    #         time_3 = struct.unpack('d', data[20:28])[0]
    #
    #         global delay
    #         global expTime
    #
    #         delay += ((time_4 - time_1) - (time_3 - time_2)) / 2
    #         expTime += ((time_4 - time_3) - (time_2 - time_1)) / 2
    #
    # print("Delay: ", delay / 100)
    # print("ExpTime: ", expTime / 100)
    # expTime = expTime / 100
    # -------------NTP--End-------------#

    print("Start Initializing Video Camera")
    # 配置RealSense相机
    # pipeline = rs.pipeline()
    # config = rs.config()
    # config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, FPS)

    # 启动 RealSense 相机
    cameraCapture = cv2.VideoCapture(0)  # 打开编号为0的摄像头

    cv2.namedWindow('Car Detected', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Car Detected', WIDTH, HEIGHT)

    # pipeline.start(config)
    success, frame = cameraCapture.read()

    global frame_image
    frame_image = np.zeros((HEIGHT, WIDTH, 3))
    # frame_image = cv2.imread("waitImg.png")
    #
    frame_image = cv2.resize(frame, (WIDTH, HEIGHT))
    print("Main Thread Frame:", end="")
    # print(frame_image[100][100])

    # second_thread = threading.Thread(target=resolve_thread, args=(sock,))
    # second_thread.start()

    while True:
        # frames = pipeline.wait_for_frames()
        # color_frame = frames.get_color_frame()
        # if not color_frame:
        #     continue

        success, frame = cameraCapture.read()

        # frame_image = cv2.resize(frame, (WIDTH, HEIGHT))
        # 将帧转换为 OpenCV 图像

        # frame_image = np.asanyarray(color_frame.get_data())
        frame_image = frame

        # 获取检测到的对象信息
        anomaly_detect_img, detected_objects = anomaly_detect(frame_image, visualize=False, return_objects=True)
        
        # 检查是否有新的行人ID
        new_pedestrian_detected = False
        with id_lock:
            for obj in detected_objects:
                if obj['type'] == 'pedestrian':
                    ped_id = obj['id']
                    if ped_id not in sent_pedestrian_ids:
                        sent_pedestrian_ids.add(ped_id)
                        new_pedestrian_detected = True
                        print(f"检测到新行人，ID: {ped_id}")
            
            # 清理过期的ID（可选：防止内存无限增长）
            if len(sent_pedestrian_ids) > 1000:  # 防止集合过大
                # 简单策略：清除一半
                items = list(sent_pedestrian_ids)
                sent_pedestrian_ids.clear()
                sent_pedestrian_ids.update(items[len(items)//2:])
        
        # 在锁外发送消息，避免在网络I/O时持有锁
        if new_pedestrian_detected:
            # 新的行人ID，发送通知
            message = "前方有行人经过"
            tcp_send_message(message)
            
        third_thread = threading.Thread(target=send_thread, args=(anomaly_detect_img, sock))
        third_thread.start()
        third_thread.join()

        # 通过TCP发送图像
        tcp_send(anomaly_detect_img)

        cv2.imshow('Car Detected', anomaly_detect_img[..., ::-1])

        key = cv2.waitKey(1)
        # Press esc or 'q' to close the image window
        if key == 27:
            cv2.destroyAllWindows()
            break

    # second_thread.join()
    # 关闭 RealSense 相机和 socket
    cameraCapture.release()
    # pipeline.stop()
    sock.close()
    
    # 关闭TCP连接
    global tcp_connected
    tcp_connected = False
    if tcp_socket:
        tcp_socket.close()


if __name__ == '__main__':
    main_thread(UDP_IP_ADDRESS, UDP_PORT)