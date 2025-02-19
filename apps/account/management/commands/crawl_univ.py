import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from apps.account.models import School

class Command(BaseCommand):
    help = "Crawl universities from Wikipedia..."

    def handle(self, *args, **options):
        url = "https://en.wikipedia.org/wiki/List_of_universities_in_South_Korea"
        resp = requests.get(url)
        print("Response status code:", resp.status_code)
        print("Response length:", len(resp.text))
        soup = BeautifulSoup(resp.text, 'html.parser')
        print(soup.prettify()[:1000])

        # mw-parser-output 안의 <ul> -> <li> 목록을 찾는다
        lis = soup.select("div.mw-parser-output > ul > li")

        for li in lis:
            # li 내 첫 번째 a 태그 찾기
            first_link = li.find("a")
            if not first_link:
                continue  # a 태그가 없으면 스킵

            college_name = first_link.get_text(strip=True)

            # "College"라는 단어가 들어간 것만 필터링
            # (혹은 'University' 등 다른 조건을 추가해도 됨)
            if "College" in college_name or "University" in college_name:
                print(college_name)
                School.objects.get_or_create(name=college_name)

        self.stdout.write(self.style.SUCCESS("Crawling completed!"))