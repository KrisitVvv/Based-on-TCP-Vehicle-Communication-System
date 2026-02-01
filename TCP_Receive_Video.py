# -*- coding: UTF-8 -*-
"""
TCP图像接收端程序
用于接收通过TCP传输的图像并显示
"""
import socket
import cv2
import numpy as np
import struct
import threading
import time

# TCP接收配置
TCP_HOST = '0.0.0.0'  # 监听所有IP地址，可根据需要修改
TCP_PORT = 8888  # 与发送端相同的端口

# TCP发送配置 - 用于向其他车辆发送消息
VEHICLE_TCP_HOST = '192.168.1.196'  # 第二辆车的IP地址，需要根据实际情况修改
VEHICLE_TCP_PORT = 8889  # 发送到其他车辆的端口，需要与第二辆车的接收端口一致

class TCPImageReceiver:
    def __init__(self, host=TCP_HOST, port=TCP_PORT, vehicle_host=VEHICLE_TCP_HOST, vehicle_port=VEHICLE_TCP_PORT):
        self.host = host
        self.port = port
        self.vehicle_host = vehicle_host
        self.vehicle_port = vehicle_port
        self.socket = None
        self.client_socket = None
        self.connected = False
        self.running = False
        self.vehicle_tcp_socket = None  # 用于向其他车辆发送消息的socket
        
    def send_brake_message(self, message="前车刹车"):
        """向其他车辆发送刹车消息
        :param message: 要发送的消息内容
        """
        try:
            # 尝试连接到第二辆车
            if not self.vehicle_tcp_socket:
                self.vehicle_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.vehicle_tcp_socket.connect((self.vehicle_host, self.vehicle_port))
                print(f"连接到车辆 {self.vehicle_host}:{self.vehicle_port}")
            
            # 编码消息为字节
            message_bytes = message.encode('utf-8')
            
            # 使用特殊标识表示这是文本消息（例如，使用负数表示）
            size = len(message_bytes)
            size_bytes = struct.pack('!I', size | (1 << 31))  # 最高位设为1表示文本消息
            
            # 发送数据
            self.vehicle_tcp_socket.sendall(size_bytes)
            self.vehicle_tcp_socket.sendall(message_bytes)
            print(f"已向其他车辆发送消息: {message}")
            
        except Exception as e:
            print(f"发送消息到其他车辆失败: {e}")
            # 关闭当前连接，下次会重新连接
            if self.vehicle_tcp_socket:
                self.vehicle_tcp_socket.close()
                self.vehicle_tcp_socket = None

    def start_server(self):
        """启动TCP服务器，等待客户端连接"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置socket选项，允许地址重用
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 绑定地址和端口
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            print(f"TCP图像接收服务器启动，监听 {self.host}:{self.port}")
            
            # 接收客户端连接
            self.client_socket, addr = self.socket.accept()
            print(f"客户端已连接: {addr}")
            
            self.connected = True
            self.receive_data()
                
        except Exception as e:
            print(f"TCP服务器错误: {e}")
        finally:
            self.cleanup()
    
    def receive_data(self):
        """接收并处理图像或文本消息"""
        while self.connected and self.running:
            try:
                # 接收数据大小（4字节）
                size_data = self._recv_all(4)
                if not size_data:
                    break
                    
                # 解析大小，检查最高位是否为1（表示文本消息）
                size_raw = struct.unpack('!I', size_data)[0]
                is_text_message = (size_raw & (1 << 31)) != 0  # 检查最高位
                actual_size = size_raw & ((1 << 31) - 1)  # 去掉最高位，获取实际大小
                
                # 接收数据
                data = self._recv_all(actual_size)
                if not data:
                    break
                
                if is_text_message:
                    # 解码文本消息
                    message = data.decode('utf-8')
                    print(f"接收消息: {message}")
                    # 在控制台打印消息
                    if message.startswith("NEW_PEDESTRIAN_DETECTED:"):
                        print("前方有行人经过")
                        # 发送"前车刹车"消息到其他车辆
                        self.send_brake_message("前车刹车")
                    elif message == "前方有行人经过":
                        print("前方有行人经过")
                        # 发送"前车刹车"消息到其他车辆
                        self.send_brake_message("前车刹车")
                    else:
                        print(message)
                else:
                    # 解码图像
                    nparr = np.frombuffer(data, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if image is not None:
                        # 显示图像
                        cv2.imshow('Received Image', image)
                        
                        # 按'q'键退出
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q'):
                            print("用户按下'q'键，退出接收")
                            self.connected = False
                            self.running = False
                    else:
                        print("图像解码失败")
                    
            except Exception as e:
                print(f"接收数据时出错: {e}")
                self.connected = False
                break
    
    def _recv_all(self, size):
        """确保接收指定大小的数据"""
        data = b''
        while len(data) < size:
            try:
                packet = self.client_socket.recv(size - len(data))
                if not packet:
                    return None
                data += packet
            except Exception as e:
                print(f"接收数据时出错: {e}")
                return None
        return data
    
    def start(self):
        """启动接收器"""
        self.running = True
        server_thread = threading.Thread(target=self.start_server)
        server_thread.daemon = True
        server_thread.start()
        
        try:
            # 主线程等待，直到用户退出
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("接收到中断信号，正在关闭...")
        finally:
            self.stop()
    
    def stop(self):
        """停止接收器"""
        self.running = False
        self.connected = False
        self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        if self.client_socket:
            self.client_socket.close()
        if self.socket:
            self.socket.close()
        cv2.destroyAllWindows()
        print("资源已清理")


def main():
    # 可以通过修改参数来指定要发送消息的目标车辆
    receiver = TCPImageReceiver(vehicle_host=VEHICLE_TCP_HOST, vehicle_port=VEHICLE_TCP_PORT)
    
    print("TCP图像接收程序启动")
    print("按'q'键或使用Ctrl+C退出程序")
    
    try:
        receiver.start()
    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        print("程序已退出")


if __name__ == '__main__':
    main()