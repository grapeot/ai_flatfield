# AI-FlatField: Smart Sensor Dust Detection & Calibration

[中文版](./README.md) | [**Deep Dive (Blog Post)**](https://yage.ai/ai-flat-field-en.html)

AI-FlatField is an automated sensor dust detection and flat-field correction tool designed specifically for astrophotography. It bridges the gap between the visual reasoning of Google Gemini AI (Nano Banana Pro) and the scientific rigor of mathematical calibration, effectively solving the "dust donut" problem even in extreme conditions (e.g., high focal ratio solar imaging).

## Philosophy: AI for the "Eye," Math for the "Hand"

When dealing with sensor dust, we often face a trade-off:
*   **Traditional Algorithms (e.g., KLL)**: Physics-based and safe, but "blind." They struggle to distinguish dust from solar features, especially in poor seeing conditions.
*   **End-to-End Generative AI**: Incredibly "sharp-eyed" at detection but "slippery-handed." Pure AI outputs often introduce hallucinations (imaginary textures) or subtle luminance shifts, which compromise scientific integrity.

**The core philosophy of this project is to decouple the two: use AI as the "Eye" to locate dust and infer obscured signals, while using deterministic Math as the "Hand" to perform the actual calibration, strictly limiting changes to affected areas.**

## The Workflow

The tool implements a hybrid "AI-as-Middleware" workflow:

1.  **Temporal Median Extraction**: Extract frames from a video stream (SER file) and compute a temporal median. While this isolates static features, it often retains low-frequency solar structures.
2.  **AI Dust Localization (The Eye)**: The median image is sent to Gemini (Nano Banana Pro). The AI generates a dust mask with precision far exceeding manual annotation. This mask alone is scientifically valuable for data exclusion.
3.  **AI Signal Inference (Inpainting)**: Leveraging its contextual understanding, the AI infers what the sensor response *would have been* without the dust, creating a clean reference.
4.  **Synthetic Flat Field Generation (The Hand)**: To ensure scientific validity, we don't use the AI's direct output. Instead, we synthesize a "Synthetic Flat Field" using the formula:
    `final_flatfield = (1 - mask) * 1.0 + mask * (median_flatfield / inpainted)`
    *   In **clean areas**, the correction factor is strictly **1.0**, ensuring original data is 100% preserved with zero AI interference.
    *   In **dusty areas**, the tool compensates for intensity loss based on AI inference.
5.  **Histogram Matching**: A crucial normalization step ensures that global luminance shifts introduced during AI generation are eliminated before synthesis.

## Result Showcase

| Median Flat Field (Original) | AI-Generated Dust Mask |
| :---: | :---: |
| ![Median Flat Field](./imgs/median_flatfield.jpg) | ![Mask](./imgs/mask_0.jpg) |
| **AI Inpainting (Inference)** | **Final Synthetic Flat Field** |
| ![Inpainted Image](./imgs/inpainted_0.jpg) | ![Final Flat Field](./imgs/final_flatfield.jpg) |

## How to Use

### 1. Prerequisites

We recommend using [uv](https://github.com/astral-sh/uv) for environment management. Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file in the project root and add your Google Gemini API key:

```bash
GEMINI_API_KEY=your_actual_gemini_api_key
```
*(Get your key at: [Google AI Studio](https://aistudio.google.com/app/apikey))*

### 3. Execution

Place your `.ser` file in the directory and run:

```bash
python main.py --input your_filename.ser
```

The program runs in an interactive wizard mode. You can preview and confirm AI results at each stage. If a specific AI inference isn't perfect, press **'R'** to re-roll and generate a new version.

### 4. Calibration in PixInsight

The output `final_flatfield.tiff` is a 16-bit image (65535 maps to 1.0). You can:
*   Apply it directly in **PixelMath** using `$T / final_flatfield`.
*   Use it as a Flat Field in the **Image Calibration** process.

## Project Structure

*   `main.py`: Orchestrates the interactive workflow.
*   `gemini_client.py`: Handles Gemini (Nano Banana Pro) detection and inpainting logic.
*   `flatfield.py`: Core mathematical operations (median, synthesis, histogram matching).
*   `ser_reader.py`: Efficient SER file handling.
*   `mask_processing.py`: Mask dilation and blurring.

## Further Reading

For more on the reasoning behind this project, comparative experiments, and why this hybrid approach is the future of scientific imaging, read the blog post:
👉 [**AI-Assisted Astrophotography: Removing Sensor Dust with Generative Models**](https://yage.ai/ai-flat-field-en.html)
