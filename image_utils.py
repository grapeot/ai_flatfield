#!/usr/bin/env python3
"""
图像处理工具函数模块
"""

import numpy as np
from PIL import Image
from tifffile import imwrite, imread
import cv2


def tiff_to_8bit_for_display(image_array):
    """将16位TIFF转换为8位用于显示（flat field，非负值，直接除以最大值）"""
    # 确保是2D数组
    if len(image_array.shape) > 2:
        image_array = image_array.squeeze()
    
    # 转换为浮点数进行计算
    img_float = image_array.astype(np.float32)
    
    # 获取最大值（16位最大值是65535）
    img_max = img_float.max()
    
    if img_max > 0:
        # 直接除以最大值然后乘以255
        normalized = (img_float / img_max * 255).astype(np.uint8)
    else:
        # 如果最大值是0，全部设为0
        normalized = np.zeros_like(image_array, dtype=np.uint8)
    
    return normalized


def show_image(image_array, window_name="Image", wait_key=True, prompt=""):
    """
    显示图像（使用OpenCV）
    Args:
        image_array: numpy数组图像（可以是16位TIFF）
        window_name: 窗口名称
        wait_key: 是否等待按键
        prompt: 提示信息
    Returns:
        按下的键（如果是wait_key=True）
    """
    # 转换为8位用于显示
    if image_array.dtype == np.uint16 or image_array.max() > 255:
        display_image = tiff_to_8bit_for_display(image_array)
    else:
        display_image = image_array.astype(np.uint8)
    
    # 确保是2D数组
    if len(display_image.shape) > 2:
        display_image = display_image.squeeze()
    
    # 显示图像
    cv2.imshow(window_name, display_image)
    
    if prompt:
        print(prompt)
    
    if wait_key:
        key = cv2.waitKey(0) & 0xFF
        cv2.destroyAllWindows()
        return key
    else:
        return None


def resize_image_to_match(image, target_shape):
    """
    将图像resize到目标尺寸
    Args:
        image: numpy数组图像
        target_shape: 目标形状 (height, width)
    Returns:
        resized_image: resize后的图像
    """
    if image.shape[:2] == target_shape:
        return image
    
    # 使用PIL进行resize
    if len(image.shape) == 2:
        # 灰度图
        pil_image = Image.fromarray(image)
        resized = pil_image.resize((target_shape[1], target_shape[0]), Image.Resampling.LANCZOS)
        return np.array(resized)
    else:
        # 彩色图（虽然我们主要是灰度，但为了安全）
        pil_image = Image.fromarray(image)
        resized = pil_image.resize((target_shape[1], target_shape[0]), Image.Resampling.LANCZOS)
        return np.array(resized)


def png_to_tiff_16bit(png_path, output_path, original_shape=None):
    """将PNG/JPG图像转回16位TIFF"""
    # 读取PNG/JPG图像
    pil_image = Image.open(png_path)
    img_array = np.array(pil_image)
    
    # 如果是RGB，转换为灰度
    if len(img_array.shape) == 3:
        # 转换为灰度（使用平均值）
        img_array = img_array.mean(axis=2).astype(np.uint8)
    
    # 转换为16位
    # 将8位值扩展到16位范围（0-255 -> 0-65535）
    img_16bit = (img_array.astype(np.uint16) * 257)  # 257 = 65535 / 255
    
    # 如果提供了原始形状，调整大小
    if original_shape:
        if img_16bit.shape[:2] != original_shape[:2]:
            print(f"Resizing image from {img_16bit.shape} to {original_shape}")
            img_16bit = resize_image_to_match(img_16bit, original_shape[:2])
    
    # 保存为16位TIFF
    imwrite(output_path, img_16bit)
    print(f"Saved 16-bit TIFF to: {output_path} (shape: {img_16bit.shape})")
    return output_path


def numpy_to_image_bytes(image_array, format='PNG'):
    """将numpy数组转换为图像字节流（用于发送给Gemini，flat field非负值，直接除以最大值）"""
    # 确保是2D数组
    if len(image_array.shape) > 2:
        image_array = image_array.squeeze()
    
    # 转换为浮点数进行计算
    img_float = image_array.astype(np.float32)
    
    # 获取最大值
    img_max = img_float.max()
    
    if img_max > 0:
        # 直接除以最大值然后乘以255
        normalized = (img_float / img_max * 255).astype(np.uint8)
    else:
        # 如果最大值是0，全部设为0
        normalized = np.zeros_like(image_array, dtype=np.uint8)
    
    # 转换为PIL Image
    if len(normalized.shape) == 2:
        # 灰度图
        pil_image = Image.fromarray(normalized, mode='L')
    else:
        pil_image = Image.fromarray(normalized)
    
    # 转换为字节流
    from io import BytesIO
    img_bytes = BytesIO()
    pil_image.save(img_bytes, format=format)
    img_bytes.seek(0)
    return img_bytes.getvalue()


def save_binary_file(file_name, data):
    """保存二进制文件"""
    f = open(file_name, "wb")
    f.write(data)
    f.close()
    print(f"File saved to: {file_name}")

