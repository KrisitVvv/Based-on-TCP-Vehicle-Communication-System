# -*- coding: UTF-8 -*-
"""
车辆间消息接收端程序
用于接收来自其他车辆的消息，如"前车刹车"
"""
import socket
import cv2
import numpy as np
import struct
import threading
import time

# TCP接收配置 - 用于接收来自其他车辆的消息
VEHICLE_TCP_HOST = '0.0.0.0'  # 监听所有IP地址
VEHICLE_TCP_PORT = 8889  # 接收来自其他车辆的端口

class VehicleMessageReceiver:
    def __init__(self, host=VEHICLE_TCP_HOST, port=VEHICLE_TCP_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.client_socket = None
        self.connected = False
        self.running = False
        
    def start_server(self):
        """启动TCP服务器，等待客户端连接"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置socket选项，允许地址重用
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 绑定地址和端口
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            print(f"车辆消息接收服务器启动，监听 {self.host}:{self.port}")
            
            print("等待来自其他车辆的连接...")
            # 接收客户端连接
            self.client_socket, addr = self.socket.accept()
            print(f"来自其他车辆的连接已建立: {addr}")
            
            self.connected = True
            self.receive_data()
                
        except Exception as e:
            print(f"车辆消息接收服务器错误: {e}")
        finally:
            self.cleanup()
    
    def receive_data(self):
        """接收并处理来自其他车辆的文本消息"""
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
                    print(f"接收来自其他车辆的消息: {message}")
                    
                    # 处理特定消息
                    if message == "前车刹车":
                        print("警告：前车刹车！请立即采取制动措施！")
                        # 在这里可以添加其他处理逻辑，如触发车辆的制动系统
                    else:
                        print(f"收到其他消息: {message}")
                else:
                    print("接收到非文本消息，忽略处理")
                    
            except Exception as e:
                print(f"接收来自其他车辆的数据时出错: {e}")
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
        print("车辆消息接收端资源已清理")


def main():
    receiver = VehicleMessageReceiver()
    
    print("车辆消息接收程序启动")
    print(f"监听来自其他车辆的消息端口: {VEHICLE_TCP_PORT}")
    print("按Ctrl+C退出程序")
    
    try:
        receiver.start()
    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        print("车辆消息接收程序已退出")


if __name__ == '__main__':
    main()