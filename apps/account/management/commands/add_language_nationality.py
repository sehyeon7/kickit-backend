from django.core.management.base import BaseCommand
from apps.account.models import Language, Nationality

class Command(BaseCommand):
    help = "Populate initial Language and Nationality data"

    def handle(self, *args, **kwargs):
        languages = [
            "官話", "Español", "English", "हिन्दी", "اُردوُ", "Bahasa Indonesia", "العربية", "Português", "Français", "Русский язык",
            "বাংলা", "日本語", "Tiếng Việt", "Deutsch", "吳語", "한국어", "Basa Jawa", "ਪੰਜਾਬੀ", "پنجابی", "తెలుగు", "मराठी",
            "தமிழ்", "Italiano", "Türkçe", "עברית"
        ]
        countries = [
            "Algeria", "Angaur (Palau)", "Argentina", "Australia", "Austria", "Bangladesh", "Belgium", "Brazil", "Cambodia",
            "Canada", "Chile", "China", "Costa Rica", "Cuba", "Czech Republic", "Denmark", "Egypt", "Finland", "France",
            "Germany", "Hungary", "India", "Indonesia", "Ireland", "Iraq", "Israel", "Italy", "Jamaica", "Japan", "Kazakhstan",
            "Liechtenstein", "Luxembourg", "Malaysia", "Mauritius", "Mexico", "Morocco", "Namibia", "Netherlands", "New Zealand",
            "North Korea", "Northern Cyprus", "Norway", "Pakistan", "Palestine", "Peru", "Philippines", "Poland", "Portugal",
            "Russia", "Senegal", "Singapore", "South Africa", "South Korea", "Spain", "Sri Lanka", "Suriname", "Sweden",
            "Switzerland", "Taiwan", "Thailand", "Türkiye", "United Arab Emirates", "United Kingdom", "United States",
            "Uzbekistan", "Vietnam", "Zimbabwe"
        ]

        created_languages = Language.objects.bulk_create(
            [Language(language=l) for l in languages],
            ignore_conflicts=True
        )
        created_nationalities = Nationality.objects.bulk_create(
            [Nationality(name=c) for c in countries],
            ignore_conflicts=True
        )

        self.stdout.write(self.style.SUCCESS(f"✅ {len(languages)} languages and {len(countries)} nationalities inserted (duplicates ignored)."))
