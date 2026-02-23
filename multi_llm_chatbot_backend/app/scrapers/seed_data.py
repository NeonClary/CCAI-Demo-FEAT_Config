"""
Seed data for CU Boulder courses and professor ratings.

Used when the external APIs (RateMyProfessors GraphQL, classes.colorado.edu)
are unreachable.  Called automatically on startup when the collections are
empty.  Data is representative of real CU Boulder offerings.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _professors() -> List[Dict[str, Any]]:
    now = datetime.utcnow()
    return [
        {"name": "Sarah Chen", "department": "Engineering", "rating": 4.8, "difficulty": 3.2, "would_take_again_pct": 95, "num_ratings": 142, "rmp_id": "seed_1", "scraped_at": now},
        {"name": "Michael Torres", "department": "Engineering", "rating": 4.5, "difficulty": 3.5, "would_take_again_pct": 88, "num_ratings": 97, "rmp_id": "seed_2", "scraped_at": now},
        {"name": "Jennifer Walsh", "department": "Engineering", "rating": 4.2, "difficulty": 2.8, "would_take_again_pct": 82, "num_ratings": 63, "rmp_id": "seed_3", "scraped_at": now},
        {"name": "David Kim", "department": "Engineering", "rating": 3.9, "difficulty": 3.8, "would_take_again_pct": 70, "num_ratings": 51, "rmp_id": "seed_4", "scraped_at": now},
        {"name": "Robert Braun", "department": "Engineering", "rating": 4.6, "difficulty": 3.0, "would_take_again_pct": 91, "num_ratings": 120, "rmp_id": "seed_5", "scraped_at": now},
        {"name": "Lisa Marker-Goldstein", "department": "Engineering", "rating": 4.3, "difficulty": 2.5, "would_take_again_pct": 85, "num_ratings": 78, "rmp_id": "seed_6", "scraped_at": now},
        {"name": "James Papadopoulos", "department": "Computer Science", "rating": 4.7, "difficulty": 3.6, "would_take_again_pct": 93, "num_ratings": 205, "rmp_id": "seed_7", "scraped_at": now},
        {"name": "Elizabeth Bhatt", "department": "Computer Science", "rating": 4.4, "difficulty": 3.3, "would_take_again_pct": 86, "num_ratings": 167, "rmp_id": "seed_8", "scraped_at": now},
        {"name": "Richard Han", "department": "Computer Science", "rating": 4.1, "difficulty": 3.7, "would_take_again_pct": 78, "num_ratings": 134, "rmp_id": "seed_9", "scraped_at": now},
        {"name": "Shayon Gupta", "department": "Computer Science", "rating": 3.8, "difficulty": 4.1, "would_take_again_pct": 65, "num_ratings": 89, "rmp_id": "seed_10", "scraped_at": now},
        {"name": "Kenneth Anderson", "department": "Computer Science", "rating": 4.5, "difficulty": 3.4, "would_take_again_pct": 90, "num_ratings": 180, "rmp_id": "seed_11", "scraped_at": now},
        {"name": "Amanda Sullivan", "department": "Mathematics", "rating": 4.6, "difficulty": 3.1, "would_take_again_pct": 92, "num_ratings": 155, "rmp_id": "seed_12", "scraped_at": now},
        {"name": "Thomas Grant", "department": "Mathematics", "rating": 3.7, "difficulty": 4.0, "would_take_again_pct": 62, "num_ratings": 98, "rmp_id": "seed_13", "scraped_at": now},
        {"name": "Judith Packer", "department": "Mathematics", "rating": 4.3, "difficulty": 3.5, "would_take_again_pct": 84, "num_ratings": 112, "rmp_id": "seed_14", "scraped_at": now},
        {"name": "Daniel Larremore", "department": "Computer Science", "rating": 4.9, "difficulty": 3.3, "would_take_again_pct": 97, "num_ratings": 73, "rmp_id": "seed_15", "scraped_at": now},
        {"name": "Patricia Rankin", "department": "Physics", "rating": 4.4, "difficulty": 3.6, "would_take_again_pct": 87, "num_ratings": 102, "rmp_id": "seed_16", "scraped_at": now},
        {"name": "Carlos Rivera", "department": "Physics", "rating": 4.0, "difficulty": 3.9, "would_take_again_pct": 74, "num_ratings": 68, "rmp_id": "seed_17", "scraped_at": now},
        {"name": "Emily Harmon", "department": "Writing and Rhetoric", "rating": 4.7, "difficulty": 2.3, "would_take_again_pct": 94, "num_ratings": 185, "rmp_id": "seed_18", "scraped_at": now},
        {"name": "Nathan Brooks", "department": "Writing and Rhetoric", "rating": 4.1, "difficulty": 2.7, "would_take_again_pct": 80, "num_ratings": 120, "rmp_id": "seed_19", "scraped_at": now},
        {"name": "Anca Radulescu", "department": "Applied Mathematics", "rating": 4.2, "difficulty": 3.8, "would_take_again_pct": 79, "num_ratings": 91, "rmp_id": "seed_20", "scraped_at": now},
        {"name": "Derek Briggs", "department": "Education", "rating": 4.5, "difficulty": 2.9, "would_take_again_pct": 89, "num_ratings": 76, "rmp_id": "seed_21", "scraped_at": now},
        {"name": "Maria Gonzalez", "department": "ENVD", "rating": 4.3, "difficulty": 3.1, "would_take_again_pct": 83, "num_ratings": 64, "rmp_id": "seed_22", "scraped_at": now},
        {"name": "William Kusner", "department": "Mathematics", "rating": 4.0, "difficulty": 3.4, "would_take_again_pct": 76, "num_ratings": 55, "rmp_id": "seed_23", "scraped_at": now},
    ]


def _courses() -> List[Dict[str, Any]]:
    now = datetime.utcnow()
    semester = "Spring 2026"
    raw = [
        # ENES courses
        ("ENES 1010", "First-Year Engineering Projects", "001", "Sarah Chen", {"days": "MWF", "start_time": "9:00am", "end_time": "9:50am", "raw": "MWF 9:00am-9:50am"}, "ECCE 141", 35),
        ("ENES 1010", "First-Year Engineering Projects", "002", "Michael Torres", {"days": "MWF", "start_time": "10:00am", "end_time": "10:50am", "raw": "MWF 10:00am-10:50am"}, "ECCE 141", 28),
        ("ENES 1010", "First-Year Engineering Projects", "003", "Jennifer Walsh", {"days": "TTh", "start_time": "11:00am", "end_time": "12:15pm", "raw": "TTh 11:00am-12:15pm"}, "ECCE 141", 15),
        ("ENES 1010", "First-Year Engineering Projects", "004", "David Kim", {"days": "MWF", "start_time": "1:00pm", "end_time": "1:50pm", "raw": "MWF 1:00pm-1:50pm"}, "ECCE 283", 32),
        ("ENES 1010", "First-Year Engineering Projects", "005", "Robert Braun", {"days": "TTh", "start_time": "2:00pm", "end_time": "3:15pm", "raw": "TTh 2:00pm-3:15pm"}, "ECCE 141", 5),
        ("ENES 1010", "First-Year Engineering Projects", "006", "Lisa Marker-Goldstein", {"days": "MWF", "start_time": "8:00am", "end_time": "8:50am", "raw": "MWF 8:00am-8:50am"}, "ECCE 283", 40),
        ("ENES 1110", "Engineering Design Projects", "001", "Sarah Chen", {"days": "TTh", "start_time": "9:30am", "end_time": "10:45am", "raw": "TTh 9:30am-10:45am"}, "ECCE 141", 22),
        ("ENES 1110", "Engineering Design Projects", "002", "Robert Braun", {"days": "MWF", "start_time": "11:00am", "end_time": "11:50am", "raw": "MWF 11:00am-11:50am"}, "ECCE 283", 18),

        # CSCI courses
        ("CSCI 1300", "Computer Science 1: Starting Computing", "001", "James Papadopoulos", {"days": "MWF", "start_time": "10:00am", "end_time": "10:50am", "raw": "MWF 10:00am-10:50am"}, "ECCR 200", 12),
        ("CSCI 1300", "Computer Science 1: Starting Computing", "002", "Elizabeth Bhatt", {"days": "TTh", "start_time": "2:00pm", "end_time": "3:15pm", "raw": "TTh 2:00pm-3:15pm"}, "ECCR 200", 8),
        ("CSCI 1300", "Computer Science 1: Starting Computing", "003", "Shayon Gupta", {"days": "MWF", "start_time": "1:00pm", "end_time": "1:50pm", "raw": "MWF 1:00pm-1:50pm"}, "ECCR 150", 20),
        ("CSCI 2270", "Computer Science 2: Data Structures", "001", "Richard Han", {"days": "MWF", "start_time": "9:00am", "end_time": "9:50am", "raw": "MWF 9:00am-9:50am"}, "ECCR 200", 5),
        ("CSCI 2270", "Computer Science 2: Data Structures", "002", "Kenneth Anderson", {"days": "TTh", "start_time": "11:00am", "end_time": "12:15pm", "raw": "TTh 11:00am-12:15pm"}, "ECCR 200", 10),
        ("CSCI 2400", "Computer Systems", "001", "Richard Han", {"days": "TTh", "start_time": "9:30am", "end_time": "10:45am", "raw": "TTh 9:30am-10:45am"}, "ECCR 150", 15),
        ("CSCI 3104", "Algorithms", "001", "Daniel Larremore", {"days": "MWF", "start_time": "2:00pm", "end_time": "2:50pm", "raw": "MWF 2:00pm-2:50pm"}, "ECCR 200", 7),
        ("CSCI 3155", "Principles of Programming Languages", "001", "Elizabeth Bhatt", {"days": "MWF", "start_time": "11:00am", "end_time": "11:50am", "raw": "MWF 11:00am-11:50am"}, "ECCR 150", 14),
        ("CSCI 3308", "Software Dev Methods and Tools", "001", "Kenneth Anderson", {"days": "MWF", "start_time": "3:00pm", "end_time": "3:50pm", "raw": "MWF 3:00pm-3:50pm"}, "ECCR 200", 20),

        # MATH courses
        ("MATH 1300", "Calculus 1", "001", "Amanda Sullivan", {"days": "MWF", "start_time": "8:00am", "end_time": "8:50am", "raw": "MWF 8:00am-8:50am"}, "MATH 100", 10),
        ("MATH 1300", "Calculus 1", "002", "Thomas Grant", {"days": "TTh", "start_time": "9:30am", "end_time": "10:45am", "raw": "TTh 9:30am-10:45am"}, "MATH 100", 25),
        ("MATH 1300", "Calculus 1", "003", "William Kusner", {"days": "MWF", "start_time": "12:00pm", "end_time": "12:50pm", "raw": "MWF 12:00pm-12:50pm"}, "MATH 100", 18),
        ("MATH 2300", "Calculus 2", "001", "Judith Packer", {"days": "MWF", "start_time": "10:00am", "end_time": "10:50am", "raw": "MWF 10:00am-10:50am"}, "MATH 100", 15),
        ("MATH 2300", "Calculus 2", "002", "Amanda Sullivan", {"days": "TTh", "start_time": "11:00am", "end_time": "12:15pm", "raw": "TTh 11:00am-12:15pm"}, "MATH 100", 8),
        ("MATH 2400", "Calculus 3", "001", "Judith Packer", {"days": "MWF", "start_time": "1:00pm", "end_time": "1:50pm", "raw": "MWF 1:00pm-1:50pm"}, "MATH 100", 12),
        ("MATH 3430", "Ordinary Differential Equations", "001", "Anca Radulescu", {"days": "TTh", "start_time": "2:00pm", "end_time": "3:15pm", "raw": "TTh 2:00pm-3:15pm"}, "MATH 220", 20),

        # PHYS courses
        ("PHYS 1110", "General Physics 1", "001", "Patricia Rankin", {"days": "MWF", "start_time": "9:00am", "end_time": "9:50am", "raw": "MWF 9:00am-9:50am"}, "DUAN G1B30", 8),
        ("PHYS 1110", "General Physics 1", "002", "Carlos Rivera", {"days": "TTh", "start_time": "12:30pm", "end_time": "1:45pm", "raw": "TTh 12:30pm-1:45pm"}, "DUAN G1B30", 22),
        ("PHYS 1120", "General Physics 2", "001", "Patricia Rankin", {"days": "MWF", "start_time": "11:00am", "end_time": "11:50am", "raw": "MWF 11:00am-11:50am"}, "DUAN G1B30", 18),

        # WRTG courses
        ("WRTG 1150", "First-Year Writing", "001", "Emily Harmon", {"days": "MWF", "start_time": "10:00am", "end_time": "10:50am", "raw": "MWF 10:00am-10:50am"}, "HUMN 135", 6),
        ("WRTG 1150", "First-Year Writing", "002", "Nathan Brooks", {"days": "TTh", "start_time": "3:30pm", "end_time": "4:45pm", "raw": "TTh 3:30pm-4:45pm"}, "HUMN 135", 14),
        ("WRTG 3030", "Writing on Science and Society", "001", "Emily Harmon", {"days": "TTh", "start_time": "11:00am", "end_time": "12:15pm", "raw": "TTh 11:00am-12:15pm"}, "HUMN 250", 10),

        # ENVD / General
        ("ENVD 1000", "Environmental Design 1", "001", "Maria Gonzalez", {"days": "MW", "start_time": "2:00pm", "end_time": "3:15pm", "raw": "MW 2:00pm-3:15pm"}, "ENVD 234", 30),
    ]
    courses = []
    for code, title, section, instructor, schedule, location, seats in raw:
        courses.append({
            "course_code": code,
            "title": title,
            "section": section,
            "instructor": instructor,
            "schedule": schedule,
            "location": location,
            "seats_available": seats,
            "semester": semester,
            "scraped_at": now,
        })
    return courses


async def seed_if_empty():
    """Insert seed data into MongoDB if the collections are empty."""
    from app.core.database import get_database
    db = get_database()

    prof_count = await db.professor_ratings.count_documents({})
    course_count = await db.courses.count_documents({})

    if prof_count == 0:
        profs = _professors()
        for p in profs:
            await db.professor_ratings.update_one(
                {"name": p["name"], "department": p["department"]},
                {"$set": p},
                upsert=True,
            )
        logger.info("Seeded %d professor ratings", len(profs))

    if course_count == 0:
        courses = _courses()
        for c in courses:
            await db.courses.update_one(
                {"course_code": c["course_code"], "section": c["section"], "semester": c["semester"]},
                {"$set": c},
                upsert=True,
            )
        logger.info("Seeded %d courses", len(courses))

    if prof_count > 0 and course_count > 0:
        logger.info("Database already seeded (professors=%d, courses=%d)", prof_count, course_count)
