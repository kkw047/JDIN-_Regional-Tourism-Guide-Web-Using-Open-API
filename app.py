from flask import Flask, render_template, request, jsonify, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pymysql
import atexit
import sys
from apistudy.map import bp as map_bp

# tourist_attraction.py에서 관광지 API 호출 및 DB 저장 함수 임포트
from apistudy.tourist_attraction import get_tourist_sites_from_api, save_tourist_sites_to_db

app = Flask(__name__)
app.register_blueprint(map_bp)

# MySQL DB 접속 설정 정보
db_config = {
    'host': '61.81.96.151',  # MySQL 서버 IP 또는 도메인
    'user': 'outer',  # MySQL 사용자 계정
    'password': 'outeropensql',  # 사용자 비밀번호
    'database': 'User_Selecte',  # 접속할 데이터베이스 이름
    'charset': 'utf8mb4',  # 문자 인코딩 (한글 지원)
    'cursorclass': pymysql.cursors.DictCursor  # 결과를 dict 형태로 반환
}


@app.route('/')
def index():
    # 메인 페이지 렌더링 (index.html)
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    # 폼에서 전송된 도시명과 관광지 수 받아오기
    city = request.form.get('tourist_location')
    count = request.form.get('tourist_sites_count')

    # 입력 검증: 도시가 선택되지 않았거나 "none"일 때
    if not city or city == "none":
        return "도시를 선택하세요!", 400
    # 관광지 수가 1 미만일 경우
    if not count or int(count) < 1:
        return "관광지 수는 최소 1개 이상이어야 합니다!", 400

    # 입력값이 유효하면 결과 페이지로 리다이렉트 (GET 방식)
    return redirect(url_for('result', city=city, count=count))


@app.route('/result')
def result():
    # 결과 페이지 렌더링, GET 파라미터로 도시와 관광지 수 전달받음
    city = request.args.get('city')
    count = request.args.get('count')

    return render_template('result.html', city=city, count=count)


@app.route('/get_categories', methods=['GET'])
def get_categories():
    # 카테고리 목록을 DB에서 조회해 JSON으로 반환하는 API
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = "SELECT name FROM category"  # 카테고리 이름만 조회
            cursor.execute(sql)
            categories = [row['name'] for row in cursor.fetchall()]  # 리스트로 변환

        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"success": False, "error": str(e)})
    finally:
        if 'connection' in locals():
            connection.close()  # DB 연결 종료


@app.route('/get_tourist_sites', methods=['GET'])
def get_tourist_sites():
    # 관광지 목록 조회 API (도시 및 선택된 카테고리 기반)
    city = request.args.get('city')
    categories = request.args.get('categories', '')

    print(f"도시: {city}, 카테고리: {categories}")  # 디버깅용 로그 출력

    if not city:
        return jsonify({"success": False, "error": "도시를 지정해야 합니다."}), 400

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # 기본 조건: 주소에 도시명이 포함된 관광지 검색
            sql = "SELECT id, name, address, mapx, mapy, tel FROM tourist_attraction WHERE address LIKE %s"
            params = [f"%{city}%"]

            # 카테고리가 지정되었고 '전체'가 아닐 경우 추가 조건 생성
            if categories and categories != "전체":
                category_list = categories.split(",")
                like_conditions = []
                for category in category_list:
                    # 관광지 이름에 카테고리 문자열이 포함된 조건 추가
                    like_conditions.append("name LIKE %s")
                    params.append(f"%{category}%")

                # 카테고리 조건들을 OR 조건으로 묶음
                sql += " AND (" + " OR ".join(like_conditions) + ")"

            # 결과를 무작위로 최대 10개 추출
            sql += " ORDER BY RAND() LIMIT 10"
            cursor.execute(sql, params)
            results = cursor.fetchall()

        return jsonify({"success": True, "sites": results})
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"success": False, "error": str(e)})
    finally:
        if 'connection' in locals():
            connection.close()  # DB 연결 종료


@app.route('/process')
def process():
    # 처리 진행 페이지 렌더링 (process.html)
    return render_template('process.html',
                           city=request.args.get('city'),
                           count=request.args.get('count'))


def update_tourist_attractions():
    """
    주기적으로 관광지 데이터를 API에서 받아와 DB에 저장하는 작업 함수.
    """
    print("관광지 데이터 갱신 작업 시작...")

    # API 호출로 관광지 데이터 가져오기
    from apistudy.tourist_attraction import get_tourist_sites_from_api, save_tourist_sites_to_db

    tourist_sites = get_tourist_sites_from_api()  # API에서 데이터 수집

    # 수집된 데이터를 DB에 저장
    save_tourist_sites_to_db(tourist_sites)

    print("관광지 데이터 갱신 작업 완료!")


# 백그라운드 스케줄러 생성 및 시작
scheduler = BackgroundScheduler()
scheduler.start()

# 매일 1회 관광지 데이터 갱신 작업 예약 등록
scheduler.add_job(
    func=update_tourist_attractions,  # 실행할 함수 지정
    trigger=IntervalTrigger(days=1),  # 1일 간격 실행
    id="update_tourist_attractions_job",  # 작업 고유 ID
    name="관광지 데이터 갱신 작업",  # 작업 이름
    replace_existing=True  # 동일 ID 작업 존재 시 덮어쓰기
)

# 프로그램 종료 시 스케줄러도 안전하게 종료하도록 설정
atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    print("스케줄러가 실행 중입니다...")
    # Flask 개발 서버 실행 (외부 접속 허용)
    app.run(host='0.0.0.0', port=5000, debug=True)
