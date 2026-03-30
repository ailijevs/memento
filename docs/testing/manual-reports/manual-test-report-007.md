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
|  |  |  |

---

### Outcome

- [ ] **Pass**
- [ ] **Fail**

---

### Logs / Screenshots / Evidence

- 

---

### Next Steps (as required)

- First, a github issue will be
- If passed: any regression or edge cases to add?
- Action items:

1. …
2. …
