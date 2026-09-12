# Onboarding fields

`POST /api/v1/onboarding` accepts one JSON body for the **form path**. Onboarding is a **lightweight starting seed**, not a massive form. It captures only the essential identity, DOB, gender, and life stage so PAI knows who it is speaking with from turn 1.

Deeper facts (education degrees, institutions, GPA, skills, work experience, test scores, budget) are progressively and authentically discovered during **counseling chat** or extracted in 1 click via **CV upload**.

The **CV path** is `POST /api/v1/onboarding/cv` only. A successful extract marks onboarding complete. Do not send this form after a CV upload.

---

## Required Core Fields

| Field | What it is | Allowed values / format | Example |
|---|---|---|---|
| `dateOfBirth` | Date of birth (age verification & counseling stage) | ISO date, age 13–100 | `"2004-03-12"` |
| `gender` | Gender | `male` \| `female` \| `non_binary` \| `prefer_not_to_say` \| `other` | `"male"` |
| `currentStatus` | Life stage | `student` \| `graduate` \| `professional` \| `job_seeker` \| `other` | `"student"` |
| `primaryGoal` | High-level direction | `exploring` \| `placement` \| `admission` \| `professional` \| `journey_tracker` | `"admission"` |

---

## Optional Identity & Location Seeds

| Field | What it is | Allowed values / format | Example |
|---|---|---|---|
| `fullName` | Display / preferred name | Free text, ≤ 256 chars (defaults to auth signup name if omitted) | `"Ali Khan"` |
| `phone` | Mobile number | E.164, or national + `currentCountry` | `"+923001234567"` |
| `currentCountry` | Where they live now | ISO alpha-2 (`PK`), alpha-3 (`DEU`), or English name | `"PK"` |
| `currentCity` | City they live in | Free text, 2–128 chars | `"Lahore"` |
| `nationality` | Citizenship | ISO alpha-2, alpha-3, or English name | `"PK"` |

---

## Example Minimal Request

```json
{
  "dateOfBirth": "2004-03-12",
  "gender": "male",
  "currentStatus": "student",
  "primaryGoal": "admission"
}
```

---

## How Deeper Profile Details Enter the Vault

| Detail | Where it is collected |
|---|---|
| **Education (Institutions, Degrees, GPA, Major)** | Natural chat dialogue or CV upload (`/onboarding/cv`) |
| **Skills & Work History** | Natural chat dialogue or CV upload (`/onboarding/cv`) |
| **Standardized Tests & Scores** | Counseling chat dialogue or CV upload |
| **Budget & Financial Preferences** | Financial counseling sessions in chat |
| **Direct Profile Management** | Dedicated endpoints (`/api/v1/person/educations`, `/api/v1/person/skills`, etc.) |