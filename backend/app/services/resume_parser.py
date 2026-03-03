"""Resume parsing service using OpenAI for intelligent extraction."""

import io
import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Minimum characters to consider text extraction successful
MIN_TEXT_LENGTH = 50


@dataclass
class Experience:
    """Work experience entry."""

    company: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    location: str | None = None


@dataclass
class Education:
    """Education entry."""

    school: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@dataclass
class ResumeData:
    """Structured resume data extracted from a resume file."""

    full_name: str | None = None
    headline: str | None = None
    bio: str | None = None
    location: str | None = None
    company: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    email: str | None = None
    phone: str | None = None
    skills: list[str] = field(default_factory=list)
    profile_one_liner: str | None = None
    profile_summary: str | None = None
    experiences: list[dict] | None = None
    education: list[dict] | None = None
    raw_text: str | None = None


class ResumeParser:
    """Parse resumes and extract structured data using OpenAI."""

    def __init__(self, openai_api_key: str | None = None):
        """Initialize the parser with optional OpenAI API key."""
        self.openai_api_key = openai_api_key

    def parse(self, file_content: bytes, filename: str) -> ResumeData:
        """Parse resume file and extract structured data."""
        text = self._extract_text(file_content, filename)

        if self.openai_api_key:
            return self._parse_with_ai(text)
        else:
            return self._parse_with_regex(text)

    def _extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from PDF or DOCX file."""
        filename_lower = filename.lower()

        if filename_lower.endswith(".pdf"):
            return self._extract_from_pdf(file_content)
        elif filename_lower.endswith(".docx"):
            return self._extract_from_docx(file_content)
        else:
            raise ValueError(f"Unsupported file type: {filename}")

    def _extract_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF using pdfplumber, with OCR fallback for image-based PDFs."""
        text = self._extract_pdf_text(file_content)

        if len(text.strip()) < MIN_TEXT_LENGTH:
            logger.info("PDF text extraction returned minimal text, attempting OCR...")
            ocr_text = self._extract_pdf_with_ocr(file_content)
            if len(ocr_text.strip()) > len(text.strip()):
                return ocr_text

        return text

    def _extract_pdf_text(self, file_content: bytes) -> str:
        """Extract text from PDF using pdfplumber (text-based PDFs)."""
        try:
            import pdfplumber

            text_parts = []
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n".join(text_parts)
        except ImportError:
            logger.warning("pdfplumber not installed, returning empty text")
            return ""
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""

    def _extract_pdf_with_ocr(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF using OCR (for image-based/scanned PDFs)."""
        try:
            import pytesseract
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(pdf_bytes, dpi=300)

            text_parts = []
            for i, image in enumerate(images):
                logger.debug(f"Running OCR on page {i + 1}/{len(images)}")
                page_text = pytesseract.image_to_string(image)
                if page_text.strip():
                    text_parts.append(page_text)

            return "\n".join(text_parts)

        except ImportError as e:
            logger.warning(f"OCR dependencies not installed: {e}")
            logger.info("Install with: pip install pytesseract pdf2image pillow")
            return ""
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

    def _extract_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX using python-docx."""
        try:
            from docx import Document

            doc = Document(io.BytesIO(file_content))
            text_parts = [para.text for para in doc.paragraphs if para.text]
            return "\n".join(text_parts)
        except ImportError:
            logger.warning("python-docx not installed, returning empty text")
            return ""
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            return ""

    def _parse_with_ai(self, text: str) -> ResumeData:
        """Parse resume text using OpenAI API."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.openai_api_key)

            system_prompt = (
                "You are an expert resume parser. "
                "Extract structured information from resumes accurately. "
                "Always return valid JSON. Be precise with names, dates, and company names. "
                "For graduation_year, always return an integer (e.g., 2024) or null. "
                "Generate professional summaries based on actual resume content."
            )

            user_prompt = f"""Extract information from this resume and return a JSON object.

REQUIRED FIELDS (you MUST generate these based on the resume):
- full_name: The person's full legal name exactly as written
- headline: Professional headline like "Software Engineer at Google"
- bio: 2-3 sentence professional summary of their background and expertise
- profile_one_liner: One memorable sentence capturing their professional identity
- profile_summary: 2-3 compelling sentences highlighting key achievements

EXTRACTED FIELDS (use null if not found):
- company: Current or most recent employer name
- major: Field of study (e.g., "Computer Science", "Mechanical Engineering")
- graduation_year: Year of graduation as INTEGER (e.g., 2024), not string
- location: City, State or City, Country format
- email: Email address
- phone: Phone number in original format
- skills: Array of up to 10 technical skills mentioned

STRUCTURED DATA (arrays, use empty array [] if none found):
- experiences: Array of {{company, title, start_date, end_date, description, location}}
- education: Array of {{school, degree, field_of_study, start_date, end_date}}

Date formats: Use "YYYY" for years, "Month YYYY" for specific dates, "Present" for current.

RESUME TEXT:
{text[:8000]}

Return ONLY valid JSON, no markdown code blocks or explanations."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                logger.warning("Empty response from OpenAI")
                return self._parse_with_regex(text)

            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n?", "", content)
                content = re.sub(r"\n?```$", "", content)

            data = json.loads(content)

            # Validate and convert graduation_year to int
            grad_year = data.get("graduation_year")
            if grad_year is not None:
                try:
                    grad_year = int(grad_year)
                    if not (1900 <= grad_year <= 2100):
                        grad_year = None
                except (ValueError, TypeError):
                    grad_year = None

            # Ensure skills is a list
            skills = data.get("skills")
            if not isinstance(skills, list):
                skills = []

            # Ensure experiences and education are lists
            experiences = data.get("experiences")
            if not isinstance(experiences, list):
                experiences = []

            education = data.get("education")
            if not isinstance(education, list):
                education = []

            return ResumeData(
                full_name=self._sanitize_string(data.get("full_name")),
                headline=self._sanitize_string(data.get("headline")),
                bio=self._sanitize_string(data.get("bio")),
                location=self._sanitize_string(data.get("location")),
                company=self._sanitize_string(data.get("company")),
                major=self._sanitize_string(data.get("major")),
                graduation_year=grad_year,
                email=self._sanitize_string(data.get("email")),
                phone=self._sanitize_string(data.get("phone")),
                skills=skills,
                profile_one_liner=self._sanitize_string(data.get("profile_one_liner")),
                profile_summary=self._sanitize_string(data.get("profile_summary")),
                experiences=experiences,
                education=education,
                raw_text=text,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            return self._parse_with_regex(text)
        except Exception as e:
            logger.error(f"OpenAI parsing failed: {e}")
            return self._parse_with_regex(text)

    def _sanitize_string(self, value: str | None) -> str | None:
        """Sanitize string values - strip whitespace and return None for empty strings."""
        if value is None:
            return None
        if not isinstance(value, str):
            return str(value) if value else None
        value = value.strip()
        return value if value else None

    def _parse_with_regex(self, text: str) -> ResumeData:
        """Fallback regex-based parsing when OpenAI is not available."""
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        phone_match = re.search(r"(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", text)

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        full_name = lines[0] if lines else None

        return ResumeData(
            full_name=full_name,
            email=email_match.group(0) if email_match else None,
            phone=phone_match.group(1) if phone_match else None,
            raw_text=text,
        )
