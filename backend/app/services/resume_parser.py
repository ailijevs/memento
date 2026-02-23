"""
Resume parsing service.
Extracts structured data from PDF and DOCX resumes.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import BinaryIO

logger = logging.getLogger(__name__)


@dataclass
class ResumeData:
    """Structured data extracted from a resume."""

    full_name: str | None = None
    headline: str | None = None
    bio: str | None = None
    company: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    location: str | None = None
    email: str | None = None
    phone: str | None = None
    skills: list[str] | None = None
    raw_text: str | None = None


class ResumeParser:
    """Parse resumes and extract structured data."""

    def __init__(self, openai_api_key: str | None = None):
        self.openai_api_key = openai_api_key

    async def parse(self, file: BinaryIO, filename: str) -> ResumeData:
        """
        Parse a resume file and extract structured data.

        Args:
            file: File-like object containing the resume
            filename: Original filename (used to determine file type)

        Returns:
            ResumeData with extracted information
        """
        # Extract text based on file type
        if filename.lower().endswith(".pdf"):
            text = self._extract_text_from_pdf(file)
        elif filename.lower().endswith((".docx", ".doc")):
            text = self._extract_text_from_docx(file)
        else:
            raise ValueError(f"Unsupported file type: {filename}")

        logger.info(f"Extracted {len(text)} characters from resume")

        # Parse the text
        if self.openai_api_key:
            return await self._parse_with_ai(text)
        else:
            return self._parse_with_patterns(text)

    def _extract_text_from_pdf(self, file: BinaryIO) -> str:
        """Extract text from a PDF file."""
        import io

        import pdfplumber

        text_parts = []
        raw = file.read()
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n".join(text_parts)

    def _extract_text_from_docx(self, file: BinaryIO) -> str:
        """Extract text from a DOCX file."""
        from docx import Document

        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs])

    def _parse_with_patterns(self, text: str) -> ResumeData:
        """
        Parse resume text using pattern matching.
        This is a fallback when OpenAI is not available.
        """
        data = ResumeData(raw_text=text[:2000])  # Store first 2000 chars

        # Extract email
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        if email_match:
            data.email = email_match.group()

        # Extract phone
        phone_match = re.search(r"(\+?1?[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
        if phone_match:
            data.phone = phone_match.group()

        # Extract name (usually at the top, first line that looks like a name)
        lines = text.strip().split("\n")
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            # Name heuristic: 2-4 capitalized words, no special chars
            if re.match(r"^[A-Z][a-z]+(\s+[A-Z][a-z]+){1,3}$", line):
                data.full_name = line
                break

        # Extract graduation year
        year_match = re.search(r"(20\d{2}|19\d{2})", text)
        if year_match:
            year = int(year_match.group())
            if 2000 <= year <= 2030:  # Reasonable graduation year range
                data.graduation_year = year

        # Extract education/major keywords
        education_keywords = [
            "Computer Science",
            "Electrical Engineering",
            "Mechanical Engineering",
            "Business",
            "Economics",
            "Mathematics",
            "Physics",
            "Biology",
            "Chemistry",
            "Psychology",
            "Engineering",
            "Data Science",
            "Information Technology",
        ]
        for keyword in education_keywords:
            if keyword.lower() in text.lower():
                data.major = keyword
                break

        # Extract company (look for "at" or common company patterns)
        company_patterns = [
            r"(?:at|@)\s+([A-Z][A-Za-z\s&]+(?:Inc|LLC|Corp|Company)?)",
            r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)"
            r"\s*[-–]\s*(?:Intern|Engineer|Developer|Analyst)",
        ]
        for pattern in company_patterns:
            match = re.search(pattern, text)
            if match:
                data.company = match.group(1).strip()
                break

        # Create a headline from extracted info
        if data.major:
            data.headline = f"{data.major} Student"
            if data.company:
                data.headline += f" | Previously at {data.company}"

        return data

    async def _parse_with_ai(self, text: str) -> ResumeData:
        """
        Parse resume text using OpenAI for intelligent extraction.
        """
        from openai import OpenAI

        client = OpenAI(api_key=self.openai_api_key)

        prompt = (
            "Extract the following information from this resume."
            " Return a JSON object with these fields:\n"
            "- full_name: The person's full name\n"
            "- headline: A short professional headline"
            ' (e.g., "Software Engineer at Google")\n'
            "- bio: A brief 1-2 sentence professional summary\n"
            "- company: Current or most recent company\n"
            "- major: Field of study/major\n"
            "- graduation_year: Year of graduation (as integer)\n"
            "- location: City, State or City, Country\n"
            "- email: Email address\n"
            "- phone: Phone number\n"
            "- skills: Array of top 5 technical skills\n\n"
            "If a field cannot be determined, use null.\n\n"
            f"Resume text:\n{text[:4000]}\n\n"
            "Return only valid JSON, no markdown or explanation."
        )

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )

            result_text = response.choices[0].message.content
            if result_text is None:
                return self._parse_with_patterns(text)
            result_text = result_text.strip()
            if result_text.startswith("```"):
                result_text = re.sub(r"```json?\n?", "", result_text)
                result_text = result_text.rstrip("`")

            parsed = json.loads(result_text)

            return ResumeData(
                full_name=parsed.get("full_name"),
                headline=parsed.get("headline"),
                bio=parsed.get("bio"),
                company=parsed.get("company"),
                major=parsed.get("major"),
                graduation_year=parsed.get("graduation_year"),
                location=parsed.get("location"),
                email=parsed.get("email"),
                phone=parsed.get("phone"),
                skills=parsed.get("skills"),
                raw_text=text[:2000],
            )

        except Exception as e:
            logger.error(f"AI parsing failed: {e}, falling back to patterns")
            return self._parse_with_patterns(text)
