from django.core.management.base import BaseCommand
from apps.account.models import School, Department

DEPARTMENTS = [
    "College of Humanities",
    "Department of Korean Language and Literature",
    "Department of Chinese Language and Literature",
    "Department of English Language and Literature",
    "Department of French Language and Literature",
    "Department of German Language and Literature",
    "Department of Russian Language and Literature",
    "Department of Hispanic Language and Literature",
    "Department of Linguistics",
    "Department of History, College of Humanities",
    "Department of Philosopy",
    "Department of Aesthetics",
    "Department of Religious Studies",
    "Department of Archaeology and Art History",
    "College of Social Sciences",
    "Department of Political Science",
    "Department of International Relations",
    "Department of Economics",
    "Department of Sociology",
    "Department of Anthropology",
    "Department of Psychology",
    "Department of Geography",
    "Department of Social Welfare",
    "Department of Communication",
    "College of Natural Sciences",
    "Department of Mathematical Sciences",
    "Department of Statistics",
    "Department of Physics",
    "Department of Astronomy",
    "Department of Chemistry",
    "Department of Biological Science",
    "Department of Earth and Environmental Studies",
    "College of Nursing",
    "Department of Business Administration",
    "College of Engineering",
    "Department of Civil and Environmental Engineering",
    "Department of Mechanical Engineering",
    "Department of Aerospace Engineering",
    "Department of Materials Science and Engineering",
    "Department of Electrical and Computer Engineering",
    "Department of Computer Science and Engineering",
    "Department of Chemical and Biological Engineering",
    "Department of Architecture",
    "Department of Industrial Engineering",
    "Department of Energy Resources Engineering",
    "Department of Nuclear Engineering",
    "Department of Naval Architecture and Ocean Engineering",
    "College of Agriculture and Life Science",
    "Department of Plant Science",
    "Department of Forest Science",
    "Department of Applied Biology and Chemistry",
    "Department of Food and Animal Biotechnology",
    "Department of Biosystems and Biomaterials Science & Engineering",
    "Department of Landscape Architecture and Rural Systems Engineering",
    "Department of Agricultural Economics and Rural Development",
    "College of Fine Arts",
    "Department of Oriental Painting",
    "Department of Painting",
    "Department of Sculpture",
    "Department of Crafts",
    "Department of Design",
    "College of Education",
    "Department of Education",
    "Department of Korean Language Education",
    "Department of English Language Education",
    "Department of Mathematics Education",
    "Department of Social Studies Education",
    "Department of French Language Education",
    "Department of German Language Education",
    "Department of History Education",
    "Department of Geography Education",
    "Department of Ethics Education",
    "Department of Physics Education",
    "Department of Chemistry Education",
    "Department of Biology Education",
    "Department of Earth Science Education",
    "Department of Physical Education",
    "College of Human Ecology",
    "Department of Consumer Science",
    "Department of Child Development and Family Studies",
    "Department of Food and Nutrition",
    "Department of Fashion and Textiles",
    "College of Veterinary Medicine",
    "College of Pharmacy",
    "College of Music",
    "Department of Vocal Music",
    "Department of Composition",
    "Program in Piano",
    "Program in String, Woodwind, Brass and Percussion",
    "Department of Korean Music",
    "College of Medicine",
    "College of Liberal Studies",
    "College of Transdisciplinary Innovations",
    "College of Dentistry"
]

class Command(BaseCommand):
    help = "Add departments to all schools"

    def handle(self, *args, **kwargs):
        schools = School.objects.all()
        total_added = 0

        if not schools.exists():
            self.stdout.write(self.style.ERROR("❌ No schools found in the database. Please add schools first."))
            return

        for school in schools:
            count = 0
            for dept_name in DEPARTMENTS:
                _, created = Department.objects.get_or_create(school=school, name=dept_name)
                if created:
                    count += 1
            self.stdout.write(self.style.SUCCESS(f"✅ {count} departments added for {school.name}"))
            total_added += count
        
        self.stdout.write(self.style.SUCCESS(f"🎉 Total {total_added} departments added to all schools."))
