#!/usr/bin/env python3
"""
SER文件读取模块
"""

import struct
import numpy as np
from pathlib import Path
from tifffile import imwrite, imread


def read_ser_header(ser_path):
    """读取SER文件头"""
    with open(ser_path, 'rb') as f:
        header = f.read(178)
        
    file_id = header[0:14].decode('ascii', errors='ignore')
    if file_id != 'LUCAM-RECORDER':
        raise ValueError(f"Invalid SER file format: {file_id}")
    
    lu_id = struct.unpack('<I', header[14:18])[0]
    color_id = struct.unpack('<I', header[18:22])[0]
    little_endian = struct.unpack('<I', header[22:26])[0]
    image_width = struct.unpack('<I', header[26:30])[0]
    image_height = struct.unpack('<I', header[30:34])[0]
    pixel_depth = struct.unpack('<I', header[34:38])[0]
    frame_count = struct.unpack('<I', header[38:42])[0]
    observer = header[42:82].decode('ascii', errors='ignore').strip()
    instrument = header[82:122].decode('ascii', errors='ignore').strip()
    telescope = header[122:162].decode('ascii', errors='ignore').strip()
    date_time = struct.unpack('<Q', header[162:170])[0]
    date_time_utc = struct.unpack('<Q', header[170:178])[0]
    
    return {
        'file_id': file_id,
        'lu_id': lu_id,
        'color_id': color_id,
        'little_endian': little_endian,
        'width': image_width,
        'height': image_height,
        'pixel_depth': pixel_depth,
        'frame_count': frame_count,
        'observer': observer,
        'instrument': instrument,
        'telescope': telescope,
        'date_time': date_time,
        'date_time_utc': date_time_utc,
    }


def load_frames_from_ser(ser_path):
    """从SER文件直接加载帧到内存（不保存到磁盘）"""
    print(f"Loading frames from {ser_path} into memory...")
    header = read_ser_header(ser_path)
    
    width = header['width']
    height = header['height']
    pixel_depth = header['pixel_depth']
    frame_count = header['frame_count']
    
    # 计算每帧的字节数
    if pixel_depth == 16:
        bytes_per_pixel = 2
    elif pixel_depth == 14:
        bytes_per_pixel = 2  # 14位数据也存储在16位中
    else:
        raise ValueError(f"Unsupported pixel depth: {pixel_depth}")
    
    bytes_per_frame = width * height * bytes_per_pixel
    header_size = 178
    
    # 预分配数组以存储所有帧
    frames = []
    
    with open(ser_path, 'rb') as f:
        # 跳过文件头
        f.seek(header_size)
        
        for frame_idx in range(frame_count):
            # 读取帧数据
            frame_data = f.read(bytes_per_frame)
            if len(frame_data) < bytes_per_frame:
                print(f"Warning: Only read {len(frame_data)} bytes for frame {frame_idx}, expected {bytes_per_frame}")
                break
            
            # 转换为numpy数组
            if pixel_depth == 16:
                frame_array = np.frombuffer(frame_data, dtype=np.uint16)
            elif pixel_depth == 14:
                # 14位数据可能需要特殊处理
                frame_array = np.frombuffer(frame_data, dtype=np.uint16)
            else:
                frame_array = np.frombuffer(frame_data, dtype=np.uint16)
            
            # 重塑为图像形状
            frame_array = frame_array.reshape((height, width))
            frames.append(frame_array)
            
            if (frame_idx + 1) % 50 == 0:
                print(f"Loaded {frame_idx + 1}/{frame_count} frames...")
    
    print(f"Loaded {len(frames)} frames into memory")
    return frames


def extract_frames(ser_path, frames_dir):
    """从SER文件提取帧到frames文件夹（保留此函数以保持兼容性）"""
    frames_dir = Path(frames_dir)
    frames_dir.mkdir(exist_ok=True)
    
    # 检查是否已有帧文件
    existing_frames = list(frames_dir.glob('frame_*.tiff'))
    if existing_frames:
        print(f"Found {len(existing_frames)} existing frames in {frames_dir}")
        return len(existing_frames)
    
    print(f"Extracting frames from {ser_path}...")
    frames = load_frames_from_ser(ser_path)
    
    # 保存帧到磁盘
    for frame_idx, frame_array in enumerate(frames):
        frame_path = frames_dir / f'frame_{frame_idx:05d}.tiff'
        imwrite(frame_path, frame_array)
    
    print(f"Extracted {len(frames)} frames to {frames_dir}")
    return len(frames)

