"""
OCR Module
Handles scanned PDFs and receipt images using Claude Vision.
"""
import base64
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
import anthropic

SUPPORTED_IMAGES = {'.jpg', '.jpeg', '.png', '.heic', '.webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using pypdf."""
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()


def is_scanned_pdf(pdf_path: Path) -> bool:
    """Check if PDF is scanned (image-based) vs text-based."""
    try:
        text = extract_text_from_pdf(pdf_path)
        return len(text.strip()) == 0
    except Exception:
        return True


def is_supported_image(file_path: Path) -> bool:
    """Check if file is a supported image format."""
    return file_path.suffix.lower() in SUPPORTED_IMAGES


def validate_image_size(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Validate image file size."""
    try:
        size = file_path.stat().st_size
        if size > MAX_FILE_SIZE:
            return False, f"File size {size / 1024 / 1024:.1f}MB exceeds maximum 10MB"
        return True, None
    except Exception as e:
        return False, str(e)


def convert_heic_to_jpeg(heic_path: Path) -> Path:
    """Convert HEIC image to JPEG."""
    try:
        import pillow_heif
        from PIL import Image
        heif_file = pillow_heif.read_heif(heic_path)
        image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
        jpeg_path = heic_path.with_suffix('.jpg')
        image.save(jpeg_path, "JPEG", quality=95)
        return jpeg_path
    except Exception as e:
        raise ValueError(f"Failed to convert HEIC: {e}")


def encode_image_base64(image_path: Path) -> str:
    """Encode image to base64 for Claude API."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def get_image_media_type(image_path: Path) -> str:
    """Get media type for image."""
    suffix = image_path.suffix.lower()
    media_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp', '.heic': 'image/jpeg'}
    return media_types.get(suffix, 'image/jpeg')


def process_image_with_vision(image_path: Path, prompt: str) -> str:
    """Process an image using Claude Vision API."""
    client = anthropic.Anthropic()
    if image_path.suffix.lower() == '.heic':
        image_path = convert_heic_to_jpeg(image_path)
    image_data = encode_image_base64(image_path)
    media_type = get_image_media_type(image_path)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
            {"type": "text", "text": prompt}
        ]}]
    )
    return message.content[0].text


def process_receipt(image_path: Path) -> Dict:
    """Process a receipt photo and extract transaction data."""
    valid, error = validate_image_size(image_path)
    if not valid:
        return {"error": "file_size", "message": error, "needs_manual_review": True}
    if not is_supported_image(image_path):
        return {"error": "unsupported_format", "message": f"Unsupported format: {image_path.suffix}"}

    prompt = '''Analyze this receipt image and extract transaction details.
Return JSON: {"merchant": "...", "date": "YYYY-MM-DD", "total": 123.45, "currency": "HKD", "items": [{"name": "...", "price": 10.00}], "confidence": "high/medium/low"}
If too blurry/dark: {"error": "image_quality", "suggestion": "Retake photo with better lighting"}
Return ONLY JSON.'''

    try:
        response = process_image_with_vision(image_path, prompt)
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]
        else:
            json_str = response
        result = json.loads(json_str.strip())
        result["source_file"] = str(image_path.name)
        return result
    except json.JSONDecodeError:
        return {"error": "parse_error", "raw_response": response, "needs_manual_review": True}
    except Exception as e:
        return {"error": "processing_error", "message": str(e), "needs_manual_review": True}


def process_scanned_pdf(pdf_path: Path) -> Dict:
    """Process a scanned PDF using Claude Vision."""
    try:
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, first_page=1, last_page=5)
        except ImportError:
            return {"error": "dependency_missing", "message": "pdf2image required. Install with: pip install pdf2image", "needs_manual_review": True}

        if not images:
            return {"error": "no_pages", "needs_manual_review": True}

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            images[0].save(tmp.name, 'JPEG')
            tmp_path = Path(tmp.name)

        from .config import CATEGORIES
        prompt = f'''This is a scanned bank statement. Extract all transactions.
For each: date (YYYY-MM-DD), description, amount (positive=income, negative=expense), currency, category ({", ".join(CATEGORIES)}).
Also: account_type, institution_name, statement period.
Return JSON: {{"statement_info": {{"period_start": "...", "period_end": "...", "account_type": "...", "institution_name": "...", "currency": "HKD"}}, "transactions": [...]}}'''

        response = process_image_with_vision(tmp_path, prompt)
        tmp_path.unlink()

        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0]
        else:
            json_str = response
        result = json.loads(json_str.strip())
        result["source_file"] = str(pdf_path.name)
        result["ocr_processed"] = True
        return result
    except Exception as e:
        return {"error": "ocr_failed", "message": str(e), "needs_manual_review": True}
