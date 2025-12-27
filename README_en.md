# AI-Powered Flat Field Correction Tool

[中文版](./README.md)

An automated sensor dust detection and flat-field correction suite leveraging the power of Google Gemini AI, specifically engineered for astrophotography.

## Motivation

In astrophotography, dust particles on the sensor surface create unsightly dark spots (donuts), which can significantly degrade image quality. While traditional flat-field calibration is standard practice, it becomes increasingly cumbersome when calibration frames themselves are inaccurate or when dust shifts during an imaging session.

This project aims to automate dust identification using advanced AI vision models and generate "ideal," dust-free reference frames via state-of-the-art inpainting techniques. This ensures a smarter, more precise calibration workflow for astronomical data.

## Key Algorithms

The tool implements a sophisticated pipeline combining traditional digital image processing with modern Large Language Model (LLM) capabilities:

1.  **Median Flat Field Computation**: Frames are extracted from a video stream (SER file), and a median is calculated along the temporal dimension. This effectively eliminates transient signals like cosmic rays or sensor noise, isolating the pure static flat field and dust characteristics.
2.  **AI Dust Detection**: The median flat field is sent to the Gemini AI model. Leveraging its visual reasoning, the model identifies sensor defects such as dust and smudges, generating a high-precision initial mask.
3.  **Soft Mask Expansion**: The AI-generated mask undergoes a 10-pixel binary dilation followed by a Gaussian blur. This ensures the mask fully encapsulates the dust edges and facilitates a seamless, natural transition during the blending phase.
4.  **AI Inpainting**: A second call to Gemini is made, providing both the original image and the expanded mask. The model is tasked with inpainting *only* within the masked regions, reconstructing the obscured details to create a "clean" reference image.
5.  **Histogram Matching**: A critical normalization step. Since generative models can introduce slight global luminance shifts, we perform histogram matching on the unmasked regions (mask=0) to map the inpainted result precisely back into the original image's intensity space.
6.  **Final Synthesis**: The correction factor is synthesized using the formula: `final_flatfield = (1 - mask) * 1.0 + mask * (median_flatfield / inpainted)`. This ensures that "clean" areas remain untouched (factor exactly 1.0), while dust-affected regions receive precise intensity compensation.

## Result Showcase

Below are the key milestones in the processing pipeline:

| Median Flat Field (Original) | AI-Generated Dust Mask |
| :---: | :---: |
| ![Median Flat Field](./imgs/median_flatfield.jpg) | ![Mask](./imgs/mask_0.jpg) |
| **AI-Inpainted Result (Clean)** | **Final Correction Factor** |
| ![Inpainted Image](./imgs/inpainted_0.jpg) | ![Final Flat Field](./imgs/final_flatfield.jpg) |

## How to Use

### 1. Prerequisites

Install Python 3.10+ and the required dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

This project requires access to the Google Gemini API. Create a `.env` file in the project root (refer to `.env.example`):

```bash
GEMINI_API_KEY=your_actual_gemini_api_key
```

You can obtain a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 3. Execution

Place your `.ser` file in the project directory, update the `ser_file` variable in `main.py` accordingly, and run:

```bash
python main.py
```

The program operates in an interactive wizard mode, allowing you to preview results at every stage:
*   **Step 1**: Confirm the median flat field.
*   **Step 2**: Review the AI-identified dust mask.
*   **Step 4**: Preview the inpainting quality. If unsatisfactory, press **'R'** to retry and generate a new iteration.
*   **Step 5**: Generate the final `final_flatfield.tiff`.

### 4. Integration with PixInsight

The output `final_flatfield.tiff` is a 16-bit uint16 image where a value of 65535 corresponds to a factor of 1.0. You can apply this correction in PixInsight using PixelMath:

```javascript
$T / (final_flatfield / 65535)
```

## Project Structure

*   `main.py`: Main entry point managing the interactive workflow.
*   `ser_reader.py`: Efficient handling of SER headers and frame extraction.
*   `flatfield.py`: Core mathematical operations including median calculation and histogram matching.
*   `gemini_client.py`: API wrappers for Gemini AI (Detection & Inpainting).
*   `mask_processing.py`: Handling mask dilation, blurring, and smoothing.
*   `image_utils.py`: Utilities for scaling, format conversion, and OpenCV display.

## Notes

*   **Memory Usage**: All frames from the SER file are loaded into memory for median calculation. Ensure your system has sufficient RAM or limit the frame count.
*   **Idempotency**: The script automatically skips steps if intermediate files already exist. To force a re-run, delete the corresponding `.tiff` files.

