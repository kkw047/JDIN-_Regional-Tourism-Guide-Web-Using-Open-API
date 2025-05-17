from flask import Flask, render_template, request, jsonify, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pymysql
import atexit
import sys

# tourist_attraction.py에서 함수 가져오기
from apistudy.tourist_attraction import get_tourist_sites_from_api, save_tourist_sites_to_db

app = Flask(__name__)

# MySQL DB 설정
db_config = {
    'host': '61.81.96.151',  # MySQL 서버 주소
    'user': 'outer',  # MySQL 사용자 이름
    'password': 'outeropensql',  # MySQL 비밀번호
    'database': 'User_Selecte',  # 데이터베이스 이름
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    city = request.form.get('tourist_location')
    count = request.form.get('tourist_sites_count')

    if not city or city == "none":
        return "도시를 선택하세요!", 400
    if not count or int(count) < 1:
        return "관광지 수는 최소 1개 이상이어야 합니다!", 400

    return redirect(url_for('result', city=city, count=count))


@app.route('/result')
def result():
    city = request.args.get('city')
    count = request.args.get('count')

    return render_template('result.html', city=city, count=count)


@app.route('/get_categories', methods=['GET'])
def get_categories():
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            sql = "SELECT name FROM category"
            cursor.execute(sql)
            categories = [row['name'] for row in cursor.fetchall()]

        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"success": False, "error": str(e)})
    finally:
        if 'connection' in locals():
            connection.close()


@app.route('/get_tourist_sites', methods=['GET'])
def get_tourist_sites():
    city = request.args.get('city')
    categories = request.args.get('categories', '')

    print(f"도시: {city}, 카테고리: {categories}")  # 디버깅용 출력

    if not city:
        return jsonify({"success": False, "error": "도시를 지정해야 합니다."}), 400

    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # SQL 쿼리 수정: mapx, mapy 컬럼 추가
            sql = "SELECT id, name, address, mapx, mapy, image FROM tourist_attraction WHERE address LIKE %s"
            params = [f"%{city}%"]

            if categories and categories != "전체":
                category_list = categories.split(",")
                like_conditions = []
                for category in category_list:
                    like_conditions.append("name LIKE %s")
                    params.append(f"%{category}%")

                sql += " AND (" + " OR ".join(like_conditions) + ")"

            sql += " ORDER BY RAND() LIMIT 10"
            cursor.execute(sql, params)
            results = cursor.fetchall()

            # 각 관광지 정보에 mapx, mapy 정보를 location 객체에 추가
            for result in results:
                result['location'] = {'mapx': result['mapx'], 'mapy': result['mapy']}

        return jsonify({"success": True, "sites": results})
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"success": False, "error": str(e)})
    finally:
        if 'connection' in locals():
            connection.close()



@app.route('/process')
def process():
    return render_template('process.html',
                           city=request.args.get('city'),
                           count=request.args.get('count'))


def update_tourist_attractions():
    """
    tourist_attraction.py에 정의된 함수들을 사용해서 관광 데이터를 갱신합니다.
    """
    print("관광지 데이터 갱신 작업 시작...")

    # API를 통해 관광지 데이터 가져오기
    from apistudy.tourist_attraction import get_tourist_sites_from_api, save_tourist_sites_to_db
    tourist_sites = get_tourist_sites()

    # 가져온 데이터를 데이터베이스에 저장
    save_tourist_sites_to_db(tourist_sites)

    print("관광지 데이터 갱신 작업 완료!")


# 스케줄러 설정
scheduler = BackgroundScheduler()
scheduler.start()

# 스케줄링 작업 등록
scheduler.add_job(
    func=update_tourist_attractions,  # 실행할 작업 함수
    trigger=IntervalTrigger(days=1),  # 1분마다 실행

    id="update_tourist_attractions_job",  # 고유 작업 ID
    name="관광지 데이터 갱신 작업",  # 작업 이름
    replace_existing=True  # 동일 ID가 있을 경우 기존 작업 대체
)

# 애플리케이션 종료 시 스케줄러도 종료
atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    print("스케줄러가 실행 중입니다...")
    app.run(host='0.0.0.0', port=5000, debug=True)


