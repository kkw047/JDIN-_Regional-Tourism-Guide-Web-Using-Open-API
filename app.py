from flask import Flask, render_template
from apistudy.main import get_results  # apistudy/main.py의 get_results 함수 가져오기

app = Flask(__name__)  # Flask 애플리케이션 생성


@app.route('/')
def homepage():
    # main.py의 get_results() 함수로부터 관광지 및 음식 데이터 가져오기
    results = get_results()
    tourist_sites = results.get("tourist_sites", [])
    food_locations_cheongju = results.get("food_locations_cheongju", [])
    food_locations_chungju = results.get("food_locations_chungju", [])

    # 템플릿으로 데이터를 전달하여 렌더링
    return render_template(
        'index.html',
        tourist_sites=tourist_sites,
        food_locations_cheongju=food_locations_cheongju,
        food_locations_chungju=food_locations_chungju
    )


if __name__ == '__main__':
    app.run(debug=True)  # 개발 중에는 debug=True로 실행
