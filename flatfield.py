#!/usr/bin/env python3
"""
Flat field计算模块
"""

import numpy as np
from pathlib import Path
from tifffile import imread
from scipy.interpolate import interp1d
from image_utils import resize_image_to_match


def compute_median_flatfield_from_frames(frames):
    """从帧数组计算时间维度的中位数（median flat field）"""
    if not frames:
        raise ValueError("No frames provided")
    
    print(f"Computing median from {len(frames)} frames...")
    
    # 转换为numpy数组
    frames_array = np.array(frames)
    
    # 计算时间维度的中位数
    median_flatfield = np.median(frames_array, axis=0).astype(frames_array.dtype)
    
    print(f"Computed median flat field: shape={median_flatfield.shape}, dtype={median_flatfield.dtype}")
    return median_flatfield


def compute_median_flatfield(frames_dir):
    """从frames文件夹计算时间维度的中位数（median flat field）"""
    frames_dir = Path(frames_dir)
    frame_files = sorted(frames_dir.glob('frame_*.tiff'))
    
    if not frame_files:
        raise ValueError(f"No frame files found in {frames_dir}")
    
    print(f"Loading {len(frame_files)} frames to compute median...")
    
    # 读取所有帧
    frames = []
    for frame_file in frame_files:
        frame = imread(frame_file)
        frames.append(frame)
    
    return compute_median_flatfield_from_frames(frames)


def histogram_match_using_mask(source, target, mask_zero):
    """
    使用mask=0区域的histogram进行匹配，将source映射到target的亮度空间
    
    Args:
        source: 源图像（inpainted）
        target: 目标图像（median_flatfield）
        mask_zero: mask=0的区域（boolean数组）
    
    Returns:
        matched: 匹配后的图像
    """
    # 只使用mask=0区域的像素进行histogram matching
    source_mask_values = source[mask_zero].flatten()
    target_mask_values = target[mask_zero].flatten()
    
    if len(source_mask_values) == 0:
        print("Warning: No mask=0 pixels found, skipping histogram matching")
        return source
    
    # 计算histogram
    # 使用相同的bins范围
    min_val = min(source_mask_values.min(), target_mask_values.min())
    max_val = max(source_mask_values.max(), target_mask_values.max())
    n_bins = 256
    
    # 计算累积分布函数（CDF）
    source_hist, source_bins = np.histogram(source_mask_values, bins=n_bins, range=(min_val, max_val))
    target_hist, target_bins = np.histogram(target_mask_values, bins=n_bins, range=(min_val, max_val))
    
    # 归一化到CDF
    source_cdf = source_hist.cumsum()
    source_cdf = source_cdf / source_cdf[-1] if source_cdf[-1] > 0 else source_cdf
    
    target_cdf = target_hist.cumsum()
    target_cdf = target_cdf / target_cdf[-1] if target_cdf[-1] > 0 else target_cdf
    
    # 创建映射函数：对于source的每个值，找到对应的target值
    # 使用bin的中心值
    source_bin_centers = (source_bins[:-1] + source_bins[1:]) / 2
    target_bin_centers = (target_bins[:-1] + target_bins[1:]) / 2
    
    # 创建映射：对于source的每个CDF值，找到target中对应的值
    # 使用插值来创建平滑的映射
    mapping = np.zeros_like(source_bin_centers)
    for i, source_cdf_val in enumerate(source_cdf):
        # 找到target CDF中最接近的值
        idx = np.searchsorted(target_cdf, source_cdf_val)
        if idx >= len(target_cdf):
            idx = len(target_cdf) - 1
        elif idx > 0 and abs(target_cdf[idx-1] - source_cdf_val) < abs(target_cdf[idx] - source_cdf_val):
            idx = idx - 1
        mapping[i] = target_bin_centers[idx]
    
    # 创建插值函数
    # 处理边界情况
    source_bin_centers_extended = np.concatenate([[min_val - 1], source_bin_centers, [max_val + 1]])
    mapping_extended = np.concatenate([[target_bin_centers[0]], mapping, [target_bin_centers[-1]]])
    
    # 使用线性插值创建映射函数
    interp_func = interp1d(source_bin_centers_extended, mapping_extended, 
                          kind='linear', bounds_error=False, 
                          fill_value=(target_bin_centers[0], target_bin_centers[-1]))
    
    # 应用映射到整个图像
    matched = interp_func(source).astype(source.dtype)
    
    # 确保值在合理范围内
    matched = np.clip(matched, target.min(), target.max())
    
    return matched


def compute_final_flatfield(median_flatfield, inpainted, mask):
    """
    计算final flat field，使得 median_flatfield / final_flatfield = inpainted
    
    算法：
    1. 计算 ratio = median_flatfield / inpainted（这是理想的final_flatfield）
    2. 在mask=0的地方，final_flatfield = 1.0（不改变）
    3. 在mask>0的地方，使用计算出的ratio值
    4. 使用线性插值：final_flatfield = (1 - mask) * 1.0 + mask * ratio
    
    数学推导：
    - 目标：median_flatfield / final_flatfield = inpainted
    - 因此：final_flatfield = median_flatfield / inpainted
    - 在mask=0处：final_flatfield = 1.0
    - 在mask>0处：final_flatfield = median_flatfield / inpainted
    - 混合：final_flatfield = (1 - mask) * 1.0 + mask * (median_flatfield / inpainted)
    
    确保所有图像尺寸一致，以median_flatfield为准
    """
    # 获取目标尺寸（以median_flatfield为准）
    target_shape = median_flatfield.shape[:2]
    
    # 检查并resize inpainted图像
    if inpainted.shape[:2] != target_shape:
        print(f"Resizing inpainted image from {inpainted.shape} to match median_flatfield {median_flatfield.shape}")
        inpainted = resize_image_to_match(inpainted, target_shape)
    
    # 检查并resize mask
    if mask.shape[:2] != target_shape:
        print(f"Resizing mask from {mask.shape} to match median_flatfield {median_flatfield.shape}")
        mask = resize_image_to_match(mask, target_shape)
    
    # 确保mask是float类型且在0-1范围内
    mask_float = mask.astype(np.float32)
    
    # 如果mask是16位，归一化到0-1
    if mask_float.max() > 1.0:
        mask_float = mask_float / 65535.0
    
    mask_float = np.clip(mask_float, 0.0, 1.0)
    
    # 转换为float32进行计算
    median_float = median_flatfield.astype(np.float32)
    inpainted_float = inpainted.astype(np.float32)
    
    # 使用mask=0区域的histogram进行亮度配准
    # 这样可以修正Gemini可能改变的整体亮度偏移
    mask_zero_mask = mask_float == 0.0
    if np.sum(mask_zero_mask) > 0:
        print(f"Performing histogram matching using {np.sum(mask_zero_mask)} mask=0 pixels...")
        inpainted_float = histogram_match_using_mask(inpainted_float, median_float, mask_zero_mask)
        print("Histogram matching completed")
    
    # 避免除零，添加小的epsilon
    epsilon = 1e-6
    inpainted_safe = np.maximum(inpainted_float, epsilon)
    
    # 计算 ratio = median_flatfield / inpainted
    ratio = median_float / inpainted_safe
    
    # 如果mask是2D但图像是3D，需要扩展mask的维度
    if len(mask_float.shape) == 2 and len(median_float.shape) == 3:
        mask_float = mask_float[:, :, np.newaxis]
    
    # 计算final_flatfield：
    # 在mask=0的地方 = 1.0
    # 在mask>0的地方 = ratio
    # 线性插值：final = (1 - mask) * 1.0 + mask * ratio
    final_flatfield = (1.0 - mask_float) * 1.0 + mask_float * ratio
    
    # 额外保证：在mask=0的地方强制设为1.0（防止浮点误差）
    if len(mask_float.shape) == 2:
        final_flatfield[mask_zero_mask] = 1.0
    else:
        final_flatfield[mask_zero_mask, :] = 1.0
    
    # 确保是float32类型
    final_flatfield = final_flatfield.astype(np.float32)
    
    return final_flatfield

