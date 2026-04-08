# Manual Test Report #007

| Field | Value |
|-------|-------|
| **Report ID** | MT-007 (or custom ID) |
| **Date** | 2026-03-16 |
| **Tester** | Will Ott |
| **Test Case ID** | MT-07 |
| **Requirement ID** | FR-1: Real-Time Face Recognition Pipeline |

---

## Test Steps

NOTE: Because the app was unavailable at the time of performing the test, the UI wasn't used and I opted for a file upload for testing using the following steps:

1. Find an image containing multiple persons that can be found for Rekognition, this image should be downloaded locally as jpg or jpeg.
2. Prepare the image as base64 using helper script.
    - Copy the local path of the saved .jpg or .jpeg image
    - In backend directory, run: python scripts/encode_data_jpg_to_base64.py --input "C:\path\to\photo.jpg"
3. Call the detect endpoint.
    - URL: POST http://<backend>/api/v1/recognition/detect
    - Body (JSON): {
                    "image_base64": "<base64 encoded .txt image>",
                    "event_id": "<default event_id>"
                    }
    - In Memento's API, paste the JSON in POST /api/v1/recognition/detect
4. Interpret the results to ensure available captured faces are accounted for with correct information provided.
    - matches: list of ProfileCard objects, there is one per recognized, allowed profile, not the total count of faces in the image
    - Faces with no enrolled match don't add rows; consent or missing profile can drop a match even if Rekognition matched a user_id
5. To avoid Type I and Type II errors (false positives and false negatives), repeat steps 1-4 four more times.

---

### Expected vs Actual Results

| Expected | Actual | Match? |
|----------|--------|--------|
| Return information for both Noddie and Sasha from provided picture | Return information for both Noddie and Sasha from provided picture | Yes |

---

### Outcome

- [x] **Pass**
- [ ] **Fail**

---

### Logs / Screenshots / Evidence

- Output:
{
  "matches": [
    {
      "user_id": "ab87fdd7-6941-48c9-904f-d60fdeaa55f5",
      "full_name": "Noddie Mgbodille",
      "headline": "Founder",
      "company": "Memento",
      "photo_path": "profiles/ab87fdd7-6941-48c9-904f-d60fdeaa55f5-onboarding.jpg",
      "profile_one_liner": "Builds backend and infrastructure systems.",
      "face_similarity": 96.3,
      "experience_similarity": null,
      "bio": null,
      "location": null,
      "major": "Computer Science",
      "graduation_year": 2026,
      "linkedin_url": null,
      "profile_summary": null,
      "experiences": [],
      "education": []
    },
    {
      "user_id": "c96ffe68-01df-4823-83f9-dded98fae363",
      "full_name": "Aleksandar (Sasha) Ilijevski",
      "headline": "Computer Engineering Student at Purdue University",
      "company": "acuvity",
      "photo_path": "profiles/c96ffe68-01df-4823-83f9-dded98fae363-onboarding.jpg",
      "profile_one_liner": "Computer Engineering student at Purdue University with expertise in AI security platforms and startup leadership.",
      "face_similarity": 94.8,
      "experience_similarity": null,
      "bio": "Computer engineering student with a passion for software development and AI technologies. Experienced in leading technical projects and building innovative solutions.",
      "location": null,
      "major": "Computer Engineering",
      "graduation_year": 2026,
      "linkedin_url": "linkedin.com/in/aleksandar-drago-ilijevski",
      "profile_summary": "Aleksandar Ilijevski is a computer engineering student at Purdue University, graduating in 2026. He has a strong background in software engineering and entrepreneurship, notably building AI security platforms. Aleksandar holds various leadership roles, including Co-Founder of BuildPurdue and Vice President of Public Relations for the Purdue University ECE Student Society. Additionally, he has gained valuable experience as a software engineer intern at Acuvity and a fellow at the iVenture Accelerator.",
      "experiences": [{"title": "software engineer intern", "company": "acuvity", "end_date": "2025-12", "start_date": "2025-08", "description": null}, {"title": "cohort 11 fellow", "company": "iventure accelerator", "end_date": "2025-09", "start_date": "2025-05", "description": null}, {"title": "vice president of public relations", "company": "purdue university electrical and computer engineering student society", "end_date": "2026", "start_date": "2025-04", "description": null}, {"title": "co-founder", "company": "buildpurdue", "end_date": "2026", "start_date": "2025-03", "description": null}, {"title": "venture scout", "company": "afore capital", "end_date": "2025-01", "start_date": "2024-10", "description": null}, {"title": "summer intern investing series", "company": "dimensional fund advisors", "end_date": "2024-07", "start_date": "2024-06", "description": null}, {"title": "national science foundation innovation corps graduate", "company": "the grainger college of engineering", "end_date": "2024-07", "start_date": "2024-05", "description": null}, {"title": "newsletter chair", "company": "purdue university electrical and computer engineering student society", "end_date": "2025-04", "start_date": "2024-03", "description": null}, {"title": "cozad business venture challenge participant", "company": "the grainger college of engineering", "end_date": "2024-04", "start_date": "2024-01", "description": null}, {"title": "co-founder", "company": "klink! (iv11)", "end_date": "2025-08", "start_date": "2023-12", "description": null}, {"title": "volunteer - volunteer", "company": "humane indiana", "end_date": "2022-06", "start_date": "2021-08", "description": null}, {"title": "volunteer - volunteer", "company": "indiana state school music association inc", "end_date": "2022-08", "start_date": "2017-08", "description": null}],
      "education": [{"degree": "bachelors", "school": "purdue university college of engineering", "end_date": "2026", "start_date": "2022-08", "field_of_study": "computer engineering"}, {"degree": null, "school": "munster high school", "end_date": "2022-06", "start_date": "2018-08", "field_of_study": null}, {"degree": null, "school": "munster high school", "end_date": null, "start_date": null, "field_of_study": null}]
    }
  ],
  "processing_time_ms": 487.12,
  "event_id": "2495503e-fe23-49c9-95b2-245b589f5cb7"
}

---

### Next Steps (as required)

1. Depending on how well the recognition performs in real-time, changes may need to be made to increase efficiency and recognition time.
2. Perform UAT to guage how well recognition is captured for various users using the physical glasses.
