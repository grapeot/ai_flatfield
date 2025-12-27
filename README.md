# AI 平场校准工具 (AI Flat Field Correction)

[English version](./README_en.md)

这是一个利用 Google Gemini AI 强大能力，专门为天文摄影设计的传感器灰尘自动检测与平场校准工具。

## 动机 (Motivation)

在天文摄影中，传感器表面的灰尘会在图像中产生暗斑，严重影响成片质量。传统的平场校准虽然能解决大部分问题，但当平场本身由于光学系统变化或灰尘移动而不再准确时，处理起来非常麻烦。

本项目旨在通过 AI 的图像理解能力，自动识别传感器上的灰尘，并利用最先进的 Inpainting（图像修复）技术生成“理想”的无灰尘平场，从而实现更精准、更智能的图像校准。

## 主要算法 (Key Algorithms)

本项目采用了一套结合传统图像处理与现代大模型 AI 的复合算法：

1.  **中值平场计算 (Median Flat Field)**: 从视频流（SER文件）中提取所有帧，并在时间维度上计算中位数。这能有效消除宇宙射线、热噪声等随机干扰，提取出纯净的静态平场和灰尘特征。
2.  **AI 灰尘检测 (AI Dust Detection)**: 将平场发送给 Gemini AI，利用其视觉能力识别尘埃、污点等传感器瑕疵，生成精准的初始遮罩 (Mask)。
3.  **遮罩柔性扩展 (Mask Expansion)**: 对 AI 生成的遮罩进行 10 像素的二值膨胀 (Binary Dilation) 并配合高斯模糊 (Gaussian Blur)，确保遮罩能完美覆盖灰尘边缘，并在混合时实现自然过渡。
4.  **AI 图像修复 (AI Inpainting)**: 再次调用 Gemini，传入原图和扩展后的遮罩，要求其仅在遮罩区域内进行修复，填补灰尘覆盖的细节，生成一张“洁净”的参考图。
5.  **直方图匹配 (Histogram Matching)**: 这是关键的一步。由于 AI 在生成图像时可能会产生细微的整体亮度偏移，我们通过对非遮罩区域 (mask=0) 进行直方图匹配，将修复后的图像精准地映射回原图的亮度空间。
6.  **最终平场合成 (Final Blending)**: 基于公式 `final_flatfield = (1 - mask) * 1.0 + mask * (median_flatfield / inpainted)` 合成。这样在干净区域，校正因子严格为 1.0；在灰尘区域，则能精准补偿光强损失。

## 结果展示 (Result Showcase)

以下是处理流程中的关键节点图像：

| 原始中值平场 (Median Flat Field) | 灰尘检测遮罩 (Dust Mask) |
| :---: | :---: |
| ![Median Flat Field](./imgs/median_flatfield.jpg) | ![Mask](./imgs/mask_0.jpg) |
| **AI 修复结果 (Inpainted Image)** | **最终校正因子 (Final Flat Field)** |
| ![Inpainted Image](./imgs/inpainted_0.jpg) | ![Final Flat Field](./imgs/final_flatfield.jpg) |

## 使用方法 (How to Use)

### 1. 环境准备

安装 Python 3.10+ 及相关依赖：

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

本项目需要 Google Gemini API 支持。请在项目根目录下创建 `.env` 文件（可参考 `.env.example`）：

```bash
GEMINI_API_KEY=你的_GEMINI_API_KEY
```

你可以从 [Google AI Studio](https://aistudio.google.com/app/apikey) 获取免费的 API Key。

### 3. 运行程序

将你的 `.ser` 文件放入项目目录，并修改 `main.py` 中的 `ser_file` 变量名，然后执行：

```bash
python main.py
```

程序将以向导模式运行，你可以在每个关键阶段通过弹出窗口预览结果：
*   **Step 1**: 确认中值平场。
*   **Step 2**: 确认 AI 识别的灰尘遮罩。
*   **Step 4**: 预览 AI 修复效果。如果效果不佳，按 **'R'** 键可重新“抽卡”生成。
*   **Step 5**: 生成最终的 `final_flatfield.tiff`。

### 4. 在 PixInsight 中使用

生成的 `final_flatfield.tiff` 是 16 位 uint16 格式，其中值 65535 对应 1.0。在 PixInsight 的 PixelMath 中，你可以使用如下公式校正你的原始图像：

```javascript
$T / (final_flatfield / 65535)
```

## 项目结构 (Project Structure)

*   `main.py`: 主程序入口，管理交互流程。
*   `ser_reader.py`: 高效读取 SER 文件头及帧数据。
*   `flatfield.py`: 负责中值计算、直方图匹配等核心数学运算。
*   `gemini_client.py`: 封装 Gemini API 的调用逻辑（检测与修复）。
*   `mask_processing.py`: 处理遮罩的膨胀、模糊与平滑。
*   `image_utils.py`: 包含图像缩放、格式转换及 OpenCV 显示等工具。

## 注意事项 (Notes)

*   **内存使用**: SER 文件所有帧会加载到内存中进行中值计算，请确保你的 RAM 足够（或减小 frame count）。
*   **幂等性**: 脚本会自动跳过已生成的中间文件，方便断点调试。如果需要重新生成，请先删除对应的 `.tiff` 文件。
