import sys
import matplotlib.pyplot as plt
sys.path.append('../')
import os
import numpy as np
import yaml
import glob
import pickle as pkl
import random
import cv2
import copy
from PIL import Image
import torch
import argparse


import time
import pyrealsense2 as rs
# import torch_tensorrt
# 下面为目标检测，轨迹跟踪引入模块
#lib_path = os.path.abspath(os.path.join('VehicleTracking/application/main/infrastructure', 'yolov5'))  #添加到环境变量
#sys.path.append(lib_path)

lib_path = os.path.abspath(os.path.join('VehicleTracking/application', 'main'))  #添加到环境变量
sys.path.append(lib_path)
from VehicleTracking.application.main.infrastructure.handlers.track import Yolo5Tracker

print("Cuda available: ", torch.cuda.is_available())
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 初始化目标检测，轨迹跟踪
tracker = Yolo5Tracker(config_path="VehicleTracking/settings/config.yml")
current_directory = os.path.dirname(os.path.abspath(__file__))

# 添加全局变量来跟踪已发送的行人ID和之前检测到的ID
sent_pedestrian_ids = set()
previous_detected_ids = set()

global current_frame_id
current_frame_id = 0

def anomaly_detect(frame_image, visualize=False, return_objects=False):
    global current_frame_id, sent_pedestrian_ids, previous_detected_ids
    
    # current_directory = os.path.dirname(os.path.abspath(__file__))
    # 随机生成颜色
    tracker_colors = []
    for i in range(999):
        tracker_colors.append([random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)])

    # if args.input_type == 0:
    #     FPS = 30
    #     capture = cv2.VideoCapture(0)
    #     ref, frame = capture.read()
    #     if not ref:
    #         raise ValueError("未能正确读取摄像头（视频），请注意是否正确安装摄像头（是否正确填写视频路径）。")
    current_frame_id += 1

    # if args.input_type == 0:
    #     ref, frame = capture.read()
    #     if not ref:
    #         break
    #     # 格式转变，BGRtoRGB
    #     frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    #     # 进行检测

    print("-----------------------------第" + str(current_frame_id) + "帧:-----------------------------")
    result = tracker.detect(frame_image, current_frame_id)
    show_result = result[..., ::-1]
    
    # 如果需要返回检测对象信息
    detected_objects = []
    if return_objects:
        # 检查current_frame是否为字典
        if isinstance(tracker.current_frame, dict):
            # 从tracker获取当前帧的所有ID
            current_ids = set(tracker.current_frame.get('IDs_vehicles', []))
            print(f"当前帧检测到的ID: {current_ids}")
            print(f"之前帧的ID: {previous_detected_ids}")
            
            # 检查新增的ID
            new_ids = current_ids - previous_detected_ids
            print(f"新增的ID: {new_ids}")
            
            for new_id in new_ids:
                # 检查该ID是否已经处理过
                if new_id not in sent_pedestrian_ids:
                    # 检查这个ID是否是行人 (类别为 'person')
                    if new_id in tracker.vehicle_infos and tracker.vehicle_infos[new_id]['type_vehicle'] == 'person':
                        # 这是一个新的行人ID
                        print(f"检测到新行人，ID: {new_id}")
                        detected_objects.append({
                            'id': int(new_id),
                            'type': 'pedestrian',
                            'frame': current_frame_id
                        })
                        # 记录已发送的行人ID
                        sent_pedestrian_ids.add(new_id)
                else:
                    print(f"ID {new_id} 已经处理过，跳过")
            
            # 更新previous_detected_ids为当前ID
            previous_detected_ids = current_ids.copy()
        else:
            print("tracker.current_frame 不是字典类型")
    
    # if visualize:
    #     cv2.imshow("car detected", show_result)
    #     cv2.waitKey(1)
    
    if return_objects:
        return show_result, detected_objects
    else:
        return show_result