"""Resume parsing service using OpenAI for intelligent extraction."""

import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


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
        """Extract text from PDF using pdfplumber."""
        try:
            import io

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

    def _extract_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX using python-docx."""
        try:
            import io

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

            prompt = (
                "Extract the following information from this resume."
                " Return a JSON object with these fields:\n\n"
                "REQUIRED FIELDS (always generate these):\n"
                "- full_name: The person's full name\n"
                "- headline: A short professional headline combining role and company"
                ' (e.g., "Computer Engineering Student at Purdue University")\n'
                "- bio: A 2-3 sentence professional summary based on their experience\n"
                "- profile_one_liner: A catchy, memorable one-line description"
                ' (e.g., "Engineering student with Fortune 500 experience")\n'
                "- profile_summary: A compelling 2-3 sentence summary highlighting"
                " key achievements, technical skills, and what makes them stand out."
                " Be specific about accomplishments and impact.\n\n"
                "OTHER FIELDS:\n"
                "- company: Current or most recent company\n"
                "- major: Field of study/major\n"
                "- graduation_year: Year of graduation (as integer)\n"
                "- location: City, State or City, Country\n"
                "- email: Email address\n"
                "- phone: Phone number\n"
                "- skills: Array of top 5 technical skills\n"
                "- experiences: Array of work experiences, each with:"
                " {company, title, start_date, end_date, description, location}\n"
                "- education: Array of education entries, each with:"
                " {school, degree, field_of_study, start_date, end_date}\n\n"
                "IMPORTANT: You MUST generate headline, bio, profile_one_liner,"
                " and profile_summary based on the resume content."
                " Never return null for these fields.\n"
                "For other fields, use null if not found.\n"
                "For dates, use format like '2023' or 'May 2023' or 'Present'.\n\n"
                f"Resume text:\n{text[:4000]}\n\n"
                "Return only valid JSON, no markdown or explanation."
            )

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
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

            return ResumeData(
                full_name=data.get("full_name"),
                headline=data.get("headline"),
                bio=data.get("bio"),
                location=data.get("location"),
                company=data.get("company"),
                major=data.get("major"),
                graduation_year=data.get("graduation_year"),
                email=data.get("email"),
                phone=data.get("phone"),
                skills=data.get("skills", []),
                profile_one_liner=data.get("profile_one_liner"),
                profile_summary=data.get("profile_summary"),
                experiences=data.get("experiences"),
                education=data.get("education"),
                raw_text=text,
            )

        except Exception as e:
            logger.error(f"OpenAI parsing failed: {e}")
            return self._parse_with_regex(text)

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
