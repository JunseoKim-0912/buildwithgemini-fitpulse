#!/usr/bin/env python3
"""Seed script for FitPulse Firestore database."""

import datetime
from google.cloud import firestore

# CRITICAL: Hardcoded project ID string for Firestore client
PROJECT_ID = "qwiklabs-gcp-03-a5fda0a88d46"

db = firestore.Client(project=PROJECT_ID)


def seed_database():
    print(f"Seeding Firestore database for project: {PROJECT_ID}...")

    # Seed Workout Logs collection
    workout_logs_ref = db.collection("workout_logs")
    seed_workouts = [
        {
            "user_id": "user_demo",
            "exercise_name": "Push-ups",
            "sets": 3,
            "reps": 15,
            "weight_kg": 0.0,
            "category": "Chest/Triceps",
            "notes": "Good posture, completed all 3 sets cleanly",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "user_id": "user_demo",
            "exercise_name": "Barbell Squats",
            "sets": 4,
            "reps": 10,
            "weight_kg": 60.0,
            "category": "Legs",
            "notes": "Felt light, can increase weight next week",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "user_id": "user_demo",
            "exercise_name": "Dumbbell Bicep Curls",
            "sets": 3,
            "reps": 12,
            "weight_kg": 12.5,
            "category": "Arms",
            "notes": "Controlled tempo",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ]

    for workout in seed_workouts:
        doc_ref = workout_logs_ref.add(workout)
        print(f"Added workout log document ID: {doc_ref[1].id}")

    # Seed Meal Logs collection
    meal_logs_ref = db.collection("meal_logs")
    seed_meals = [
        {
            "user_id": "user_demo",
            "meal_type": "Breakfast",
            "food_items": "Oatmeal with chia seeds, banana, and almond milk",
            "calories": 420,
            "protein_g": 14,
            "carbs_g": 68,
            "fat_g": 9,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "user_id": "user_demo",
            "meal_type": "Lunch",
            "food_items": "Quinoa salad with chickpeas, avocado, and spinach",
            "calories": 550,
            "protein_g": 22,
            "carbs_g": 72,
            "fat_g": 18,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ]

    for meal in seed_meals:
        doc_ref = meal_logs_ref.add(meal)
        print(f"Added meal log document ID: {doc_ref[1].id}")

    print("Firestore seeding complete!")


if __name__ == "__main__":
    seed_database()
