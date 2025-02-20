import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from apps.account.models import Department

class Command(BaseCommand):
    help = "Crawl department names (academic disciplines) from Wikipedia and store in Department model"

    def handle(self, *args, **options):
        url = "https://en.wikipedia.org/wiki/List_of_academic_disciplines_and_sub-disciplines"
        resp = requests.get(url)
        print("Response status code:", resp.status_code)
        print("Response length:", len(resp.text))

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 아래 selector는 예시입니다. 실제로 페이지 구조를 보고 수정해야 함.
        # 예: div.div-col ul li a
        discipline_links = soup.select("div.div-col ul li a")

        count = 0
        for link in discipline_links:
            # 예: <a href="/wiki/Computer_science" title="Computer science">Computer science</a>
            dept_name = link.get_text(strip=True)
            if not dept_name:
                continue

            # 예: 간단히 영어 알파벳/공백만 필터링한다거나, 너무 긴 항목 스킵
            # 필요시 조건을 추가해서 "Department" "Studies" 등 특정 키워드만 저장할 수도 있음
            if len(dept_name) > 50:
                # 너무 길면 스킵
                continue

            # DB 저장 (get_or_create로 중복 방지)
            obj, created = Department.objects.get_or_create(name=dept_name)
            if created:
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Crawling completed! {count} new departments added."))