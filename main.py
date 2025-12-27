#!/usr/bin/env python3
"""
AI Flat Field Correction - 主程序
使用 Gemini AI 进行天文图像 flat field 校正
"""

import argparse
import os
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from tifffile import imwrite, imread

from ser_reader import load_frames_from_ser
from flatfield import compute_median_flatfield_from_frames, compute_final_flatfield
from gemini_client import process_with_gemini, generate_inpainted_image
from mask_processing import expand_mask
from image_utils import show_image, resize_image_to_match


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='AI-Powered Flat Field Correction Tool')
    parser.add_argument('--input', type=str, default='2025_11_9T16_00_34.ser',
                        help='Path to the input SER file (default: 2025_11_9T16_00_34.ser)')
    args = parser.parse_args()

    # 加载 .env 文件
    load_dotenv()
    
    # 检查环境变量
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        print("Please create a .env file with your API key:")
        print("  GEMINI_API_KEY=your_api_key_here")
        print("\nGet your API key from: https://aistudio.google.com/app/apikey")
        return
    
    print(f"GEMINI_API_KEY loaded: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '***'}")
    
    ser_file = args.input
    if not Path(ser_file).exists():
        print(f"Error: Input file {ser_file} not found.")
        return
        
    ser_stem = Path(ser_file).stem
    
    # 步骤1: 直接从SER文件加载帧到内存（不保存到磁盘）
    # 步骤2: 计算median flat field - 幂等性检查
    median_flatfield_path = f'median_flatfield_{ser_stem}.tiff'
    if Path(median_flatfield_path).exists():
        print(f"\nUsing existing median flat field: {median_flatfield_path}")
        median_flatfield = imread(median_flatfield_path)
    else:
        print(f"\nLoading frames from {ser_file} and computing median flat field...")
        # 直接从SER文件加载帧到内存
        frames = load_frames_from_ser(ser_file)
        # 计算median flat field
        median_flatfield = compute_median_flatfield_from_frames(frames)
        # 保存median flat field（16位TIFF）
        imwrite(median_flatfield_path, median_flatfield)
        print(f"Saved median flat field to {median_flatfield_path}")
    
    # 显示 median flat field
    print("\n=== Step 1: Median Flat Field ===")
    show_image(median_flatfield, "Median Flat Field", wait_key=True, 
               prompt="Review the median flat field. Press any key to continue...")
    
    # 步骤2: 使用Gemini生成mask0
    print("\n=== Step 2: Generating Dust Mask ===")
    mask0_path = f'mask_0_{ser_stem}.tiff'
    if Path(mask0_path).exists():
        print(f"Using existing mask: {mask0_path}")
        mask0 = imread(mask0_path)
    else:
        print("Generating mask0 with Gemini...")
        mask_files = process_with_gemini(
            median_flatfield,
            prompt="This is an astronomical imaging flat field image from a sensor that contains dust particles. First, identify what type of astronomical image this is. Then generate a de-dusting mask image where pixel values range from 0 to 1: 0 indicates areas that should remain unchanged (clean areas), and 1 indicates areas that need dust removal (dust-covered areas). Values between 0 and 1 are acceptable for partial coverage. The mask must be tight and closely follow the detected dust particles, avoiding unnecessary coverage of clean areas."
        )
        # 保存第一个mask为TIFF
        if mask_files:
            # process_with_gemini 返回的是 TIFF 文件列表
            # 直接读取 TIFF 文件
            mask0 = imread(mask_files[0])
            # 如果文件不存在，保存它
            if not Path(mask0_path).exists():
                imwrite(mask0_path, mask0)
        else:
            raise ValueError("No mask file generated")
    
    # 显示 mask0
    show_image(mask0, "Dust Mask", wait_key=True,
               prompt="Review the dust mask. Press any key to continue...")
    
    # 获取原始flat field的尺寸作为参考
    target_shape = median_flatfield.shape[:2]
    print(f"Target image shape: {target_shape}")
    
    # 步骤3: 对mask0做expansion（不显示）
    print("\n=== Step 3: Expanding Mask ===")
    expanded_mask_path = f'mask0_expanded_{ser_stem}.tiff'
    
    if Path(expanded_mask_path).exists():
        print(f"Using existing expanded mask: {expanded_mask_path}")
        mask0_expanded = imread(expanded_mask_path)
        # 检查尺寸并resize
        if mask0_expanded.shape[:2] != target_shape:
            print(f"Resizing expanded mask from {mask0_expanded.shape} to {target_shape}")
            mask0_expanded = resize_image_to_match(mask0_expanded, target_shape)
            # 重新保存正确尺寸的mask
            imwrite(expanded_mask_path, mask0_expanded)
        mask0_expanded = mask0_expanded.astype(np.float32) / 65535.0  # 归一化到0-1
    else:
        # 检查尺寸并resize到目标尺寸
        if mask0.shape[:2] != target_shape:
            print(f"Resizing mask0 from {mask0.shape} to {target_shape}")
            mask0 = resize_image_to_match(mask0, target_shape)
        
        if mask0.dtype == np.uint16:
            mask0_normalized = mask0.astype(np.float32) / 65535.0
        else:
            mask0_normalized = mask0.astype(np.float32) / 255.0
        
        # 扩展mask
        mask0_expanded = expand_mask(mask0_normalized, expand_pixels=10, sigma=3.0)
        
        # 保存扩展后的mask（转回16位）
        mask0_expanded_16bit = (mask0_expanded * 65535.0).astype(np.uint16)
        imwrite(expanded_mask_path, mask0_expanded_16bit)
        print(f"Saved expanded mask to: {expanded_mask_path} (shape: {mask0_expanded_16bit.shape})")
    
    # 步骤4: 使用Gemini生成inpainted图像（支持重试）
    print("\n=== Step 4: Generating Inpainted Image ===")
    inpainted_path = f'inpainted_{ser_stem}.tiff'
    
    while True:
        if Path(inpainted_path).exists():
            print(f"Using existing inpainted image: {inpainted_path}")
            inpainted_image = imread(inpainted_path)
        else:
            print("Generating inpainted image with Gemini...")
            inpainted_files = generate_inpainted_image(median_flatfield, mask0_expanded)
            
            if inpainted_files:
                # generate_inpainted_image 返回的是 TIFF 文件列表
                # 直接读取 TIFF 文件
                inpainted_image = imread(inpainted_files[0])
                # 如果文件不存在，保存它
                if not Path(inpainted_path).exists():
                    imwrite(inpainted_path, inpainted_image)
            else:
                raise ValueError("No inpainted file generated")
        
        # 检查inpainted图像尺寸
        if inpainted_image.shape[:2] != target_shape:
            print(f"Resizing inpainted image from {inpainted_image.shape} to {target_shape}")
            inpainted_image = resize_image_to_match(inpainted_image, target_shape)
            imwrite(inpainted_path, inpainted_image)
        
        # 显示 inpainted 图像
        key = show_image(inpainted_image, "Inpainted Image", wait_key=True,
                        prompt="Review the inpainted image. Press 'R' to retry, or any other key to continue...")
        
        if key == ord('r') or key == ord('R'):
            print("Retrying inpainting...")
            # 删除现有文件，重新生成
            if Path(inpainted_path).exists():
                Path(inpainted_path).unlink()
            continue
        else:
            break
    
    # 步骤5: 计算final flat field
    print("\n=== Step 5: Computing Final Flat Field ===")
    print(f"Algorithm: final_flatfield = (1 - mask) * 1.0 + mask * (median_flatfield / inpainted)")
    print(f"  - Where mask=0: final_flatfield = 1.0 (no change)")
    print(f"  - Where mask>0: final_flatfield = median_flatfield / inpainted")
    
    final_image_path = f'final_flatfield_{ser_stem}.tiff'
    if Path(final_image_path).exists():
        print(f"Using existing final flat field: {final_image_path}")
        final_flatfield = imread(final_image_path)
    else:
        # 计算final flat field（返回float32）
        final_flatfield_float = compute_final_flatfield(median_flatfield, inpainted_image, mask0_expanded)
        
        # Clip 超过 1.0 的值到 1.0，保持 mask=0 区域为 1.0
        final_clipped = np.clip(final_flatfield_float, 0.0, 1.0)
        clipped_count = np.sum(final_flatfield_float > 1.0)
        if clipped_count > 0:
            print(f"Warning: {clipped_count} pixels ({100*clipped_count/final_flatfield_float.size:.2f}%) have values > 1.0, clipping to 1.0")
        
        # 转换为 uint16 TIFF: 值 1.0 对应 65535
        final_flatfield = (final_clipped * 65535.0).astype(np.uint16)
        
        # 保存为 uint16 TIFF 格式
        imwrite(final_image_path, final_flatfield)
        print(f"Saved final flat field to {final_image_path} (uint16 TIFF)")
    
    # 显示 final flat field
    show_image(final_flatfield, "Final Flat Field", wait_key=True,
               prompt="Review the final flat field. Press any key to finish...")
    
    print("\n=== Processing Complete! ===")
    print(f"Input SER file: {ser_file}")
    print(f"Median flat field: {median_flatfield_path}")
    print(f"Mask0: mask_0_{ser_stem}.tiff")
    print(f"Expanded mask: mask0_expanded_{ser_stem}.tiff")
    print(f"Inpainted image: {inpainted_path}")
    print(f"Final flat field: {final_image_path}")


if __name__ == '__main__':
    main()
