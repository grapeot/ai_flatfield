#!/usr/bin/env python3
"""
Gemini API (Nano Banana Pro) 调用模块
"""

import os
import mimetypes
import numpy as np
from google import genai
from google.genai import types
from image_utils import numpy_to_image_bytes, save_binary_file, png_to_tiff_16bit


def process_with_gemini(median_flatfield, prompt="Analyze this image and generate a mask highlighting important features."):
    """使用 Gemini (Nano Banana Pro) 处理 median flat field 并获取遮罩"""
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )
    
    # 将median flat field转换为图像字节（8位PNG）
    image_bytes = numpy_to_image_bytes(median_flatfield, format='PNG')
    
    model = "gemini-3-pro-image-preview"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(text=prompt),
                types.Part(
                    inline_data=types.Blob(
                        mime_type="image/png",
                        data=image_bytes,
                    )
                ),
            ],
        ),
    ]
    tools = [
        types.Tool(googleSearch=types.GoogleSearch(
        )),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_modalities=[
            "IMAGE",
            "TEXT",
        ],
        image_config=types.ImageConfig(
            image_size="2K",
        ),
        tools=tools,
    )
    
    print("Sending median flat field to Gemini (Nano Banana Pro)...")
    file_index = 0
    mask_files_png = []
    mask_files_tiff = []
    
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if (
            chunk.candidates is None
            or chunk.candidates[0].content is None
            or chunk.candidates[0].content.parts is None
        ):
            continue
        if chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data:
            file_name = f"mask_{file_index}"
            file_index += 1
            inline_data = chunk.candidates[0].content.parts[0].inline_data
            data_buffer = inline_data.data
            file_extension = mimetypes.guess_extension(inline_data.mime_type)
            if file_extension is None:
                file_extension = ".png"
            full_file_name_png = f"{file_name}{file_extension}"
            save_binary_file(full_file_name_png, data_buffer)
            mask_files_png.append(full_file_name_png)
            
            # 将PNG转回16位TIFF
            full_file_name_tiff = f"{file_name}.tiff"
            png_to_tiff_16bit(full_file_name_png, full_file_name_tiff, original_shape=median_flatfield.shape)
            mask_files_tiff.append(full_file_name_tiff)
        else:
            if chunk.text:
                print(chunk.text, end="")
    
    print(f"\nReceived {len(mask_files_png)} mask file(s) from Gemini (Nano Banana Pro)")
    return mask_files_tiff


def generate_inpainted_image(median_flatfield, expanded_mask, prompt=None):
    """
    使用 Gemini (Nano Banana Pro) 生成 inpainted 图像（去除 dust）
    Args:
        median_flatfield: 原始 flat field 图像
        expanded_mask: 扩展后的 mask（0-1之间）
        prompt: 可选的 prompt，如果为 None 则使用默认 prompt
    """
    if prompt is None:
        prompt = """Your task is to perform high-precision inpainting on a CMOS sensor flat field image to remove dust shadows.

CONTEXT:
1. Original Image: A raw flat field containing dark spots caused by dust particles on the sensor glass.
2. Mask Image: A guidance map where white areas (value 1) represent regions with dust shadows, and black areas (value 0) are clean areas.

GOAL:
Reconstruct the underlying sensor response within the masked (white) regions. The goal is to make the dust shadows completely disappear as if they were never there.

INSTRUCTIONS:
- Analyze the content (solar? planet? moon? etc.) and the textures in the clean (black) areas surrounding each masked region.
- Fill the masked regions with a smooth, natural reconstruction that perfectly interpolates the surrounding intensity and gradient.
- The transition between the inpainted area and the original area needs to be mathematically seamless.
- Ensure the total removal of all dark artifacts within the mask. The resulting image should look like a perfect, clean sensor response.
"""
    
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )
    
    # 将median flat field转换为图像字节（8位PNG）
    image_bytes = numpy_to_image_bytes(median_flatfield, format='PNG')
    
    # 将expanded mask转换为图像字节（8位PNG）
    # mask需要归一化到0-1，然后转换为0-255
    mask_normalized = np.clip(expanded_mask, 0.0, 1.0)
    mask_8bit = (mask_normalized * 255.0).astype(np.uint8)
    mask_bytes = numpy_to_image_bytes(mask_8bit, format='PNG')
    
    model = "gemini-3-pro-image-preview"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(text=prompt),
                types.Part(
                    inline_data=types.Blob(
                        mime_type="image/png",
                        data=image_bytes,
                    )
                ),
                types.Part(
                    inline_data=types.Blob(
                        mime_type="image/png",
                        data=mask_bytes,
                    )
                ),
            ],
        ),
    ]
    tools = [
        types.Tool(googleSearch=types.GoogleSearch(
        )),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_modalities=[
            "IMAGE",
            "TEXT",
        ],
        image_config=types.ImageConfig(
            image_size="2K",
        ),
        tools=tools,
    )
    
    print("Sending median flat field to Gemini (Nano Banana Pro) for inpainting...")
    file_index = 0
    inpainted_files_png = []
    inpainted_files_tiff = []
    
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if (
            chunk.candidates is None
            or chunk.candidates[0].content is None
            or chunk.candidates[0].content.parts is None
        ):
            continue
        if chunk.candidates[0].content.parts[0].inline_data and chunk.candidates[0].content.parts[0].inline_data.data:
            file_name = f"inpainted_{file_index}"
            file_index += 1
            inline_data = chunk.candidates[0].content.parts[0].inline_data
            data_buffer = inline_data.data
            file_extension = mimetypes.guess_extension(inline_data.mime_type)
            if file_extension is None:
                file_extension = ".png"
            full_file_name_png = f"{file_name}{file_extension}"
            save_binary_file(full_file_name_png, data_buffer)
            inpainted_files_png.append(full_file_name_png)
            
            # 将PNG转回16位TIFF
            full_file_name_tiff = f"{file_name}.tiff"
            png_to_tiff_16bit(full_file_name_png, full_file_name_tiff, original_shape=median_flatfield.shape)
            inpainted_files_tiff.append(full_file_name_tiff)
        else:
            if chunk.text:
                print(chunk.text, end="")
    
    print(f"\nReceived {len(inpainted_files_png)} inpainted image(s) from Gemini (Nano Banana Pro)")
    return inpainted_files_tiff
