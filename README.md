# <p align="center"> Based on TCP Vehicle Communication System </p>
## Introduction
This project is based on TCP or UDP agreement to achieve vehicle to vehicle and vehicle to infrastructure communication.This is my University course work,it's have any problems,you can try to solve it.
## Information
This project is sloved in scenarios where the A-pillar of a vehicle or roadside parking causes a blind spot,a pedestrian suddenly appears in the driving path,how to avoid the collision?  

We simulation the roadside camera and two vehicle in pedestrian appers in the road.Firstly,we use a camera to capture the video,and accross YOLOv5 to recognize the pedestrian or motocycle.If the pedestrian or motocycle appears in the road,computer will send a warning to all vehicles within the range,the vehicle received the warning,and the vehicle will emergency stop.Besides that,we consider the front vehicle have emergency stop,the following vehicle not in the broadcast range,so the following vehicle have a risk of rear-end collision.To solve this problem, we introduced the vehicle to vehicle communication system.The system not only in the one scenarios applicable,but also in any front vehicle emergency stop to avoid the collision.  
<p align="center"> <img width="525" height="344" src="https://github.com/user-attachments/assets/e95dbd17-36e3-4335-b0be-09716dfc0b50"/> </p>

## Environment
### Software and Hardware
We develop this project in a PC and two Songling Vehicle.The vehicle is equipped with a NVIDIA Jetson AGX Xavier,and running Ubuntu 18.04.  

We use Conda to manage our software environment.In the project,we use Python and **yolov5** to achieve the vehicle detection.If you want to reproduce this repository,you can follow the steps below:  
* Computer Environment:  
```bash
# Create a conda environment
conda create -n tcp_communication
conda activate tcp_communication
conda install --file ./VehicleTracking/requirements.txt
```
* Vehicle Environment:  
```bash
conda create -n tcp_receive
conda activate tcp_receive
conda install numpy -y
conda install -c conda-forge opencv-python -y
```
This project Demo is using external camera,we use a USB camera to capture the video,you can try to use computer camera or internet camera to achieve the same effect.
### Internet
This project need to computer transmit video to vehicle,therefore,network bondwidth is important.During our experiment,we use WIFI to connect computer and vehicle,at the beginning,we pursued longer transmission distances selected 2.4GHz WIFI,but the network bondwidth is not enough,causes the video to be very laggy.In the end, we solved this problem by using **5GHz WiFi**.  

If you experimental environment have to 2.4GHz WIFI,you can modify the file **RSU_Send_Video.py** line 25-27 to change the vedio quality.
```python
WIDTH = 1280 # vedio width
HEIGHT = 720 # vedio height
FPS = 30 # vedio FPS
```
## Running
### Computer
Prepare your camera and the corresponding driver.  
Open file **RSU_Send_Video.py** line 20-21 to change front vehicle's ip address and port.  
```python
TCP_SERVER_IP = '10.204.9.213'
TCP_PORT = 8888
```
In your project path running terminal:
```bash
conda activate tcp_communication
python RSU_Send_Video.py
```
### Front Vehicle
Open file **TCP_Receive_Video.py** line 18-19 to change following vehicle's ip address and port.
```python
VEHICLE_TCP_HOST = '192.168.1.196'
VEHICLE_TCP_PORT = 8889 
```
In your project path running terminal:
```bash
conda activate tcp_receive
python TCP_Receive_Video.py
```
### Following Vehicle
The vehicle just need to running terminal:
```bash
conda activate tcp_receive
python TCP_Receive_Vehicle_Message.py
```
### By the way
You'd better to firstly running folowing vehicle,front vehicle and then running computer.In some special situations,not follow the order of running,you may have some problems.  
If you don't know how to get ip address,you can in Songling vehicle System running order `ifconfig` to find.
## Effect
### YOLO Verify
We use YOLO to recongnize the pedestrian in lab,it's effect is nice.  
<p align="center"> <img width="577" height="327" src="https://github.com/user-attachments/assets/c1e1deda-075a-48c5-9d87-44b170ef2313" /></p>

### Communication Verify
In order to prevent excessive warning messages from being generated due to repeated identifications of the same pedestrian, we adopted an algorithm to mark individuals with an ID as identifiers.  

From the front vehicle message,it's successful to receive the warning message and transmit to the following vehicle.  
<p align="center"><img width="849" height="330" src="https://github.com/user-attachments/assets/0952e8f4-1822-4c52-85f1-bd3ab8371d3e" /></p>  
In the following vehicle,it's successful to receive the warning message and respond.  
<p align="center"><img width="746" height="277" src="https://github.com/user-attachments/assets/d24a6806-a60b-4507-842e-54022a0fe3fe" /></p>

### In the real scene
In the real scene,the camera can recognize the pedestrian and the vehicle can receive the warning message and respond.  
<p align="center"><img width="529" height="477" src="https://github.com/user-attachments/assets/44ef1ae7-1225-40c5-87bc-6b67d97f047b" /></p>

## How to improve
1.During our use, we found that the video transmit to vehicle,video's RGB is faulty.You can try to solve it.  
2.We only notify the following vehicle when the vehicle in front receives a warning.Any sudden braking by the vehicle ahead that does not meet expectations should be communicated to the following vehicle.  
3.You can try to use the TCP agreement to achieve control of the vehicle,let them receive the warning message and automatically stop.If you want to achieve the function, you need to learning Songling Vehicle's ROS topics how to use.
