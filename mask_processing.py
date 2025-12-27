#!/usr/bin/env python3
"""
Mask处理模块
"""

import numpy as np
from scipy.ndimage import binary_dilation, gaussian_filter


def expand_mask(mask, expand_pixels=10, sigma=3.0):
    """
    对mask做柔性扩展
    Args:
        mask: 输入mask (0-1之间的值)
        expand_pixels: 扩展的像素数
        sigma: Gaussian blur的sigma值
    Returns:
        expanded_mask: 扩展后的mask，保证原来为1的部分还是1
    """
    # 确保mask是float类型
    mask_float = mask.astype(np.float32)
    
    # 创建binary mask（大于0.5的为True）
    binary_mask = mask_float > 0.5
    
    # 使用binary dilation扩展
    # 创建一个圆形结构元素
    structure_size = expand_pixels * 2 + 1
    structure = np.zeros((structure_size, structure_size), dtype=bool)
    y, x = np.ogrid[:structure_size, :structure_size]
    center = structure_size // 2
    structure[(x - center)**2 + (y - center)**2 <= expand_pixels**2] = True
    
    # 执行dilation
    expanded_binary = binary_dilation(binary_mask, structure=structure)
    
    # 将binary mask转换为float
    expanded_mask = expanded_binary.astype(np.float32)
    
    # 应用Gaussian blur使边缘平滑
    expanded_mask = gaussian_filter(expanded_mask, sigma=sigma)
    
    # 保证原来为1的部分还是1（取最大值）
    expanded_mask = np.maximum(expanded_mask, mask_float)
    
    # 确保值在0-1范围内
    expanded_mask = np.clip(expanded_mask, 0.0, 1.0)
    
    return expanded_mask

